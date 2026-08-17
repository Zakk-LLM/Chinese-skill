#!/usr/bin/env python3
"""Lint Chinese prose and reject Chinese code comments."""

import argparse
import ast
import dataclasses
import fnmatch
import gzip
import html
import io
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
import tokenize
import unicodedata
import zipfile


ROOT = pathlib.Path(__file__).resolve().parent.parent
RULES = json.loads((ROOT / "references" / "wording.json").read_text(
    encoding="utf-8"))
TECHNICAL_DATA = json.loads(
    (ROOT / "references" / "technical-terms.json").read_text(encoding="utf-8"))
TECHNICAL_TERMS = TECHNICAL_DATA["terms"]
PRESERVED_TERMS = TECHNICAL_DATA["preserve"]
PRESERVED_TRANSLATIONS = TECHNICAL_DATA["preserve_translations"]
HASH_COMMENT_SUFFIXES = {
    ".bash", ".cmake", ".conf", ".eclass", ".ebuild", ".env", ".ex", ".exs",
    ".fish", ".ini", ".ksh", ".mk", ".nix", ".pl", ".pm", ".properties",
    ".ps1", ".r", ".rb", ".service", ".sh", ".toml", ".yaml", ".yml",
    ".zsh",
}
HASH_COMMENT_NAMES = {
    ".dockerignore", ".editorconfig", ".gitattributes", ".gitignore",
    "CMakeLists.txt", "Containerfile", "Dockerfile", "Justfile", "Makefile",
    "PKGBUILD", "cron.d",
}
CL_COMMENT_SUFFIXES = {
    ".c", ".cc", ".cjs", ".cpp", ".cs", ".cts", ".dart", ".go",
    ".gradle", ".h", ".hpp", ".java", ".js", ".jsx", ".kt", ".kts",
    ".mdx", ".mjs", ".mts", ".php", ".rs", ".scala", ".swift", ".ts", ".tsx",
    ".vue", ".svelte",
}
HTML_COMMENT_SUFFIXES = {
    ".htm", ".html", ".markdown", ".md", ".mdx", ".svelte", ".svg", ".vue", ".xml",
}
DATA_SUFFIXES = {".csv", ".json", ".lock", ".po", ".pot", ".svg", ".toml", ".tsv",
                 ".yaml", ".yml"}
PROSE_SUFFIXES = {".adoc", ".markdown", ".md", ".mdx", ".rst", ".text", ".txt"}
SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", "vendor", "__pycache__"}
CJK_CLASS = r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U000323af"
CJK = re.compile(f"[{CJK_CLASS}]")
SENTENCE_END = re.compile(r"[。！？!?]")
SENTENCE = re.compile(r"[^。！？!?\n]+[。！？!?]?")
CLAUSE_CONNECTORS = re.compile(
    r"並且|並|同时|同時|以便|因此|因而|所以|但是|然而|如果|若是|除非|"
    r"即使|雖然|虽然|儘管|尽管|而且|以及|另一方面")
INTERNAL_RULE_FILES = {
    *((ROOT / "references" / name).resolve()
      for name in ("wording.json", "copy-fixtures.json", "technical-terms.json")),
    (ROOT / "evals" / "evals.json").resolve(),
}
LITERAL_TERMS = {
    term for group in RULES["literal_groups"] for term in group["terms"]
}


@dataclasses.dataclass(frozen=True, order=True)
class Finding:
    """One stable diagnostic with tuple-compatible legacy access."""

    line: int
    message: str
    sample: str = ""
    code: str = "internal.unknown"
    severity: str = "error"

    def __iter__(self):
        return iter((self.line, self.message, self.sample))

    def __getitem__(self, index):
        return (self.line, self.message, self.sample)[index]

    def __len__(self):
        return 3


def issue(code, line, message, sample="", severity="error"):
    return Finding(line, message, sample, code, severity)


def line_number(text, offset):
    return len(re.findall(r"\r\n|[\n\r\x85\u2028\u2029]", text[:offset])) + 1


def applies_to_style(rule, style):
    return not rule.get("styles") or style in rule["styles"]


def phrase_findings(text, style="standard"):
    matches = []
    for group in RULES["literal_groups"]:
        if not applies_to_style(group, style):
            continue
        for term in group["terms"]:
            start = 0
            while True:
                at = text.find(term, start)
                if at < 0:
                    break
                matches.append((at, group["id"], group["message"], term))
                start = at + len(term)
    words = longer_words(LITERAL_TERMS) if matches else set()
    findings = [issue(f"wording.{identifier}", line_number(text, at), message, term)
                for at, identifier, message, term in matches
                if not contained_in_longer_word(text, at, at + len(term), words)]
    for rule in RULES["regex_rules"]:
        if not applies_to_style(rule, style):
            continue
        for match in re.finditer(rule["pattern"], text):
            findings.append(issue(
                f"wording.{rule['id']}", line_number(text, match.start()),
                rule["message"], match.group(0)))
    return findings


TRADITIONAL_MARKERS = set(RULES["locale_markers"]["zh-TW"])
SIMPLIFIED_MARKERS = set(RULES["locale_markers"]["zh-CN"])
SHARED_MARKERS = TRADITIONAL_MARKERS.intersection(SIMPLIFIED_MARKERS)
TRADITIONAL_MARKERS -= SHARED_MARKERS
SIMPLIFIED_MARKERS -= SHARED_MARKERS
LOCALE_SCRIPT = {
    "zh-CN": "simplified",
    "zh-SG": "simplified",
    "zh-MY": "simplified",
    "zh-TW": "traditional",
    "zh-HK": "traditional",
}


def mask_locale_names(text):
    """Naming another locale, a brand, or a shared word is not locale mixing."""
    text = mask_comparison_lines(text)
    for name in (*RULES["locale_name_exceptions"], *RULES["locale_word_exceptions"]):
        text = text.replace(name, " " * len(name))
    return text


def locale_findings(text, locale):
    text = mask_locale_names(text)
    traditional = TRADITIONAL_MARKERS
    simplified = SIMPLIFIED_MARKERS
    found_traditional = traditional.intersection(text)
    found_simplified = simplified.intersection(text)
    if locale == "auto" and found_traditional and found_simplified:
        sample = "".join(sorted(found_traditional)[:4] + sorted(found_simplified)[:4])
        positions = [min(text.index(char) for char in found_traditional),
                     min(text.index(char) for char in found_simplified)]
        return [issue("locale.mixed-script", line_number(text, max(positions)),
                      "do not mix Traditional and Simplified Chinese", sample)]
    script = LOCALE_SCRIPT.get(locale)
    opposite = simplified if script == "traditional" else traditional
    out = []
    if script:
        for number, line in enumerate(text.splitlines(), 1):
            found = opposite.intersection(line)
            if found:
                out.append(issue(
                    "locale.wrong-script", number,
                    f"text does not match requested locale {locale}",
                    "".join(sorted(found)[:8])))
    return out


def terminology_findings(text, locale):
    if locale not in {"zh-TW", "zh-CN"}:
        return []
    text = mask_comparison_lines(text)
    other = "zh-CN" if locale == "zh-TW" else "zh-TW"
    out = []
    for item in TECHNICAL_TERMS:
        if not item.get("enforce"):
            continue
        preferred = item[locale]
        rejected_terms = [item[other], *item.get("reject", {}).get(locale, [])]
        for rejected in rejected_terms:
            if not rejected or rejected == preferred:
                continue
            start = 0
            while True:
                at = text.find(rejected, start)
                if at < 0:
                    break
                out.append(issue(
                    "terminology.locale", line_number(text, at),
                    f"use {preferred} for {item['en']} in {locale}", rejected))
                start = at + len(rejected)
    return out


def guarded_names(extra_terms=None):
    """Bundled seeds plus the project's own list; a project entry wins by name."""
    names = {item["en"]: item for item in PRESERVED_TRANSLATIONS}
    for item in extra_terms or ():
        names[item["en"]] = item
    return list(names.values())


def validate_guarded_names(data, source):
    if not isinstance(data, dict):
        raise ValueError(f"{source}: top level must be an object")
    entries = data.get("preserve_translations")
    if not isinstance(entries, list):
        raise ValueError(f"{source}: preserve_translations must be a list")
    names = set()
    for index, item in enumerate(entries):
        label = f"{source}: preserve_translations[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{label} must be an object")
        for field in ("en", "domain", "note"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f"{label}.{field} must be a non-empty string")
        rejected = item.get("reject")
        if (not isinstance(rejected, list) or not rejected
                or any(not isinstance(value, str) or not value
                       for value in rejected)):
            raise ValueError(
                f"{label}.reject must be a non-empty list of non-empty strings")
        if len(rejected) != len(set(rejected)):
            raise ValueError(f"{label}.reject contains duplicates")
        if item["en"] in names:
            raise ValueError(f"{source}: duplicate guarded name {item['en']!r}")
        names.add(item["en"])
    return entries


def load_terms(path):
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    return validate_guarded_names(data, str(path))


def guarded_name_present(text, name):
    pattern = rf"(?<![A-Za-z0-9_]){re.escape(name)}(?:s|es)?(?![A-Za-z0-9_])"
    return re.search(pattern, text, re.I) is not None


def preserved_translation_findings(name_text, prose_text, extra_terms=None):
    """A guarded name rendered in Chinese in the same document usually renames it."""
    out = []
    for item in guarded_names(extra_terms):
        if not guarded_name_present(name_text, item["en"]):
            continue
        for rejected in item["reject"]:
            start = 0
            while True:
                at = prose_text.find(rejected, start)
                if at < 0:
                    break
                out.append(issue(
                    "terminology.preserved", line_number(prose_text, at),
                    f"confirm {item['en']} before translating it: {item['note']}",
                    rejected, severity="warning"))
                start = at + len(rejected)
    return out


LEXICONS = ROOT / "lexicons"
OPENCC_ARCHIVE = LEXICONS / "opencc-1.4.1-resources.zip"
ZHCONVERSION = LEXICONS / "mediawiki-zhconversion-REL1_43.php.gz"
WORD_CORPORA = (
    (LEXICONS / "cc-cedict.txt.gz", (0, 1)),
    (LEXICONS / "mcbopomofo-data-3.0.txt.gz", (1,)),
    (LEXICONS / "jieba-dict-0.42.1.txt.gz", (0,)),
    (LEXICONS / "thuocl-it-2018-11-21.txt.gz", (0,)),
    (LEXICONS / "thuocl-animal-2018-11-21.txt.gz", (0,)),
    (LEXICONS / "thuocl-finance-2018-11-21.txt.gz", (0,)),
    (LEXICONS / "thuocl-car-2018-11-21.txt.gz", (0,)),
    (LEXICONS / "thuocl-idiom-2018-11-21.txt.gz", (0,)),
    (LEXICONS / "thuocl-place-2018-11-21.txt.gz", (0,)),
    (LEXICONS / "thuocl-food-2018-11-21.txt.gz", (0,)),
    (LEXICONS / "thuocl-law-2018-11-21.txt.gz", (0,)),
    (LEXICONS / "thuocl-historical-figures-2018-11-21.txt.gz", (0,)),
    (LEXICONS / "thuocl-medical-2018-11-21.txt.gz", (0,)),
    (LEXICONS / "thuocl-poem-2018-11-21.txt.gz", (0,)),
    (LEXICONS / "rime-essay-2026-07-13.txt.gz", (0,)),
)
REGIONAL_TABLES = {
    "zh-TW": ("TWPhrases.txt", "ZH_TO_TW", "STCharacters.txt"),
    "zh-CN": ("TWPhrasesRev.txt", "ZH_TO_CN", "TSCharacters.txt"),
}
PAIR = re.compile(r"'([^']+)' => '([^']*)'")
_regional_cache = {}
_word_cache = {}


def character_map(name):
    with zipfile.ZipFile(OPENCC_ARCHIVE) as archive:
        lines = archive.read(name).decode().splitlines()
    return {key: value.split(" ")[0]
            for key, _, value in (line.partition("\t") for line in lines)}


def conversion_pairs(phrase_file, table):
    with zipfile.ZipFile(OPENCC_ARCHIVE) as archive:
        for line in archive.read(phrase_file).decode().splitlines():
            key, _, value = line.partition("\t")
            if value:
                yield key, value.split(" ")[0]
    with gzip.open(ZHCONVERSION, "rt", encoding="utf-8") as handle:
        body = handle.read().split(f"{table} = [", 1)[1].split("\n\t];", 1)[0]
    for key, value in PAIR.findall(body):
        yield key, value.split(" ")[0]


def maintained_forms(locale):
    """Forms already decided by technical-terms.json, which outranks the corpora."""
    other = "zh-CN" if locale == "zh-TW" else "zh-TW"
    forms = set()
    for item in TECHNICAL_TERMS:
        forms.add(item[locale])
        if item.get("enforce"):
            forms.add(item[other])
            forms.update(item.get("reject", {}).get(locale, []))
    return forms


def regional_pairs(locale):
    """Wrong-locale vocabulary written in the requested locale's own script."""
    if locale in _regional_cache:
        return _regional_cache[locale]
    phrase_file, table, characters = REGIONAL_TABLES[locale]
    convert = character_map(characters)
    excluded_forms = maintained_forms(locale)
    excluded_forms.update(RULES["regional_exceptions"].get(locale, []))
    pairs = {}
    for key, value in conversion_pairs(phrase_file, table):
        wrong = "".join(convert.get(character, character) for character in key)
        if (len(wrong) < 2 or wrong == value or wrong in excluded_forms
                or wrong in pairs or value in wrong or wrong in value):
            continue
        pairs[wrong] = value
    _regional_cache[locale] = pairs
    return pairs


def longer_words(terms):
    """Dictionary words that contain a flagged term and are longer than it."""
    key = frozenset(terms)
    if key in _word_cache:
        return _word_cache[key]
    words = {form for item in TECHNICAL_TERMS
             for form in (item["zh-CN"], item["zh-TW"])}
    words.update(PRESERVED_TERMS)
    if terms:
        pattern = re.compile("|".join(sorted(map(re.escape, terms), key=len, reverse=True)))
        shortest = min(len(term) for term in terms)
        for path, columns in WORD_CORPORA:
            if not path.exists():
                continue
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("#"):
                        continue
                    fields = line.split()
                    for column in columns:
                        if column >= len(fields):
                            continue
                        word = fields[column]
                        if len(word) > shortest and pattern.search(word):
                            words.add(word)
    _word_cache[key] = words
    return words


def contained_in_longer_word(text, start, end, words):
    for word in words:
        if len(word) <= end - start:
            continue
        window = text[max(0, end - len(word)):start + len(word)]
        if word in window:
            return True
    return False


def regional_findings(text, locale):
    if locale not in REGIONAL_TABLES:
        return []
    matches = []
    for wrong, preferred in regional_pairs(locale).items():
        start = 0
        while True:
            at = text.find(wrong, start)
            if at < 0:
                break
            matches.append((at, wrong, preferred))
            start = at + len(wrong)
    if not matches:
        return []
    words = longer_words({wrong for _, wrong, _ in matches})
    return [issue("terminology.regional", line_number(text, at),
             f"regional vocabulary: use {preferred} in {locale}", wrong)
            for at, wrong, preferred in matches
            if not contained_in_longer_word(text, at, at + len(wrong), words)]


def python_comments(text):
    out = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(text).readline)
        out.extend((tok.start[0], tok.string[1:].strip()) for tok in tokens
                   if tok.type == tokenize.COMMENT)
    except (IndentationError, tokenize.TokenError):
        pass
    try:
        tree = ast.parse(text)
        nodes = [tree, *(node for node in ast.walk(tree)
                          if isinstance(node, (ast.ClassDef, ast.FunctionDef,
                                               ast.AsyncFunctionDef)))]
        for node in nodes:
            if not node.body:
                continue
            first = node.body[0]
            if (isinstance(first, ast.Expr)
                    and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                out.append((first.lineno, first.value.value))
    except (SyntaxError, ValueError):
        pass
    return out


def inside_parameter_expansion(line, index):
    return line.rfind("${", 0, index) > line.rfind("}", 0, index)


def heredoc_delimiter(line):
    match = re.search(r"(?:^|[;&|()\s])<<(-?)(?!<)[ \t]*(?:['\"]([^'\"]+)['\"]|([^\s;&|()]+))",
                      line)
    if not match:
        return None
    delimiter = match.group(2) or match.group(3)
    delimiter = re.sub(r"\\(.)", r"\1", delimiter)
    return delimiter, bool(match.group(1))


def mask_toml_multiline(line, delimiter):
    """Mask TOML multiline strings and return the active delimiter."""
    chars = list(line)
    index = 0
    if delimiter:
        end = line.find(delimiter)
        if end < 0:
            return " " * len(line), delimiter
        chars[:end + len(delimiter)] = " " * (end + len(delimiter))
        index = end + len(delimiter)
        delimiter = None
    while index < len(line):
        candidates = [(line.find(marker, index), marker)
                      for marker in ('"""', "'''")]
        candidates = [(at, marker) for at, marker in candidates if at >= 0]
        if not candidates:
            break
        start, marker = min(candidates)
        end = line.find(marker, start + len(marker))
        if end < 0:
            chars[start:] = " " * (len(line) - start)
            delimiter = marker
            break
        end += len(marker)
        chars[start:end] = " " * (end - start)
        index = end
    return "".join(chars), delimiter


def hash_comments(text, dialect="generic"):
    out = []
    heredoc = None
    yaml_indent = None
    toml_delimiter = None
    for number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line
        if dialect == "shell" and heredoc:
            delimiter, strip_tabs = heredoc
            candidate = line.lstrip("\t") if strip_tabs else line
            if candidate == delimiter:
                heredoc = None
            continue
        if dialect == "yaml" and yaml_indent is not None:
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip(" "))
            if indent > yaml_indent:
                continue
            yaml_indent = None
        if dialect == "toml":
            line, toml_delimiter = mask_toml_multiline(line, toml_delimiter)
        quote = None
        escaped = False
        for index, char in enumerate(line):
            if escaped:
                escaped = False
                continue
            if char == "\\" and quote != "'":
                escaped = True
                continue
            if quote:
                if char == quote:
                    quote = None
                continue
            if char in "'\"`":
                quote = char
                continue
            if char == "#":
                if index == 0 and line.startswith("#!"):
                    break
                if dialect == "shell" and inside_parameter_expansion(line, index):
                    continue
                if (index and not line[index - 1].isspace()
                        and not (dialect == "shell"
                                 and line[index - 1] in ";&|(){}")):
                    continue
                out.append((number, line[index + 1:].strip()))
                break
        if dialect == "shell":
            heredoc = heredoc_delimiter(line)
        elif dialect == "yaml" and re.search(
                r":\s*[|>]\s*(?:[1-9][+-]?|[+-][1-9]?)?\s*(?:#.*)?$", line):
            yaml_indent = len(line) - len(line.lstrip(" "))
    return out


def c_like_comments(text, line_comments=True, nested=False):
    out = []
    index = 0
    line = 1
    quote = None
    escaped = False
    while index < len(text):
        char = text[index]
        nxt = text[index + 1] if index + 1 < len(text) else ""
        if char == "\n":
            line += 1
        if escaped:
            escaped = False
            index += 1
            continue
        if quote:
            if char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in "'\"`":
            quote = char
            index += 1
            continue
        if line_comments and char == "/" and nxt == "/":
            end = text.find("\n", index + 2)
            end = len(text) if end < 0 else end
            out.append((line, text[index + 2:end].strip()))
            index = end
            continue
        if char == "/" and nxt == "*":
            start_line = line
            end = index + 2
            depth = 1
            while end < len(text) - 1 and depth:
                if nested and text[end:end + 2] == "/*":
                    depth += 1
                    end += 2
                elif text[end:end + 2] == "*/":
                    depth -= 1
                    if depth:
                        end += 2
                else:
                    end += 1
            if depth:
                end = len(text) - 2
            body = text[index + 2:end]
            out.append((start_line, body))
            line += body.count("\n")
            index = end + 2
            continue
        index += 1
    return out


JS_TEMPLATE_SUFFIXES = {".cjs", ".js", ".jsx", ".mjs", ".mts", ".ts", ".tsx"}


def template_expression_comments(text):
    """Extract comments from JavaScript template expressions."""
    out = []
    template = re.compile(r"`(?:\\.|[^`])*`", re.S)
    expression = re.compile(r"\$\{([\s\S]*)\}")
    for template_match in template.finditer(text):
        value = template_match.group(0)
        for match in expression.finditer(value):
            start = template_match.start() + match.start(1)
            base_line = line_number(text, start) - 1
            out.extend((base_line + line, comment)
                       for line, comment in c_like_comments(match.group(1)))
    return out


def html_comments(text):
    out = []
    for match in re.finditer(r"<!--([\s\S]*?)-->", text):
        out.append((line_number(text, match.start()), match.group(1)))
    return out


def dash_comments(text):
    out = []
    for number, line in enumerate(text.splitlines(), 1):
        quote = None
        escaped = False
        index = 0
        while index < len(line) - 1:
            char = line[index]
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif quote:
                if char == quote:
                    quote = None
            elif char in "'\"`":
                quote = char
            elif line[index:index + 2] == "--":
                out.append((number, line[index + 2:].strip()))
                break
            index += 1
    return out


def markdown_fence_comments(text):
    suffixes = {
        "bash": ".sh", "c": ".c", "cpp": ".cpp", "css": ".css",
        "go": ".go", "html": ".html", "javascript": ".js", "js": ".js",
        "jsonc": ".js", "jsx": ".jsx", "lua": ".lua", "php": ".php", "python": ".py",
        "rb": ".rb", "ruby": ".rb", "rust": ".rs", "sh": ".sh",
        "shell": ".sh", "sql": ".sql", "toml": ".toml", "ts": ".ts", "tsx": ".tsx",
        "typescript": ".ts", "xml": ".xml", "yaml": ".yaml", "yml": ".yml",
        "zsh": ".sh",
    }
    out = []
    lines = text.splitlines(keepends=True)
    index = 0
    while index < len(lines):
        opening = re.match(r"^ {0,3}(`{3,}|~{3,})([^\n]*)$",
                           lines[index].rstrip("\r\n"))
        if not opening:
            index += 1
            continue
        marker = opening.group(1)
        info = opening.group(2).strip()
        if info.startswith("{"):
            language = re.search(r"(?:^|[\s{])\.([A-Za-z0-9_+-]+)(?=[\s}])", info)
        else:
            language = re.match(r"([A-Za-z0-9_+-]+)", info)
        suffix = suffixes.get(language.group(1).lower()) if language else None
        if not suffix:
            index += 1
            continue
        close = index + 1
        closing = re.compile(rf"^ {{0,3}}{re.escape(marker[0])}{{{len(marker)},}}\s*$")
        while close < len(lines) and not closing.match(lines[close].rstrip("\r\n")):
            close += 1
        if close >= len(lines):
            break
        body = "".join(lines[index + 1:close])
        virtual_path = pathlib.Path(f"fence{suffix}")
        for number, comment in comments_for(virtual_path, body):
            out.append((index + 1 + number, comment))
        index = close + 1
    return out


def comments_for(path, text):
    out = []
    suffix = path.suffix.lower()
    if suffix in {".py", ".pyi"}:
        out.extend(python_comments(text))
    if suffix in HASH_COMMENT_SUFFIXES or path.name in HASH_COMMENT_NAMES:
        dialect = "shell" if (suffix in {".bash", ".ebuild", ".eclass", ".fish",
                                          ".ksh", ".sh", ".zsh"}
                              or (not path.suffix and text.startswith("#!"))) else "generic"
        if suffix in {".yaml", ".yml"}:
            dialect = "yaml"
        elif suffix == ".toml":
            dialect = "toml"
        out.extend(hash_comments(text, dialect))
    if not path.suffix and text.startswith("#!"):
        out.extend(hash_comments(text, "shell"))
    if suffix in CL_COMMENT_SUFFIXES:
        out.extend(c_like_comments(text, nested=suffix in {".rs", ".swift"}))
    if suffix == ".css":
        out.extend(c_like_comments(text, line_comments=False))
    if suffix in JS_TEMPLATE_SUFFIXES:
        out.extend(template_expression_comments(text))
    if suffix in {".lua", ".sql"}:
        out.extend(dash_comments(text))
    if suffix in HTML_COMMENT_SUFFIXES:
        out.extend(html_comments(text))
    if suffix in {".markdown", ".md", ".mdx"}:
        out.extend(markdown_fence_comments(text))
    return sorted(set(out))


def obvious_comment_findings(path, text):
    """Report high-confidence comments that only narrate adjacent syntax."""
    patterns = (
        (re.compile(r"^(?:建立|\u521b\u5efa|初始化)(?:一個|\u4e00\u4e2a)?空(?:列表|清單|字典|集合|陣列|\u6570\u7ec4)"),
         re.compile(r"^[A-Za-z_][\w.\[\]]*\s*=\s*(?:\[\]|\{\}|list\(\)|dict\(\)|set\(\))")),
        (re.compile(r"^(?:遍歷|\u904d\u5386)(?:所有|每個|\u6bcf\u4e2a)"), re.compile(r"^(?:async\s+)?for\b")),
        (re.compile(r"^(?:如果|若).*(?:跳過|\u8df3\u8fc7|返回|回傳|\u56de\u4f20)"), re.compile(r"^if\b")),
        (re.compile(r"^(?:返回|回傳|\u56de\u4f20)(?:結果|\u7ed3\u679c|值|資料|\u6570\u636e)?[。.]?$"),
         re.compile(r"^return\b")),
    )
    lines = text.splitlines()
    out = []
    for line, comment in comments_for(path, text):
        if not (1 <= line <= len(lines)):
            continue
        source = lines[line - 1].lstrip()
        if not source.startswith(("#", "//", "/*", "*")):
            continue
        following = ""
        for candidate in lines[line:]:
            if candidate.strip():
                following = candidate.strip()
                break
        value = re.sub(r"^\s*[*#/]+\s*", "", comment).strip()
        if any(comment_pattern.search(value) and code_pattern.search(following)
               for comment_pattern, code_pattern in patterns):
            out.append(issue(
                "comments.obvious", line,
                "remove the comment that only restates the adjacent code",
                value[:48], severity="warning"))
    return out


def excluded(path, patterns, explicit=False):
    try:
        if not explicit and path.resolve() in INTERNAL_RULE_FILES:
            return True
    except OSError:
        pass
    value = path.as_posix()
    return any(fnmatch.fnmatch(value, pattern) or fnmatch.fnmatch(path.name, pattern)
               for pattern in patterns)


def is_utf8_text(path):
    try:
        with path.open("rb") as handle:
            data = handle.read(8192)
        if b"\0" in data:
            return False
        data.decode("utf-8")
        return True
    except (OSError, UnicodeDecodeError):
        return False


def known_text_path(path):
    suffixes = (HASH_COMMENT_SUFFIXES | CL_COMMENT_SUFFIXES | HTML_COMMENT_SUFFIXES
                | DATA_SUFFIXES | PROSE_SUFFIXES
                | {".css", ".lua", ".py", ".pyi", ".sql"})
    return path.suffix.lower() in suffixes or path.name in HASH_COMMENT_NAMES


def files_from(paths, patterns):
    for raw in paths:
        if raw == "-":
            yield pathlib.Path("-")
            continue
        path = pathlib.Path(raw)
        if path.is_file():
            if not excluded(path, patterns, explicit=True):
                yield path
            continue
        if not path.is_dir():
            continue
        for directory, dirnames, filenames in os.walk(path):
            dirnames[:] = sorted(name for name in dirnames if name not in SKIP_DIRS)
            for filename in sorted(filenames):
                candidate = pathlib.Path(directory, filename)
                if excluded(candidate, patterns):
                    continue
                if known_text_path(candidate) or is_utf8_text(candidate):
                    yield candidate


def paragraph_unit_findings(paragraph, line, limit, style="standard"):
    if not CJK.search(paragraph):
        return []
    compact = re.sub(r"\s", "", paragraph)
    out = []
    style_policy = RULES["style_profiles"][style]
    paragraph_limit = limit if limit is not None else style_policy["paragraph_characters"]
    sentence_count_limit = style_policy["paragraph_sentences"]
    if paragraph_limit and len(compact) > paragraph_limit:
        out.append(issue(
            "length.paragraph", line,
            f"paragraph exceeds {paragraph_limit} non-space characters", compact[:24]))
    if (sentence_count_limit
            and len(SENTENCE_END.findall(paragraph)) > sentence_count_limit):
        out.append(issue(
            "length.paragraph-sentences", line,
            f"paragraph exceeds {sentence_count_limit} sentences", compact[:24]))
    sentence_limit = style_policy["sentence_characters"]
    clause_limit = style_policy["clause_markers"]
    for match in SENTENCE.finditer(paragraph):
        sentence = match.group(0).strip()
        if not CJK.search(sentence):
            continue
        sample = re.sub(r"\s", "", sentence)
        sentence_line = line + paragraph.count("\n", 0, match.start())
        if sentence_limit and len(sample) > sentence_limit:
            out.append(issue(
                "length.sentence", sentence_line,
                f"sentence exceeds {sentence_limit} non-space characters", sample[:24]))
        markers = len(re.findall(r"[，；：,;:]", sentence))
        markers += len(CLAUSE_CONNECTORS.findall(sentence))
        if clause_limit and markers >= clause_limit:
            out.append(issue(
                "structure.complex-sentence", sentence_line,
                "split the sentence into direct claims and conditions", sample[:24]))
    return out


def repeated_sentence_findings(text):
    minimum = RULES["repeated_sentence_characters"]
    seen = set()
    out = []
    for match in SENTENCE.finditer(text):
        sentence = match.group(0).strip()
        if not sentence.endswith(tuple("。！？!?")):
            continue
        normalized = re.sub(r"[\s`*_>#-]", "", sentence)
        if len(normalized) < minimum or not CJK.search(normalized):
            continue
        if normalized in seen:
            out.append(issue(
                "structure.repeated-sentence", line_number(text, match.start()),
                "remove the repeated sentence", normalized[:24]))
        seen.add(normalized)
    return out


def paragraph_findings(text, limit, style="standard"):
    out = []
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end >= 0:
            text = "\n" * text[:end + 5].count("\n") + text[end + 5:]
    for match in re.finditer(r"(?:^|\n\s*\n)([^\n][\s\S]*?)(?=\n\s*\n|$)", text):
        paragraph = match.group(1).strip()
        if not paragraph or re.match(r"(?:```|~~~)", paragraph):
            continue
        base_line = line_number(text, match.start(1))
        lines = paragraph.splitlines()
        if lines[0].startswith("|"):
            for offset, value in enumerate(lines):
                cells = [cell.strip() for cell in value.strip().strip("|").split("|")]
                if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                    continue
                for cell in cells:
                    if CJK.search(cell):
                        out.extend(paragraph_unit_findings(
                            cell, base_line + offset, limit, style))
            continue
        if re.match(r"(?:[-*+]\s|\d+[.)]\s)", lines[0]):
            item = []
            item_line = base_line
            for offset, value in enumerate(lines):
                marker = re.match(r"(?:[-*+]\s|\d+[.)]\s)(.*)", value)
                if marker:
                    if item:
                        out.extend(paragraph_unit_findings(
                            "\n".join(item), item_line, limit, style))
                    item = [marker.group(1)]
                    item_line = base_line + offset
                else:
                    item.append(value)
            if item:
                out.extend(paragraph_unit_findings(
                    "\n".join(item), item_line, limit, style))
            continue
        if lines[0].startswith("#"):
            lines = lines[1:]
            base_line += 1
        paragraph = "\n".join(re.sub(r"^>\s?", "", line) for line in lines).strip()
        if paragraph:
            out.extend(paragraph_unit_findings(paragraph, base_line, limit, style))
    return out


def data_paragraph_findings(text, limit, style="standard"):
    out = []
    for number, line in enumerate(text.splitlines(), 1):
        if CJK.search(line):
            out.extend(paragraph_unit_findings(line.strip(), number, limit, style))
    return out


def json_paragraph_findings(text, limit, style="standard"):
    out = []
    for match in re.finditer(r'"(?P<value>(?:\\.|[^"\\])*)"', text):
        if re.match(r"\s*:", text[match.end():]):
            continue
        try:
            value = json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
        if isinstance(value, str) and CJK.search(value):
            out.extend(paragraph_unit_findings(
                value, line_number(text, match.start()), limit, style))
    return out


def json_prose_text(text):
    """Expose decoded JSON string values while preserving source line offsets."""
    chars = ["\n" if char == "\n" else " " for char in text]
    string = re.compile(r'"(?:\\.|[^"\\])*"')
    for match in string.finditer(text):
        if re.match(r"\s*:", text[match.end():]):
            continue
        try:
            value = json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
        if not isinstance(value, str):
            continue
        value = value.replace("\r", " ").replace("\n", " ")
        available = match.end() - match.start() - 2
        value = value[:available].ljust(available)
        chars[match.start() + 1:match.end() - 1] = value
    return "".join(chars)


def prose_path(path, text):
    suffix = path.suffix.lower()
    if suffix in PROSE_SUFFIXES or suffix in DATA_SUFFIXES:
        return True
    return not path.suffix and not text.startswith("#!")


def subject_findings(subject, profile, label="commit subject"):
    limit = 69 if profile == "gentoo-overlay" else 72
    out = []
    if len(subject) > limit:
        out.append(issue(
            "vcs.subject-length", 1, f"{label} exceeds {limit} characters",
            subject[:32]))
    if subject.rstrip().endswith(tuple("。；，！？、.;,!?：:")):
        out.append(issue(
            "vcs.subject-punctuation", 1,
            f"remove the trailing punctuation from the {label}", subject[-16:]))
    if profile == "gentoo-overlay":
        if CJK.search(subject):
            out.append(issue(
                "overlay.english-subject", 1,
                f"gentoo-zh overlay {label} must be English", subject[:32]))
        if not re.match(r"\S+: \S", subject):
            out.append(issue(
                "overlay.subject-format", 1,
                f"use `scope: summary` for the overlay {label}", subject[:32]))
    return out


def commit_findings(text, profile):
    lines = text.splitlines()
    if not lines or not lines[0].strip():
        return [issue("vcs.empty-subject", 1, "commit subject line is empty")]
    out = subject_findings(lines[0].rstrip(), profile)
    if len(lines) > 1 and lines[1].strip():
        out.append(issue(
            "vcs.subject-body-spacing", 2,
            "leave line 2 blank between subject and body", lines[1][:32]))
    return out


def attribution_findings(text):
    """AI signatures are banned in every file, kind, and profile."""
    out = []
    for pattern in RULES["attribution_patterns"]:
        for match in re.finditer(pattern, text, re.M | re.I):
            out.append(issue(
                "attribution.ai", line_number(text, match.start()),
                "remove the AI attribution; AI signatures are not allowed",
                match.group(0)[:48]))
    return out


def emoji_findings(text, style="standard"):
    if RULES["style_profiles"][style]["emoji"] == "allow":
        return []
    for symbol in RULES.get("emoji_exceptions", {}).get(style, ()):
        text = text.replace(symbol, " " * len(symbol))
    return pattern_findings(
        text, "emoji_patterns", "style.emoji",
        "remove Emoji and state the meaning in text")



def signoff_findings(text):
    out = []
    for pattern in RULES["invalid_signoff_patterns"]:
        for match in re.finditer(pattern, text, re.M | re.I):
            out.append(issue(
                "attribution.invalid-signoff", line_number(text, match.start()),
                "use the contributor's real email in Signed-off-by",
                match.group(0)[:48]))
    return out


def pattern_findings(text, key, code, message):
    out = {}
    for pattern in RULES[key]:
        for match in re.finditer(pattern, text, re.M | re.I):
            line = line_number(text, match.start())
            sample = match.group(0)[:48]
            current = out.get(line, "")
            if len(sample) > len(current):
                out[line] = sample
    return [issue(code, line, message, sample) for line, sample in out.items()]


def authored_pr_text(text):
    positions = [text.find(marker) for marker in RULES["pr_template_markers"]]
    positions = [position for position in positions if position >= 0]
    return text[:min(positions)] if positions else text


def mask_markup_code(text, markdown=False, mask_inline=True):
    """Preserve offsets while excluding fenced and inline code from prose rules."""
    def blank(match):
        return "".join("\n" if char == "\n" else " " for char in match.group(0))

    lines = text.splitlines(keepends=True)
    masked = []
    fence = None
    indented = False
    previous_blank = True
    frontmatter = False
    if markdown and lines:
        first_marker = lines[0].rstrip("\r\n").strip()
        closing_markers = {"---", "..."} if first_marker == "---" else {first_marker}
    else:
        first_marker = ""
        closing_markers = set()
    if first_marker in {"---", "+++"}:
        frontmatter = any(
            candidate.rstrip("\r\n").strip() in closing_markers
            for candidate in lines[1:])
    for line_index, line in enumerate(lines):
        content = line.rstrip("\r\n")
        if frontmatter:
            masked.append(blank(re.match(r"[\s\S]*", line)))
            if line_index and content.strip() in closing_markers:
                frontmatter = False
            continue
        if fence:
            masked.append(blank(re.match(r"[\s\S]*", line)))
            marker, length = fence
            if re.fullmatch(rf" {{0,3}}{re.escape(marker)}{{{length},}}\s*", content):
                fence = None
            continue
        opening = re.match(r"^ {0,3}(`{3,}|~{3,})(?:[^\r\n]*)$", content)
        if opening:
            marker = opening.group(1)
            fence = (marker[0], len(marker))
            masked.append(blank(re.match(r"[\s\S]*", line)))
            previous_blank = False
        elif (markdown and re.match(r"^(?: {4}|\t)\S", line)
              and (indented or previous_blank)):
            masked.append(blank(re.match(r"[\s\S]*", line)))
            indented = True
        else:
            masked.append(line)
            if content.strip():
                indented = False
        previous_blank = not content.strip()
    text = "".join(masked)
    if not mask_inline:
        return text
    chars = list(text)
    index = 0
    while index < len(text):
        if text[index] != "`":
            index += 1
            continue
        end = index
        while end < len(text) and text[end] == "`":
            end += 1
        marker = text[index:end]
        search = end
        closing = -1
        while True:
            candidate = text.find(marker, search)
            if candidate < 0:
                break
            before = candidate == 0 or text[candidate - 1] != "`"
            after_at = candidate + len(marker)
            after = after_at == len(text) or text[after_at] != "`"
            if before and after:
                closing = after_at
                break
            search = candidate + len(marker)
        if closing < 0:
            index = end
            continue
        for position in range(index, closing):
            if chars[position] != "\n":
                chars[position] = " "
        index = closing
    return "".join(chars)


def mask_nonprose_markup(text):
    """Mask links, addresses, and tags while preserving line offsets."""
    def blank(match):
        return "".join("\n" if char == "\n" else " " for char in match.group(0))

    patterns = (
        r"(?is)<(?:code|pre)\b[^>]*>.*?</(?:code|pre)\s*>",
        r"(?<=\])\((?:\\.|[^)\n])*\)",
        r"(?:https?|ftp)://[^\s<>()]+",
        r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        r"\{(?:#[^}\n]+|\.[^}\n]+)\}",
        r"<[^>\n]+>",
    )
    for pattern in patterns:
        text = re.sub(pattern, blank, text)
    return text


def match_sample(text, start, end, width=12):
    left = max(text.rfind("\n", 0, start) + 1, start - width)
    newline = text.find("\n", end)
    right = len(text) if newline < 0 else newline
    right = min(right, end + width)
    return text[left:right].strip()[:48]


def typography_findings(text, style="standard"):
    checked = mask_nonprose_markup(text)
    out = []
    seen = set()

    def add(code, message, match):
        line = line_number(checked, match.start())
        key = (code, line)
        if key in seen:
            return
        seen.add(key)
        out.append(issue(code, line, message,
                         match_sample(checked, match.start(), match.end())))

    for match in re.finditer(r"[０-９Ａ-Ｚａ-ｚ]+", checked):
        add("typography.fullwidth-alphanumeric",
            "use ASCII letters and digits instead of full-width forms", match)
    for match in re.finditer(r"(?<=[0-9０-９])．(?=[0-9０-９])", checked):
        add("typography.fullwidth-decimal",
            "use an ASCII decimal point between digits", match)
    for match in re.finditer(r"([，。；：！？、])\1+", checked):
        add("typography.repeated-punctuation",
            "use one punctuation mark", match)
    for match in re.finditer(r"(?<!\.)\.{3,}(?!\.)", checked):
        line_start = checked.rfind("\n", 0, match.start()) + 1
        line_end = checked.find("\n", match.end())
        line_end = len(checked) if line_end < 0 else line_end
        if CJK.search(checked[line_start:line_end]):
            message = ("use … for a UI state" if style == "ui"
                       else "use …… for an ellipsis in Chinese prose")
            add("typography.ascii-ellipsis", message, match)
    for match in re.finditer(r"(?<![-\w])--(?![-\w])", checked):
        line_start = checked.rfind("\n", 0, match.start()) + 1
        line_end = checked.find("\n", match.end())
        line_end = len(checked) if line_end < 0 else line_end
        if CJK.search(checked[line_start:line_end]):
            add("typography.ascii-dash",
                "use —— for a dash in Chinese prose", match)

    boundary = re.compile(
        rf"(?:[{CJK_CLASS}][A-Za-z0-9]|[A-Za-z0-9][{CJK_CLASS}])")
    for match in boundary.finditer(checked):
        add("typography.cjk-latin-spacing",
            "add one space between Chinese and Latin letters or digits", match)
    return out


def apply_replacements(text, replacements):
    """Apply non-overlapping replacements from right to left."""
    for start, end, value in sorted(replacements, reverse=True):
        text = text[:start] + value + text[end:]
    return text


def fix_matches(text, pattern, replacement, predicate=None, markdown=False):
    """Replace prose matches while retaining protected markup and code."""
    checked = mask_nonprose_markup(mask_markup_code(text, markdown))
    replacements = []
    for match in re.finditer(pattern, checked):
        if predicate and not predicate(checked, match):
            continue
        value = replacement(match) if callable(replacement) else replacement
        replacements.append((match.start(), match.end(), value))
    return apply_replacements(text, replacements)


def chinese_line(checked, match):
    start = checked.rfind("\n", 0, match.start()) + 1
    end = checked.find("\n", match.end())
    end = len(checked) if end < 0 else end
    return bool(CJK.search(checked[start:end]))


def safe_fix_text(path, text, style="standard"):
    """Apply deterministic typography fixes without changing wording."""
    markdown = path.suffix.lower() in {".md", ".markdown", ".mdx"}
    text = fix_matches(
        text, r"[０-９Ａ-Ｚａ-ｚ]+",
        lambda match: unicodedata.normalize("NFKC", match.group(0)),
        markdown=markdown)
    text = fix_matches(
        text, r"(?<=[0-9])．(?=[0-9])", ".", markdown=markdown)
    text = fix_matches(text, r"([，。；：！？、])\1+",
                       lambda match: match.group(1), markdown=markdown)
    text = fix_matches(
        text, r"(?<!\.)\.{3,}(?!\.)",
        lambda _match: "…" if style == "ui" else "……",
        chinese_line, markdown=markdown)
    text = fix_matches(
        text, r"(?<![-\w])--(?![-\w])", "——", chinese_line,
        markdown=markdown)
    punctuation = {",": "，", ".": "。", ";": "；", ":": "：",
                   "!": "！", "?": "？"}
    text = fix_matches(
        text,
        rf"(?<=[{CJK_CLASS}])[,.;:!?]"
        rf"(?=\s|$|[{CJK_CLASS}])",
        lambda match: punctuation[match.group(0)], markdown=markdown)
    cjk = rf"[{CJK_CLASS}]"
    text = fix_matches(
        text, rf"{cjk}(?=[A-Za-z0-9])",
        lambda match: match.group(0) + " ", markdown=markdown)
    text = fix_matches(
        text, rf"(?<=[A-Za-z0-9]){cjk}",
        lambda match: " " + match.group(0), markdown=markdown)
    if path.suffix.lower() in {".md", ".markdown", ".mdx"} and style == "readme":
        checked = mask_markup_code(text, markdown=True)
        replacements = []
        for match in re.finditer(
                r"(?m)^ {0,3}#{1,6}\s+.+?(?P<stop>[。．.])\s*#*\s*$", checked):
            replacements.append((match.start("stop"), match.end("stop"), ""))
        text = apply_replacements(text, replacements)
    return text


def fix_file(path, kind, profile, style):
    """Safely replace one prose file while preserving supported metadata."""
    if path.is_symlink():
        raise OSError("refusing to replace a symbolic link")
    data = path.read_bytes()
    text = data.decode("utf-8")
    if path.suffix.lower() in DATA_SUFFIXES:
        return False
    prose = kind in {"prose", "pr-body", "commit-message"} or (
        kind == "all" and prose_path(path, text))
    if not prose:
        return False
    effective_style = "strict" if profile == "gentoo-overlay" else style
    updated = safe_fix_text(path, text, effective_style)
    if updated == text:
        return False
    metadata = path.stat()
    if metadata.st_nlink != 1:
        raise OSError("refusing to replace a file with multiple hard links")
    if hasattr(os, "geteuid") and metadata.st_uid != os.geteuid():
        raise OSError("refusing to replace a file owned by another user")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="wb", dir=path.parent, prefix=f".{path.name}.",
                delete=False) as handle:
            temporary = pathlib.Path(handle.name)
            handle.write(updated.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        shutil.copystat(path, temporary, follow_symlinks=False)
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return True


def grammar_findings(text, style="standard"):
    """Report only high-confidence 的/得/地 patterns as advisory findings."""
    out = []
    for rule in RULES["grammar_rules"]:
        if not applies_to_style(rule, style):
            continue
        for match in re.finditer(rule["pattern"], text):
            out.append(issue(
                f"grammar.{rule['id']}", line_number(text, match.start()),
                rule["message"], match.group(0), severity="warning"))
    return out


def comparison_line(line):
    """Return whether a line explicitly compares locales or terminology."""
    folded = line.casefold()
    return any(marker.casefold() in folded
               for marker in RULES["comparison_markers"])


def mask_comparison_lines(text):
    """Exclude explicit locale comparisons from locale-specific checks."""
    line_breaks = "\r\n\x85\u2028\u2029"
    return "".join(
        "".join(char if char in line_breaks else " " for char in line)
        if comparison_line(line) else line
        for line in text.splitlines(keepends=True))


def form_occurrences(text, forms):
    """Locate forms outside explicit comparison lines and longer dictionary words."""
    occurrences = []
    longer_forms = {
        form
        for item in TECHNICAL_TERMS
        for form in (
            item["zh-CN"], item["zh-TW"],
            *item.get("reject", {}).get("zh-CN", []),
            *item.get("reject", {}).get("zh-TW", []),
        )
    }
    lines = text.splitlines(keepends=True)
    offset = 0

    def inside_longer_form(position, form):
        for word in longer_forms:
            if len(word) <= len(form):
                continue
            index = word.find(form)
            while index >= 0:
                start = position - index
                if start >= 0 and text.startswith(word, start):
                    return True
                index = word.find(form, index + 1)
        return False

    for line in lines:
        if not comparison_line(line):
            for form in forms:
                start = 0
                while True:
                    at = line.find(form, start)
                    if at < 0:
                        break
                    absolute = offset + at
                    if not inside_longer_form(absolute, form):
                        occurrences.append((absolute, form))
                    start = at + len(form)
        offset += len(line)
    return occurrences


def consistency_findings(text, locale="auto"):
    """Report inconsistent variants without duplicating locale diagnostics."""
    groups = []
    if locale == "auto":
        for item in TECHNICAL_TERMS:
            if not item.get("enforce"):
                continue
            forms = {item["zh-CN"], item["zh-TW"]}
            for values in item.get("reject", {}).values():
                forms.update(values)
            forms.discard("")
            if len(forms) > 1:
                groups.append(("terminology", item["en"], forms))
    for group in RULES["consistency_groups"]:
        groups.append((group["id"], group["id"], set(group["forms"])))

    out = []
    for identifier, subject, forms in groups:
        occurrences = form_occurrences(text, forms)
        used = {}
        for position, form in occurrences:
            used.setdefault(form, position)
        if len(used) < 2:
            continue
        ordered = sorted(used.items(), key=lambda item: item[1])
        later_form, later_position = ordered[1]
        sample = " / ".join(form for form, _ in ordered[:3])
        message = (f"use one form consistently for {subject}"
                   if identifier == "terminology"
                   else "use one written form consistently in this document")
        out.append(issue(
            f"consistency.{identifier}", line_number(text, later_position),
            message, sample, severity="warning"))
    return out


def markdown_findings(path, text, style="standard"):
    if path.suffix.lower() not in {".md", ".markdown", ".mdx"}:
        return []
    out = []
    previous_level = None
    for match in re.finditer(r"(?m)^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$", text):
        level = len(match.group(1))
        title = match.group(2).strip()
        line = line_number(text, match.start())
        if previous_level is not None and level > previous_level + 1:
            out.append(issue(
                "markdown.heading-level", line,
                "do not skip a Markdown heading level", match.group(0).strip()))
        previous_level = level
        if style == "readme" and title.endswith(("。", ".", "．")):
            out.append(issue(
                "markdown.heading-punctuation", line,
                "remove the trailing full stop from the heading", title[:48]))

    generic_links = set(RULES["generic_link_labels"])
    for match in re.finditer(
            r"(?<!!)\[([^]\n]+)\](?:\([^)\n]+\)|\[[^]\n]*\])", text):
        label = re.sub(r"[`*_]", "", match.group(1)).strip()
        if label in generic_links:
            out.append(issue(
                "markdown.generic-link", line_number(text, match.start()),
                "use the action or destination as the link text", label))

    if style not in {"strict", "academic", "technical", "readme"}:
        return out
    groups = []
    current = []
    current_key = None
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.+)$", line)
        if not match:
            if current and re.match(r"^\s{2,}\S", line):
                continue
            if current:
                groups.append(current)
            current = []
            current_key = None
            continue
        key = (len(match.group(1)), bool(re.match(r"\s*\d", line)))
        if current and key != current_key:
            groups.append(current)
            current = []
        current_key = key
        value = match.group(2).strip()
        if CJK.search(value):
            current.append((number, value, bool(re.search(r"[。；！？]$", value))))
    if current:
        groups.append(current)
    for group in groups:
        states = {item[2] for item in group}
        if len(group) > 1 and len(states) > 1:
            first_state = group[0][2]
            mismatch = next(item for item in group[1:] if item[2] != first_state)
            out.append(issue(
                "markdown.list-punctuation", mismatch[0],
                "keep list-item ending punctuation consistent", mismatch[1][:48]))
    return out


def ui_surface_findings(path, text, checked_text, locale="auto"):
    out = []
    seen = set()

    def add_surface(start, value, surface):
        value = html.unescape(value).strip()
        surface_findings = [
            *emoji_findings(value, "ui"),
            *phrase_findings(value, "ui"),
            *typography_findings(value, "ui"),
            *grammar_findings(value, "ui"),
            *locale_findings(value, locale),
            *terminology_findings(value, locale),
        ]
        for finding in surface_findings:
            out.append(dataclasses.replace(
                finding, line=line_number(text, start) + finding.line - 1))
        if not CJK.search(value) or not re.search(r"[。；，！？.!?;,:：]$", value):
            return
        line = line_number(text, start)
        key = (line, value)
        if key in seen:
            return
        seen.add(key)
        out.append(issue(
            "ui.control-punctuation", line,
            f"remove terminal punctuation from the {surface}", value[:48]))

    suffix = path.suffix.lower()
    if suffix in {".htm", ".html", ".jsx", ".mdx", ".svelte", ".tsx", ".vue"}:
        attribute = re.compile(
            r"(?P<name>alt|title|placeholder|aria-label)\s*=\s*"
            r"(?P<quote>['\"])(?P<value>.*?)(?P=quote)", re.I)
        for match in attribute.finditer(text):
            add_surface(match.start("value"), match.group("value"),
                        match.group("name").lower())
        button = re.compile(
            r"<(?P<tag>button)\b[^>]*>(?P<value>[\s\S]*?)</(?P=tag)\s*>", re.I)
        for match in button.finditer(text):
            raw_value = match.group("value")
            offset_text = re.sub(r"<[^>]+>",
                                 lambda item: " " * len(item.group(0)), raw_value)
            content = CJK.search(offset_text)
            value = re.sub(r"<[^>]+>", "", raw_value)
            start = match.start("value") + (content.start() if content else 0)
            add_surface(start, value, "button label")

    if suffix == ".json":
        pair = re.compile(
            r'"(?P<key>[^"\\]+)"\s*:\s*"(?P<value>(?:\\.|[^"\\])*)"')
        surface_key = re.compile(
            r"(?:alt|aria[-_.]?label|button|command|field[-_.]?label|label|menu|"
            r"placeholder|tab|title|tooltip)$", re.I)
        for match in pair.finditer(text):
            if surface_key.search(match.group("key")):
                try:
                    value = json.loads(f'"{match.group("value")}"')
                except json.JSONDecodeError:
                    value = match.group("value")
                add_surface(match.start("value"), value, "UI label")

    if suffix in {".yaml", ".yml"}:
        pair = re.compile(
            r"(?m)^\s*(?P<key>[A-Za-z0-9_.-]+):\s*"
            r"(?P<value>[^#\n]+?)\s*$")
        surface_key = re.compile(
            r"(?:alt|aria[-_.]?label|button|command|field[-_.]?label|label|menu|"
            r"placeholder|tab|title|tooltip)$", re.I)
        for match in pair.finditer(text):
            if surface_key.search(match.group("key")):
                value = match.group("value").strip().strip("'\"")
                add_surface(match.start("value"), value, "UI label")

    for match in re.finditer(
            rf"[{CJK_CLASS}][！!]", checked_text):
        out.append(issue(
            "ui.exclamation", line_number(checked_text, match.start()),
            "remove the exclamation mark from UI text", match.group(0)))
    return out


def pr_body_findings(text, profile, title, style="standard"):
    policy = "gentoo-overlay" if profile == "gentoo-overlay" else style
    if policy not in RULES["pr_body_limits"]:
        policy = "standard"
    limits = RULES["pr_body_limits"][policy]
    compact = re.sub(r"\s", "", text)
    out = []
    if limits["characters"] and len(compact) > limits["characters"]:
        out.append(issue(
            "vcs.pr-length", 1,
            f"PR description exceeds {limits['characters']} non-space characters",
            compact[:32]))

    blocks = []
    for match in re.finditer(r"(?:^|\n\s*\n)([^\n][\s\S]*?)(?=\n\s*\n|$)", text):
        value = match.group(1).strip()
        if value and not re.fullmatch(r"Closes\s+#\d+\.?", value, re.I):
            blocks.append((line_number(text, match.start(1)), value))
    if limits["blocks"] and len(blocks) > limits["blocks"]:
        out.append(issue(
            "vcs.pr-blocks", blocks[limits["blocks"]][0],
            f"PR description exceeds {limits['blocks']} semantic blocks",
            blocks[limits["blocks"]][1][:32]))

    list_items = list(re.finditer(r"(?m)^\s*(?:[-*+]|\d+[.)])\s+\S", text))
    if limits["list_items"] and len(list_items) > limits["list_items"]:
        match = list_items[limits["list_items"]]
        out.append(issue(
            "vcs.pr-list-items", line_number(text, match.start()),
            f"PR description exceeds {limits['list_items']} list items",
            match.group(0).strip()))

    heading = re.search(r"(?m)^\s*#{1,6}\s+\S", text)
    if heading and not limits["headings"]:
        out.append(issue(
            "vcs.pr-heading", line_number(text, heading.start()),
            "omit headings from the PR description; state the rationale directly",
            heading.group(0).strip()[:48]))
    out.extend(pattern_findings(
        text, "pr_inventory_patterns", "vcs.pr-inventory",
        "replace the change inventory with the non-inferable rationale"))
    if title and title.strip() and title.strip().casefold() in text.casefold():
        at = text.casefold().find(title.strip().casefold())
        out.append(issue(
            "vcs.repeated-title", line_number(text, at),
            "do not repeat the PR title in the body", title.strip()[:48]))
    return out


def lint_file(path, kind, profile, title, paragraph_limit, locale="auto",
              regional=False, style="standard", stdin_filename=None,
              comment_audit=False, extra_terms=None):
    try:
        text = (sys.stdin.read() if str(path) == "-"
                else path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        return [issue("io.read", 0, f"cannot read text: {error}")]
    context_path = (pathlib.Path(stdin_filename)
                    if str(path) == "-" and stdin_filename else path)
    effective_style = "strict" if profile == "gentoo-overlay" else style
    checked_text = authored_pr_text(text) if kind == "pr-body" else text
    name_text = checked_text
    prose = kind in {"prose", "pr-body", "commit-message"} or (
        kind == "all" and prose_path(context_path, text))
    if prose:
        markdown = context_path.suffix.lower() in {".md", ".markdown", ".mdx"}
        name_text = mask_markup_code(name_text, markdown, mask_inline=False)
        checked_text = mask_markup_code(checked_text, markdown)
    suffix = context_path.suffix.lower()
    rule_text = mask_nonprose_markup(checked_text)
    if prose and suffix == ".json":
        rule_text = json_prose_text(checked_text)
    findings = attribution_findings(text)
    findings.extend(emoji_findings(rule_text, effective_style))
    findings.extend(phrase_findings(rule_text, effective_style))
    if prose:
        findings.extend(typography_findings(rule_text, effective_style))
        findings.extend(grammar_findings(rule_text, effective_style))
        findings.extend(consistency_findings(rule_text, locale))
        findings.extend(markdown_findings(
            context_path, checked_text, effective_style))
    if effective_style == "ui":
        findings.extend(ui_surface_findings(
            context_path, text, checked_text, locale))
    findings.extend(locale_findings(rule_text, locale))
    findings.extend(terminology_findings(rule_text, locale))
    findings.extend(preserved_translation_findings(
        mask_nonprose_markup(name_text), rule_text, extra_terms))
    if regional:
        findings.extend(regional_findings(rule_text, locale))
    if kind in {"all", "source"}:
        comment_language = RULES["style_profiles"][effective_style]["comment_language"]
        if comment_language == "english":
            for line, comment in comments_for(context_path, text):
                match = CJK.search(comment)
                if match:
                    comment_line = line + comment.count("\n", 0, match.start())
                    findings.append(
                        issue("comments.language", comment_line,
                              "code comments must be concise English",
                              comment.strip()[:32]))
        if comment_audit:
            findings.extend(obvious_comment_findings(context_path, text))
    if prose:
        if suffix == ".json":
            paragraph_checker = json_paragraph_findings
            length_text = checked_text
        elif suffix in DATA_SUFFIXES:
            paragraph_checker = data_paragraph_findings
            length_text = checked_text
        else:
            paragraph_checker = paragraph_findings
            length_text = mask_nonprose_markup(checked_text)
        findings.extend(paragraph_checker(
            length_text, paragraph_limit, effective_style))
        findings.extend(repeated_sentence_findings(length_text))
    if kind == "commit-message":
        findings.extend(commit_findings(text, profile))
    if kind in {"pr-body", "commit-message"}:
        findings.extend(pattern_findings(
            checked_text, "routine_passing_patterns", "vcs.routine-tests",
            "omit routine passing test reports from commit and PR text"))
        findings.extend(pattern_findings(
            checked_text, "workflow_narration_patterns", "vcs.work-diary",
            "replace the work diary or completion claim with the verified rationale"))
        findings.extend(pattern_findings(
            checked_text, "author_narration_patterns", "vcs.author-narration",
            "remove the author's work narration and state the repository fact"))
    if kind == "pr-body":
        findings.extend(pr_body_findings(
            checked_text, profile, title, effective_style))
    if profile == "gentoo-overlay" and kind in {"pr-body", "commit-message"}:
        findings.extend(signoff_findings(text))
        if kind == "pr-body":
            if title is None:
                findings.append(
                    issue("overlay.missing-title", 0,
                          "--title is required for the gentoo-overlay profile"))
            else:
                findings.extend(dataclasses.replace(item, line=0)
                                for item in subject_findings(
                                    title, profile, "PR title"))
    return sorted(set(findings))


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Check Chinese wording with selectable style and repository rules.")
    parser.add_argument("paths", nargs="+",
                        help="files or directories to inspect; use - for standard input")
    parser.add_argument("--kind",
                        choices=("all", "source", "prose", "pr-body", "commit-message"),
                        default="all", help="rules for the inspected text")
    parser.add_argument("--profile", choices=("general", "gentoo-overlay"),
                        default="general", help="repository-specific rules")
    parser.add_argument("--style", choices=tuple(RULES["style_profiles"]),
                        default="standard", help="writing style and strictness")
    parser.add_argument("--title", help="PR title used with --kind pr-body")
    parser.add_argument("--exclude", action="append", default=[],
                        help="glob to exclude; may be repeated")
    parser.add_argument("--paragraph-limit", type=int,
                        help="override the style's prose paragraph limit")
    parser.add_argument("--locale",
                        choices=("auto", "zh-CN", "zh-TW", "zh-HK", "zh-SG", "zh-MY"),
                        default="auto", help="required Chinese locale or automatic mixing check")
    parser.add_argument("--regional", action="store_true",
                        help="also report regional vocabulary from the bundled "
                             "conversion tables; requires --locale")
    parser.add_argument("--format", choices=("text", "json"), default="text",
                        dest="output_format",
                        help="diagnostic output format")
    parser.add_argument("--fail-level", choices=("error", "warning"),
                        default="error",
                        help="lowest finding severity that makes the command fail")
    parser.add_argument("--fix", action="store_true",
                        help="apply deterministic typography fixes to prose files")
    parser.add_argument("--stdin-filename",
                        help="filename used to select rules for standard input")
    parser.add_argument("--terms",
                        help="project JSON file whose preserve_translations entries "
                             "extend or override the bundled guarded names")
    parser.add_argument("--comment-audit", action="store_true",
                        help="report high-confidence comments that narrate adjacent code")
    args = parser.parse_args()
    if args.regional and args.locale not in {"zh-CN", "zh-TW"}:
        parser.error("--regional requires --locale zh-CN or --locale zh-TW")
    if args.paragraph_limit is not None and args.paragraph_limit < 1:
        parser.error("--paragraph-limit must be greater than zero")
    if args.stdin_filename and "-" not in args.paths:
        parser.error("--stdin-filename requires standard input")
    if args.paths.count("-") > 1:
        parser.error("standard input may be specified only once")
    extra_terms = None
    if args.terms:
        try:
            extra_terms = load_terms(args.terms)
        except (OSError, UnicodeDecodeError, ValueError) as error:
            parser.error(f"cannot read --terms file: {error}")

    patterns = args.exclude
    missing = [raw for raw in args.paths
               if raw != "-" and not pathlib.Path(raw).exists()]
    paths = list(files_from(args.paths, patterns))
    if args.fix and any(str(path) == "-" for path in paths):
        parser.error("--fix does not accept standard input")
    results = [(raw, issue("input.missing", 0, "input path does not exist"))
               for raw in missing]
    fixed = []
    for path in paths:
        label = (args.stdin_filename or "stdin"
                 if str(path) == "-" else str(path))
        if args.fix:
            try:
                if fix_file(path, args.kind, args.profile, args.style):
                    fixed.append(label)
            except (OSError, UnicodeDecodeError) as error:
                results.append((label, issue(
                    "io.write", 0, f"cannot update text: {error}")))
        for finding in lint_file(
                path, args.kind, args.profile, args.title, args.paragraph_limit,
                args.locale, args.regional, args.style, args.stdin_filename,
                args.comment_audit, extra_terms):
            results.append((label, finding))
    if args.output_format == "json":
        payload = {
            "version": 1,
            "count": len(results),
            "findings": [
                {
                    "path": label,
                    "line": finding.line,
                    "code": finding.code,
                    "severity": finding.severity,
                    "message": finding.message,
                    "sample": finding.sample,
                }
                for label, finding in results
            ],
        }
        if args.fix:
            payload["fixed"] = fixed
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for label in fixed:
            print(f"fixed {label}")
        for label, finding in results:
            where = f"{label}:{finding.line}" if finding.line else label
            detail = f" [{finding.sample}]" if finding.sample else ""
            print(f"{where}: {finding.message}{detail}")
    failed = any(finding.severity == "error" or args.fail_level == "warning"
                 for _, finding in results)
    if failed:
        if args.output_format == "text":
            print(f"{len(results)} finding(s)", file=sys.stderr)
        return 1
    if results:
        if args.output_format == "text":
            print(f"{len(results)} advisory finding(s)", file=sys.stderr)
        return 0
    if args.output_format == "text":
        print("Chinese wording check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
