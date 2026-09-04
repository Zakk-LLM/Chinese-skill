#!/usr/bin/env python3
"""Regression tests for chinese_lint.py."""

import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from functools import partial


sys.dont_write_bytecode = True
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")
TARGET = pathlib.Path(__file__).with_name("chinese_lint.py")
SPEC = importlib.util.spec_from_file_location("chinese_lint", TARGET)
LINT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LINT)
strict_lint_file = partial(LINT.lint_file, style="strict")
run = partial(subprocess.run, encoding="utf-8")
FIXTURES = json.loads((TARGET.parent.parent / "references" /
                       "copy-fixtures.json").read_text(encoding="utf-8"))


class Utf8Path(type(pathlib.Path())):
    def read_text(self, encoding="utf-8", errors=None):
        return super().read_text(encoding=encoding, errors=errors)

    def write_text(self, data, encoding="utf-8", errors=None, newline=None):
        return super().write_text(
            data, encoding=encoding, errors=errors, newline=newline)


def check(name, condition):
    global failures
    print(f"{'PASS' if condition else 'FAIL'} {name}")
    failures += not condition


failures = 0
with tempfile.TemporaryDirectory() as base:
    root = Utf8Path(base)
    good = root / "good.sh"
    good.write_text("# Preserve the old generation until validation succeeds.\n"
                    "echo \"服務正在運行\"\n")
    bad_comment = root / "bad-comment.py"
    bad_comment.write_text("# " + FIXTURES["bad_comment"] + "\nvalue = 1\n")
    bad_prose = root / "bad.txt"
    bad_prose.write_text(FIXTURES["bad_prose"] + "\n")
    mixed_locale = root / "mixed.txt"
    mixed_locale.write_text(FIXTURES["mixed_locale"] + "\n")
    wrong_region = root / "wrong-region.txt"
    wrong_region.write_text(FIXTURES["wrong_region"] + "\n")
    markdown = root / "example.md"
    markdown.write_text("```sh\n# " + FIXTURES["bad_comment"] + "\necho ok\n```\n")
    sql = root / "query.sql"
    sql.write_text("SELECT 1; -- " + FIXTURES["bad_comment"] + "\n")
    executable = root / "check"
    executable.write_text("#!/bin/sh\n# " + FIXTURES["bad_comment"] + "\ntrue\n")
    docstring = root / "docstring.py"
    docstring.write_text('"""' + FIXTURES["bad_comment"] + '"""\n')
    tilde_markdown = root / "tilde.md"
    tilde_markdown.write_text("~~~sh\n# " + FIXTURES["bad_comment"] + "\n~~~\n")
    gitignore = root / ".gitignore"
    gitignore.write_text("# " + FIXTURES["bad_comment"] + "\n*.pyc\n")
    body = root / "body.txt"
    body.write_text("因為執行期需要 libfoo.so，所以增加 `dev-libs/libfoo`。\n")

    check("professional source", not strict_lint_file(good, "source", "general", None, 280))
    check("Chinese comment", any("comments" in item[1]
                                 for item in strict_lint_file(
                                     bad_comment, "source", "general", None, 280)))
    prose_findings = strict_lint_file(bad_prose, "prose", "general", None, 280)
    check("discourse filler", any("filler" in item[1] for item in prose_findings))
    check("colloquial run", any("ongoing state" in item[1]
                                 for item in prose_findings))
    check("mixed locale", any("mix Traditional" in item[1]
                               for item in strict_lint_file(
                                   mixed_locale, "prose", "general", None, 280)))
    check("regional terminology", any("software" in item[1]
                                       for item in strict_lint_file(
                                           wrong_region, "prose", "general", None,
                                           280, "zh-TW")))
    check("Markdown fenced comment", any("comments" in item[1]
                                          for item in strict_lint_file(
                                              markdown, "source", "general", None, 280)))
    check("SQL comment", any("comments" in item[1]
                              for item in strict_lint_file(
                                  sql, "source", "general", None, 280)))
    check("extensionless shell comment", any("comments" in item[1]
                                              for item in strict_lint_file(
                                                  executable, "source", "general",
                                                  None, 280)))
    check("Python docstring", any("comments" in item[1]
                                   for item in strict_lint_file(
                                       docstring, "source", "general", None, 280)))
    check("tilde fenced comment", any("comments" in item[1]
                                       for item in strict_lint_file(
                                           tilde_markdown, "source", "general",
                                           None, 280)))
    check("dotfile comment", any("comments" in item[1]
                                  for item in strict_lint_file(
                                      gitignore, "source", "general", None, 280)))
    check("overlay body", not strict_lint_file(
        body, "pr-body", "gentoo-overlay", "cat/pkg: add dependency", 280))
    check("overlay Chinese title", any("title must be English" in item[1]
                                       for item in strict_lint_file(
                                           body, "pr-body", "gentoo-overlay",
                                           "套件：增加依賴", 280)))

    commit = root / "commit.txt"
    commit.write_text("app-misc/foo: add 1.2.3\n\n"
                      "因為 1.2.2 無法連結 libfoo.so.3，所以升級版本。\n")
    check("overlay commit message", not strict_lint_file(
        commit, "commit-message", "gentoo-overlay", None, 280))
    long_subject = root / "long.txt"
    long_subject.write_text("app-misc/foo: " + "x" * 70 + "\n")
    check("commit subject length", any("exceeds" in item[1]
                                       for item in strict_lint_file(
                                           long_subject, "commit-message", "general",
                                           None, 280)))
    punctuated = root / "punctuated.txt"
    punctuated.write_text("app-misc/foo: update?\n")
    check("commit subject punctuation", any("trailing punctuation" in item[1]
                                              for item in strict_lint_file(
                                                  punctuated, "commit-message",
                                                  "general", None, 280)))
    no_blank = root / "no-blank.txt"
    no_blank.write_text("app-misc/foo: add 1.2.3\n因為缺少相依套件，所以增補。\n")
    check("commit blank line", any("line 2 blank" in item[1]
                                   for item in strict_lint_file(
                                       no_blank, "commit-message", "general", None, 280)))
    attributed = root / "attributed.txt"
    attributed.write_text("app-misc/foo: add 1.2.3\n\n"
                          "因為上游改版，所以更新。\n\n"
                          "Co-authored-by: Claude <noreply@anthropic.com>\n")
    check("AI attribution", any("attribution" in item[1]
                                 for item in strict_lint_file(
                                     attributed, "commit-message", "gentoo-overlay",
                                     None, 280)))
    human_attributed = root / "human-attributed.txt"
    human_attributed.write_text("app-misc/foo: update\n\n"
                                "Co-authored-by: Alice <alice@example.org>\n")
    check("human co-author trailer is allowed", not any(
        "attribution" in item[1] for item in strict_lint_file(
            human_attributed, "commit-message", "gentoo-overlay", None, 280)))
    signed = root / "signed.txt"
    signed.write_text("app-misc/foo: update\n\n"
                      "Signed-off-by: Claude Shannon <claude@example.org>\n")
    check("human signoff", not any("attribution" in item[1]
                                    for item in strict_lint_file(
                                        signed, "commit-message", "gentoo-overlay",
                                        None, 280)))
    noreply = root / "noreply.txt"
    noreply.write_text("app-misc/foo: update\n\n"
                       "Signed-off-by: Alice <1+alice@users.noreply.github.com>\n")
    check("GitHub noreply signoff", any("real email" in item[1]
                                         for item in strict_lint_file(
                                             noreply, "commit-message",
                                             "gentoo-overlay", None, 280)))
    generated = root / "generated.txt"
    generated.write_text("app-misc/foo: update\n\nGenerated with OpenAI Codex\n")
    check("OpenAI attribution", any("attribution" in item[1]
                                     for item in strict_lint_file(
                                         generated, "commit-message", "gentoo-overlay",
                                         None, 280)))
    emoji = root / "emoji.txt"
    emoji.write_text(FIXTURES["emoji"] + "\n")
    check("Emoji is rejected", any("remove Emoji" in item[1]
                                     for item in strict_lint_file(
                                         emoji, "pr-body", "gentoo-overlay",
                                         "docs: explain robot icon", 280)))
    data = root / "terms.json"
    data.write_text('{"note": "' + "字" * 400 + '"}\n')
    check("data file Chinese length", any(
        "paragraph" in item[1] for item in strict_lint_file(data, "prose", "general",
                                                          None, 280)))
    long_list = root / "long-list.md"
    long_list.write_text("- " + "字" * 400 + "\n")
    check("long list item", any("paragraph" in item[1]
                                 for item in strict_lint_file(
                                     long_list, "prose", "general", None, 280)))
    expanded_mixed = root / "expanded-mixed.txt"
    expanded_mixed.write_text(FIXTURES["expanded_mixed"] + "\n")
    check("expanded mixed locale", any("mix Traditional" in item[1]
                                        for item in strict_lint_file(
                                            expanded_mixed, "prose", "general",
                                            None, 280)))
    several_wrong = root / "several-wrong.txt"
    several_wrong.write_text(FIXTURES["several_wrong"] + "\n")
    wrong_findings = [item for item in strict_lint_file(
        several_wrong, "prose", "general", None, 280, "zh-TW")
                      if "requested locale" in item[1]]
    check("all wrong-locale lines", len(wrong_findings) == 2)
    check("ordinary core wording", not LINT.terminology_findings(
        FIXTURES["ordinary_core"], "zh-CN"))
    unrelated_rules = root / "wording.json"
    unrelated_rules.write_text('{"notice": "服務運行正常"}\n')
    check("unrelated rule basename", unrelated_rules in list(
        LINT.files_from([root], [])))
    failed_tests = root / "failed-tests.txt"
    failed_tests.write_text("## 測試\n\n目前仍有 2 項失敗。\n")
    check("failed test report", not any("routine passing" in item[1]
                                         for item in strict_lint_file(
                                             failed_tests, "pr-body",
                                             "gentoo-overlay",
                                             "docs: record test failure", 280)))
    passed_tests = root / "passed-tests.txt"
    passed_tests.write_text("All tests passed.\n")
    check("English passing report", any("routine passing" in item[1]
                                          for item in strict_lint_file(
                                              passed_tests, "pr-body",
                                              "gentoo-overlay",
                                              "docs: update text", 280)))
    check("general passing report", any("routine passing" in item[1]
                                         for item in strict_lint_file(
                                             passed_tests, "pr-body", "general",
                                             "docs: update text", 280)))
    terse_pass = root / "terse-pass.txt"
    terse_pass.write_text("pytest: passed\n")
    check("terse passing report", any("routine passing" in item[1]
                                       for item in strict_lint_file(
                                           terse_pass, "pr-body", "general",
                                           "tests: adjust fixture", 280)))
    pr_inventory = root / "pr-inventory.txt"
    pr_inventory.write_text(
        "本次 PR 主要包含以下修改：\n\n"
        "## 修改內容\n\n"
        "- 新增同步功能。\n"
        "- 更新安裝腳本。\n"
        "- 補充測試案例。\n\n"
        "目前所有功能均已完成。\n")
    inventory_findings = strict_lint_file(
        pr_inventory, "pr-body", "general", "scripts: update tooling", 280)
    check("PR change inventory", any("change inventory" in item[1]
                                      for item in inventory_findings))
    check("PR heading", any("omit headings" in item[1]
                             for item in inventory_findings))
    check("PR completion claim", any("completion claim" in item[1]
                                      for item in inventory_findings))
    assurance = root / "assurance.txt"
    assurance.write_text("全面支援所有環境。\n確保全部功能正常。\n")
    check("unsupported PR assurance", len([
        item for item in strict_lint_file(
            assurance, "pr-body", "general", "build: update support", 280)
        if "completion claim" in item[1]]) >= 2)
    long_pr = root / "long-pr.txt"
    long_pr.write_text("字" * 601 + "\n")
    check("general PR character budget", any("600 non-space" in item[1]
                                              for item in strict_lint_file(
                                                  long_pr, "pr-body", "general",
                                                  "docs: explain constraint", 1000)))
    many_blocks = root / "many-blocks.txt"
    many_blocks.write_text("原因一。\n\n原因二。\n\n原因三。\n\n原因四。\n\n原因五。\n")
    check("general PR block budget", any("4 semantic blocks" in item[1]
                                          for item in strict_lint_file(
                                              many_blocks, "pr-body", "general",
                                              "docs: explain constraints", 280)))
    repeated_title = root / "repeated-title.txt"
    repeated_title.write_text("app-misc/foo: update\n\n因為上游介面改變，所以更新呼叫。\n")
    check("repeated PR title", any("repeat the PR title" in item[1]
                                    for item in strict_lint_file(
                                        repeated_title, "pr-body", "general",
                                        "app-misc/foo: update", 280)))
    author_story = root / "author-story.txt"
    author_story.write_text("我們已修改安裝流程。\n")
    check("author work narration", any("author's work narration" in item[1]
                                        for item in strict_lint_file(
                                            author_story, "pr-body", "general",
                                            "install: preserve files", 280)))
    template_body = root / "template-body.txt"
    template_body.write_text(
        "因為上游改變 ABI，所以增加 `dev-libs/libfoo`。\n\n"
        "<!-- Please put the pull request description above -->\n\n"
        "---\n\n"
        "Please check all the boxes that apply:\n\n"
        "- [x] All tests passed.\n"
        "- [x] I used AI and checked its output.\n")
    check("required PR template excluded", not strict_lint_file(
        template_body, "pr-body", "gentoo-overlay",
        "app-misc/foo: add dependency", 280))
    machine_translation = root / "machine-translation.txt"
    machine_translation.write_text(FIXTURES["machine_translation"] + "\n")
    mt_findings = strict_lint_file(machine_translation, "prose", "general", None, 280)
    check("translated construction", any("direct action instead" in item[1]
                                         for item in mt_findings))
    check("redundant passive", any("passive marker" in item[1] for item in mt_findings))
    artifact_cases = {
        "zh-CN": "artifact_location_simplified",
        "zh-TW": "artifact_location_traditional",
    }
    for locale, fixture in artifact_cases.items():
        artifact_location = root / f"artifact-location-{locale}.txt"
        artifact_location.write_text(FIXTURES[fixture] + "\n")
        check(f"{locale} translated artifact-location order", any(
            item.code == "wording.artifact-location-order"
            for item in strict_lint_file(
                artifact_location, "prose", "general", None, 280, locale)))
    artifact_location_code = root / "artifact-location-code-zh-CN.md"
    artifact_location_code.write_text(
        FIXTURES["artifact_location_code_simplified"] + "\n")
    check("translated artifact location before inline code", any(
        item.code == "wording.artifact-location-order"
        for item in strict_lint_file(
            artifact_location_code, "prose", "general", None, 280, "zh-CN")))
    for locale, fixture in {
            "zh-CN": "artifact_location_clean_simplified",
            "zh-TW": "artifact_location_clean_traditional",
    }.items():
        artifact_location = root / f"artifact-location-clean-{locale}.txt"
        artifact_location.write_text(FIXTURES[fixture] + "\n")
        check(f"{locale} direct artifact location", not any(
            item.code == "wording.artifact-location-order"
            for item in strict_lint_file(
                artifact_location, "prose", "general", None, 280, locale)))
    artifact_ellipsis = root / "artifact-location-ellipsis.txt"
    artifact_ellipsis.write_text(FIXTURES["artifact_location_ellipsis"] + "\n")
    check("ordinary location ellipsis", not any(
        item.code == "wording.artifact-location-order"
        for item in strict_lint_file(
            artifact_ellipsis, "prose", "general", None, 280)))
    artifact_parallel = root / "artifact-location-parallel.txt"
    artifact_parallel.write_text(FIXTURES["artifact_location_parallel"] + "\n")
    check("parallel artifact locations", not any(
        item.code == "wording.artifact-location-order"
        for item in strict_lint_file(
            artifact_parallel, "prose", "general", None, 280, "zh-TW")))
    aspect = root / "aspect.txt"
    aspect.write_text(FIXTURES["redundant_aspect"] + "\n")
    check("redundant aspect marker", any("aspect marker" in item[1]
                                          for item in strict_lint_file(
                                              aspect, "prose", "general", None, 280)))
    vague = root / "vague.txt"
    vague.write_text(FIXTURES["vague_improvement"] + "\n")
    check("vague improvement claim", any("measured change" in item[1]
                                          for item in strict_lint_file(
                                              vague, "prose", "general", None, 280)))
    brackets = root / "brackets.txt"
    brackets.write_text(FIXTURES["full_width_brackets"] + "\n")
    check("full-width brackets", any("full-width brackets" in item[1]
                                      for item in strict_lint_file(
                                          brackets, "prose", "general", None, 280)))
    ascii_punctuation = root / "punctuation.txt"
    ascii_punctuation.write_text(FIXTURES["ascii_punctuation"] + "\n")
    check("ASCII punctuation", any("Chinese punctuation" in item[1]
                                    for item in strict_lint_file(
                                        ascii_punctuation, "prose", "general", None, 280)))
    clean = root / "clean.txt"
    clean.write_text(FIXTURES["clean_prose"] + "\n")
    check("clean technical prose", not strict_lint_file(
        clean, "prose", "general", None, 280, "zh-TW"))
    terminology = root / "terminology.txt"
    terminology.write_text(FIXTURES["expanded_terminology"] + "\n")
    terminology_findings = strict_lint_file(terminology, "prose", "general", None,
                                          280, "zh-TW")
    check("expanded terminology", len([item for item in terminology_findings
                                       if "in zh-TW" in item[1]]) == 3)

    combined = root / "combined.md"
    combined.write_text("說明。\n\n```{.sh}\n# " + FIXTURES["bad_comment"] + "\n```\n")
    check("all mode checks Pandoc fenced comments", any(
        "comments" in item[1]
        for item in strict_lint_file(combined, "all", "general", None, 280)))
    table = root / "table.md"
    table.write_text("| 欄位 | 說明 |\n|---|---|\n| value | " + "字" * 400 + " |\n")
    check("Markdown table cell length", any(
        "paragraph" in item[1]
        for item in strict_lint_file(table, "all", "general", None, 280)))
    shell_data = root / "shell-data.sh"
    shell_data.write_text(
        "value=${name#中文前綴}\n"
        "cat <<'EOF'\n"
        "# 中文正文\n"
        "EOF\n")
    check("shell data is not a comment", not any(
        "comments" in item[1]
        for item in strict_lint_file(shell_data, "source", "general", None, 280)))
    here_string = root / "here-string.sh"
    here_string.write_text("cat <<<'# 中文資料'\n# " + FIXTURES["bad_comment"] + "\n")
    check("shell here-string does not start a heredoc", any(
        "comments" in item[1]
        for item in strict_lint_file(here_string, "source", "general", None, 280)))
    shell_separator = root / "shell-separator.sh"
    shell_separator.write_text("true;# " + FIXTURES["bad_comment"] + "\n")
    check("shell comment after a command separator", any(
        item.code == "comments.language" for item in strict_lint_file(
            shell_separator, "source", "general", None, 280)))
    escaped_heredoc = root / "escaped-heredoc.sh"
    escaped_heredoc.write_text(
        "cat <<\\EOF\n# 中文正文\nEOF\n# " + FIXTURES["bad_comment"] + "\n")
    check("escaped shell heredoc delimiter", len([
        item for item in strict_lint_file(
            escaped_heredoc, "source", "general", None, 280)
        if item.code == "comments.language"]) == 1)
    yaml_data = root / "data.yaml"
    yaml_data.write_text("message: |\n  # 中文正文\n")
    check("YAML block scalar is not a comment", not any(
        "comments" in item[1]
        for item in strict_lint_file(yaml_data, "source", "general", None, 280)))
    yaml_indent_indicator = root / "indent-indicator.yaml"
    yaml_indent_indicator.write_text("message: |2-\n  # 中文正文\n")
    check("YAML indentation indicator is data", not any(
        item.code == "comments.language" for item in strict_lint_file(
            yaml_indent_indicator, "source", "general", None, 280)))
    markdown_extension = root / "comments.markdown"
    markdown_extension.write_text(
        "```sh\n# " + FIXTURES["bad_comment"] + "\n```\n")
    check("Markdown extension fenced comment", any(
        item.code == "comments.language" for item in strict_lint_file(
            markdown_extension, "source", "general", None, 280)))
    mdx_comment = root / "comments.mdx"
    mdx_comment.write_text("{/* " + FIXTURES["bad_comment"] + " */}\n")
    check("MDX source comment", any(
        item.code == "comments.language" for item in strict_lint_file(
            mdx_comment, "source", "general", None, 280)))
    context = root / "context.txt"
    context.write_text("遠程醫療需要畢業證書。這份資料被所有節點使用。\n")
    context_findings = strict_lint_file(context, "prose", "general", None, 280,
                                      "zh-TW")
    check("ordinary domain wording", not any(
        "remote repository" in item[1] or "certificate" in item[1]
        or "passive marker" in item[1] for item in context_findings))
    measured = root / "measured.txt"
    measured.write_text("處理量顯著提升 35%。\n")
    check("measured improvement", not any(
        "measured change" in item[1]
        for item in strict_lint_file(measured, "prose", "general", None, 280)))
    punctuation = root / "more-punctuation.txt"
    punctuation.write_text(FIXTURES["adjacent_ascii_punctuation"] + "\n")
    check("adjacent ASCII punctuation", len([
        item for item in strict_lint_file(punctuation, "prose", "general", None, 280)
        if "Chinese punctuation" in item[1]]) == 2)
    internal = TARGET.parent.parent / "references" / "technical-terms.json"
    check("explicit internal rule file", internal in list(LINT.files_from([internal], [])))
    regional = root / "regional.txt"
    regional.write_text(FIXTURES["regional_vocabulary"] + "\n")
    regional_findings = strict_lint_file(regional, "prose", "general", None, 280,
                                       "zh-TW", True)
    check("regional vocabulary", any("regional vocabulary" in item[1]
                                     for item in regional_findings))
    check("maintained term wins", any("for server in zh-TW" in item[1]
                                      for item in regional_findings)
          and not any("regional vocabulary" in item[1]
                      and item[2] == FIXTURES["regional_server"]
                      for item in regional_findings))
    check("regional check is opt-in", not any(
        "regional vocabulary" in item[1] for item in strict_lint_file(
            regional, "prose", "general", None, 280, "zh-TW")))
    contained = root / "contained.txt"
    contained.write_text(FIXTURES["contained_word"] + "\n")
    check("longer word suppresses a match", not any(
        "colloquial" in item[1] for item in strict_lint_file(
            contained, "prose", "general", None, 280, "zh-TW", True)))
    general_attribution = root / "general-attribution.txt"
    general_attribution.write_text("fix: update parser\n\n"
                                   "因為輸入含 BOM，所以先剝除。\n\n"
                                   "Co-authored-by: Claude <noreply@anthropic.com>\n")
    check("AI attribution in any profile", any(
        "AI signatures are not allowed" in item[1] for item in strict_lint_file(
            general_attribution, "commit-message", "general", None, 280)))
    source_attribution = root / "attributed.py"
    source_attribution.write_text("# Generated with Claude Code\nvalue = 1\n")
    check("AI attribution in source", any(
        "AI signatures are not allowed" in item[1] for item in strict_lint_file(
            source_attribution, "all", "general", None, 280)))
    human_trailer = root / "human-trailer.txt"
    human_trailer.write_text("fix: update parser\n\n"
                             "Co-authored-by: Alice <alice@example.org>\n")
    check("human trailer stays outside overlay", not strict_lint_file(
        human_trailer, "commit-message", "general", None, 280))
    check("human trailer stays inside overlay", not strict_lint_file(
        human_trailer, "commit-message", "gentoo-overlay", None, 280))
    human_signoff = root / "human-signoff.txt"
    human_signoff.write_text("app-misc/foo: add 1.4.2\n\n"
                             "Signed-off-by: Zakk <zakk@example.org>\n")
    check("human sign-off is allowed", not strict_lint_file(
        human_signoff, "commit-message", "gentoo-overlay", None, 280))

    ai_article = root / "ai-article.txt"
    ai_article.write_text(FIXTURES["ai_article"] + "\n")
    article_findings = strict_lint_file(
        ai_article, "prose", "general", None, 280, "zh-TW")
    check("generic AI introduction", any(
        "era-setting" in item[1] for item in article_findings))
    check("article narration", any(
        "narrating the article" in item[1] for item in article_findings))
    check("promotional adjective", any(
        "promotional adjectives" in item[1] for item in article_findings))

    complex_sentence = root / "complex-sentence.txt"
    complex_sentence.write_text(FIXTURES["complex_sentence"] + "\n")
    check("complex sentence", any(
        "split the sentence" in item[1] for item in strict_lint_file(
            complex_sentence, "prose", "general", None, 280, "zh-TW")))
    check("standard style has no fixed sentence limit", not any(
        "split the sentence" in item[1] for item in strict_lint_file(
            complex_sentence, "prose", "general", None, None, "zh-TW",
            style="standard")))

    repeated = root / "repeated.txt"
    repeated.write_text(FIXTURES["repeated_sentence"] + "\n")
    check("repeated sentence", any(
        "repeated sentence" in item[1] for item in strict_lint_file(
            repeated, "prose", "general", None, 280, "zh-TW")))

    regional_slang = root / "regional-slang.txt"
    regional_slang.write_text(FIXTURES["regional_slang"] + "\n")
    check("region-bound slang", len([
        item for item in strict_lint_file(
            regional_slang, "prose", "general", None, 280, "zh-TW")
        if "region-bound slang" in item[1]]) == 2)

    shared_traditional = root / "shared-traditional.txt"
    shared_traditional.write_text(FIXTURES["shared_traditional"] + "\n")
    check("Traditional technical term remains valid", not strict_lint_file(
        shared_traditional, "prose", "general", None, 280, "zh-TW"))

    stdin_result = run(
        [sys.executable, str(TARGET), "--kind", "prose", "--style", "strict", "-"],
        input=FIXTURES["stdin_article"] + "\n", text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    check("standard input", stdin_result.returncode == 1
          and "narrating the article" in stdin_result.stdout)
    ui_stdin_text = (
        'download_error: "無法下載檔案。請重試。"\n'
        'loading: "正在載入…"\n'
        'empty_results: "沒有符合篩選條件的結果"\n'
        'delete_confirm: "要刪除映像檔嗎？刪除後無法復原。"\n')
    ui_stdin = run(
        [sys.executable, str(TARGET), "--kind", "prose", "--style", "ui",
         "--locale", "zh-TW", "--stdin-filename", "catalog.yaml", "-"],
        input=ui_stdin_text, text=True, capture_output=True)
    check("standard input keeps data-file context", ui_stdin.returncode == 0)

    inline_code = root / "inline-code.md"
    inline_code.write_text("Pattern: `" + FIXTURES["stdin_article"] + "`\n")
    check("inline code is excluded from prose rules", not strict_lint_file(
        inline_code, "prose", "general", None, 280))
    multi_tick_code = root / "multi-tick-code.md"
    multi_tick_code.write_text("``代碼`Ａ...``\n")
    check("multi-backtick code span is excluded", not strict_lint_file(
        multi_tick_code, "prose", "general", None, 280))
    long_fence = root / "long-fence.md"
    long_fence.write_text(
        "````text\n代碼Ａ...\n```\n仍是代碼Ｂ...\n````\n")
    check("long Markdown fence ignores a shorter marker", not strict_lint_file(
        long_fence, "prose", "general", None, 280))
    unclosed_fence = root / "unclosed-fence.md"
    unclosed_fence.write_text("````text\n代碼Ａ...\n")
    check("unclosed Markdown fence is excluded", not strict_lint_file(
        unclosed_fence, "prose", "general", None, 280))
    indented_code = root / "indented-code.md"
    indented_code.write_text("說明。\n\n    代碼Ａ...\n")
    check("Markdown indented code is excluded", not strict_lint_file(
        indented_code, "prose", "general", None, 280))
    indented_prose = root / "indented-prose.txt"
    indented_prose.write_text("    " + FIXTURES["masked_colloquial"] + "\n")
    check("indented plain text remains prose", any(
        item.code == "wording.discourse-filler" for item in strict_lint_file(
            indented_prose, "prose", "general", None, 280)))
    list_continuation = root / "list-continuation.md"
    list_continuation.write_text(
        "- 項目\n    " + FIXTURES["filler_continuation"] + "\n")
    check("Markdown list continuation remains prose", any(
        item.code == "wording.discourse-filler" for item in strict_lint_file(
            list_continuation, "prose", "general", None, 280)))
    vague = root / "vague-attribution.md"
    vague.write_text(FIXTURES["vague_attribution"] + "\n")
    check("vague attribution is reported", any(
        item.code == "wording.vague-attribution" for item in strict_lint_file(
            vague, "prose", "general", None, 280)))
    pretty_json = root / "pretty.json"
    pretty_json.write_text(
        '{\n    "message": "' + FIXTURES["masked_colloquial"] + '"\n}\n')
    check("indented JSON values remain prose", any(
        item.code == "wording.discourse-filler" for item in strict_lint_file(
            pretty_json, "prose", "general", None, 280)))

    standard_comment = root / "standard-comment.py"
    standard_comment.write_text("# " + FIXTURES["bad_comment"] + "\nvalue = 1\n")
    check("standard style follows repository comment language", not strict_lint_file(
        standard_comment, "source", "general", None, None,
        style="standard"))
    check("strict style requires English comments", any(
        "comments must be concise English" in item[1]
        for item in strict_lint_file(
            standard_comment, "source", "general", None, None,
            style="strict")))

    standard_symbol = root / "standard-symbol.txt"
    standard_symbol.write_text(FIXTURES["technical_symbol"] + "\n")
    check("standard style allows technical symbols", not strict_lint_file(
        standard_symbol, "prose", "general", None, None, "zh-TW",
        style="standard"))
    check("strict style rejects technical symbols", any(
        "remove Emoji" in item[1] for item in strict_lint_file(
            standard_symbol, "prose", "general", None, None, "zh-TW",
            style="strict")))

    academic_article = root / "academic-article.txt"
    academic_article.write_text(FIXTURES["academic_article"] + "\n")
    check("academic style allows article narration", not strict_lint_file(
        academic_article, "prose", "general", None, None, "zh-TW",
        style="academic"))
    readme_article = root / "readme-article.txt"
    readme_article.write_text(FIXTURES["academic_article"] + "\n")
    check("README starts with the subject", any(
        "narrating the article" in item[1] for item in strict_lint_file(
            readme_article, "prose", "general", None, None, "zh-TW",
            style="readme")))
    check("README style rejects decorative symbols", any(
        "remove Emoji" in item[1] for item in strict_lint_file(
            standard_symbol, "prose", "general", None, None, "zh-TW",
            style="readme")))
    ui_cases = {
        "casual error": ("ui_casual_error", "apologetic or casual"),
        "positional action": ("ui_positional_action", "action or destination"),
        "redundant progress": ("ui_redundant_progress", "ongoing-state marker"),
        "generic error": ("ui_generic_error", "operation that failed"),
        "generic confirmation": ("ui_generic_confirmation", "confirmed action"),
    }
    for label, (fixture, message) in ui_cases.items():
        ui_text = root / f"ui-{label.replace(' ', '-')}.txt"
        ui_text.write_text(FIXTURES[fixture] + "\n")
        check(f"UI {label}", any(
            message in item[1] for item in strict_lint_file(
                ui_text, "prose", "general", None, None, "zh-TW",
                style="ui")))
    ui_clean = root / "ui-clean.txt"
    ui_clean.write_text(FIXTURES["ui_clean_error"] + "\n")
    check("clean UI error", not strict_lint_file(
        ui_clean, "prose", "general", None, None, "zh-TW", style="ui"))
    check("UI permits a semantic check mark", not strict_lint_file(
        standard_symbol, "prose", "general", None, None, "zh-TW",
        style="ui"))
    check("UI rejects Emoji", any(
        "remove Emoji" in item[1] for item in strict_lint_file(
            emoji, "prose", "general", None, None, "zh-TW", style="ui")))
    quoted_term = root / "quoted-term.txt"
    quoted_term.write_text(FIXTURES["quoted_term"] + "\n")
    check("standard style allows Chinese quotation marks", not strict_lint_file(
        quoted_term, "prose", "general", None, None, "zh-TW",
        style="standard"))

    general_pr = root / "general-pr.txt"
    general_pr.write_text("## Summary\n\n" + FIXTURES["clean_prose"] + "\n")
    check("standard PR follows repository headings", not strict_lint_file(
        general_pr, "pr-body", "general", "docs: explain behavior", None,
        "zh-TW", style="standard"))
    check("strict PR rejects optional headings", any(
        "omit headings" in item[1] for item in strict_lint_file(
            general_pr, "pr-body", "general", "docs: explain behavior", None,
            "zh-TW", style="strict")))

    shared_simplified = root / "shared-simplified.txt"
    shared_simplified.write_text(FIXTURES["shared_simplified"] + "\n")
    check("Singapore locale uses Simplified Chinese", not strict_lint_file(
        shared_simplified, "prose", "general", None, None, "zh-SG",
        style="standard"))
    check("Malaysia locale uses Simplified Chinese", not strict_lint_file(
        shared_simplified, "prose", "general", None, None, "zh-MY",
        style="standard"))
    check("Hong Kong locale uses Traditional Chinese", not strict_lint_file(
        shared_traditional, "prose", "general", None, None, "zh-HK",
        style="standard"))
    fenced_prompt = root / "fenced-prompt.md"
    fenced_prompt.write_text(FIXTURES["fenced_prompt"])
    check("code fence exempt from Emoji rule", not any(
        "Emoji" in item[1] for item in strict_lint_file(
            fenced_prompt, "prose", "general", None, 280)))
    locale_name = root / "locale-name.md"
    locale_name.write_text(FIXTURES["locale_name"] + "\n")
    check("naming another locale is allowed", not any(
        "locale" in item[1] for item in strict_lint_file(
            locale_name, "prose", "general", None, 280, "zh-CN")))
    brand_locale = root / "brand-locale.md"
    brand_locale.write_text(FIXTURES["brand_locale"] + "\n")
    check("brand and shared words keep the locale", not any(
        "locale" in item[1] for item in strict_lint_file(
            brand_locale, "prose", "general", None, 280, "zh-TW")))

    typography = root / "typography.md"
    typography.write_text(FIXTURES["typography_defects"] + "\n")
    typography_findings = LINT.lint_file(
        typography, "prose", "general", None, None, "zh-TW", style="readme")
    typography_codes = {item.code for item in typography_findings}
    check("deterministic Chinese typography", {
        "typography.fullwidth-alphanumeric",
        "typography.fullwidth-decimal",
        "typography.repeated-punctuation",
        "typography.ascii-ellipsis",
        "typography.ascii-dash",
        "typography.cjk-latin-spacing",
    } <= typography_codes)
    protected_typography = root / "protected-typography.md"
    protected_typography.write_text(FIXTURES["typography_protected"] + "\n")
    check("code and URLs are excluded from typography", not any(
        item.code.startswith("typography.") for item in LINT.lint_file(
            protected_typography, "prose", "general", None, None,
            "zh-TW", style="readme")))

    markdown_bad = root / "markdown-bad.md"
    markdown_bad.write_text(FIXTURES["markdown_structure_bad"])
    markdown_codes = {item.code for item in LINT.lint_file(
        markdown_bad, "prose", "general", None, None, "zh-TW",
        style="readme")}
    check("Markdown structure", {
        "markdown.heading-level",
        "markdown.heading-punctuation",
        "markdown.generic-link",
        "markdown.list-punctuation",
    } <= markdown_codes)
    markdown_clean = root / "markdown-clean.md"
    markdown_clean.write_text(FIXTURES["markdown_structure_clean"])
    check("clean Markdown structure", not LINT.lint_file(
        markdown_clean, "prose", "general", None, None, "zh-TW",
        style="readme"))

    quoted_sentence = root / "quoted-sentence.md"
    quoted_sentence.write_text(FIXTURES["quoted_sentence"] + "\n")
    check("ordinary quotation is not a quoted-term finding", not any(
        item.code == "wording.quoted-term" for item in LINT.lint_file(
            quoted_sentence, "prose", "general", None, None, "zh-TW",
            style="strict")))
    check("explicit quoted identifier remains detectable", any(
        item.code == "wording.quoted-term" for item in strict_lint_file(
            brackets, "prose", "general", None, 280)))

    ui_json = root / "ui.json"
    ui_json.write_text(FIXTURES["ui_json_bad"] + "\n")
    ui_json_findings = LINT.lint_file(
        ui_json, "prose", "general", None, None, "zh-TW", style="ui")
    check("UI JSON control punctuation", len([
        item for item in ui_json_findings
        if item.code == "ui.control-punctuation"]) == 1)
    ui_html = root / "ui.html"
    ui_html.write_text(FIXTURES["ui_html_bad"] + "\n")
    check("UI HTML surface punctuation", len([
        item for item in LINT.lint_file(
            ui_html, "prose", "general", None, None, "zh-TW", style="ui")
        if item.code == "ui.control-punctuation"]) == 3)
    ui_surface_clean = root / "ui-clean.json"
    ui_surface_clean.write_text(FIXTURES["ui_surface_clean"] + "\n")
    check("UI explanation punctuation remains valid", not any(
        item.code == "ui.control-punctuation" for item in LINT.lint_file(
            ui_surface_clean, "prose", "general", None, None,
            "zh-TW", style="ui")))
    ui_exclamation = root / "ui-exclamation.txt"
    ui_exclamation.write_text(FIXTURES["ui_exclamation"] + "\n")
    check("UI exclamation mark", any(
        item.code == "ui.exclamation" for item in LINT.lint_file(
            ui_exclamation, "prose", "general", None, None,
            "zh-TW", style="ui")))

    grammar_bad = root / "grammar-bad.md"
    grammar_bad.write_text(FIXTURES["grammar_defects"] + "\n")
    grammar_findings = LINT.lint_file(
        grammar_bad, "prose", "general", None, None, style="technical")
    check("conservative 的得地 rules", {
        "grammar.verb-degree-de",
        "grammar.adverbial-de",
        "grammar.attributive-di",
    } <= {item.code for item in grammar_findings})
    check("grammar findings are advisory", all(
        item.severity == "warning" for item in grammar_findings
        if item.code.startswith("grammar.")))
    grammar_clean = root / "grammar-clean.md"
    grammar_clean.write_text(FIXTURES["grammar_clean"] + "\n")
    check("clean 的得地 usage", not any(
        item.code.startswith("grammar.") for item in LINT.lint_file(
            grammar_clean, "prose", "general", None, None,
            style="technical")))

    mixed_terms = root / "mixed-terms.md"
    mixed_terms.write_text(FIXTURES["mixed_terms"] + "\n")
    consistency_codes = {item.code for item in LINT.lint_file(
        mixed_terms, "prose", "general", None, None,
        style="technical")}
    check("within-document terminology consistency", {
        "consistency.program-code", "consistency.inside",
    } <= consistency_codes)
    locale_comparison = root / "locale-comparison.md"
    locale_comparison.write_text(FIXTURES["locale_comparison"] + "\n")
    check("explicit locale comparisons are excluded", not any(
        item.code.startswith("consistency.") for item in LINT.lint_file(
            locale_comparison, "prose", "general", None, None,
            style="technical")))
    selected_consistency = {item.code for item in LINT.lint_file(
        mixed_terms, "prose", "general", None, None,
        "zh-TW", style="technical")}
    check("selected locale keeps explicit consistency rules", {
        "consistency.program-code", "consistency.inside",
    } <= selected_consistency)

    json_result = run(
        [sys.executable, str(TARGET), "--kind", "prose", "--style", "readme",
         "--locale", "zh-TW", "--format", "json", str(typography)],
        check=False, capture_output=True, text=True)
    json_payload = json.loads(json_result.stdout)
    check("JSON diagnostic output", (
        json_result.returncode == 1
        and not json_result.stderr
        and json_payload["version"] == 1
        and json_payload["count"] == len(json_payload["findings"])
        and all(set(item) == {"path", "line", "code", "severity", "message", "sample"}
                for item in json_payload["findings"])))
    clean_json_result = run(
        [sys.executable, str(TARGET), "--kind", "prose", "--style", "readme",
         "--locale", "zh-TW", "--format", "json", str(markdown_clean)],
        check=False, capture_output=True, text=True)
    clean_json_payload = json.loads(clean_json_result.stdout)
    check("empty JSON diagnostic output", (
        clean_json_result.returncode == 0
        and clean_json_payload == {"version": 1, "count": 0, "findings": []}))

    fix_target = root / "fix-target.md"
    fix_target.write_bytes((
        "# 設定Redis。\r\n\r\n"
        + FIXTURES["typography_defects"]
        + " 中A文 `tool --flag` https://example.com/a...。\r\n").encode())
    fix_command = [
        sys.executable, str(TARGET), "--kind", "prose", "--style", "readme",
        "--fix", str(fix_target),
    ]
    fix_result = run(
        fix_command, check=False, capture_output=True, text=True)
    fixed_bytes = fix_target.read_bytes()
    check("safe typography fix", (
        fix_result.returncode == 0
        and "fixed " in fix_result.stdout
        and b"\r\n" in fixed_bytes
        and "# 設定 Redis\r\n".encode() in fixed_bytes
        and "12.3 全形英數！ …… —— 用了 Redis。".encode() in fixed_bytes
        and "中 A 文".encode() in fixed_bytes
        and b"`tool --flag`" in fixed_bytes
        and b"https://example.com/a..." in fixed_bytes))
    second_fix = run(
        fix_command, check=False, capture_output=True, text=True)
    check("safe fix is idempotent", (
        second_fix.returncode == 0
        and "fixed " not in second_fix.stdout
        and fix_target.read_bytes() == fixed_bytes))
    grammar_fix = root / "grammar-fix.md"
    grammar_fix.write_text(FIXTURES["grammar_defects"] + "\n")
    before_grammar_fix = grammar_fix.read_text()
    run(
        [sys.executable, str(TARGET), "--kind", "prose", "--style",
         "technical", "--fix", str(grammar_fix)],
        check=False, capture_output=True, text=True)
    check("safe fix does not rewrite grammar", (
        grammar_fix.read_text() == before_grammar_fix))
    structured_fix = root / "structured-fix.json"
    structured_fix.write_text('{"版本2": "值Ａ"}\n')
    before_structured_fix = structured_fix.read_bytes()
    run(
        [sys.executable, str(TARGET), "--kind", "prose", "--style", "ui",
         "--fix", str(structured_fix)],
        check=False, capture_output=True, text=True)
    check("safe fix leaves structured data unchanged", (
        structured_fix.read_bytes() == before_structured_fix))
    toml_frontmatter = root / "toml-frontmatter.md"
    toml_frontmatter.write_text('+++\nslug = "版本2"\n+++\n正文。\n')
    run(
        [sys.executable, str(TARGET), "--kind", "prose", "--style", "readme",
         "--fix", str(toml_frontmatter)],
        check=False, capture_output=True, text=True)
    check("safe fix preserves TOML front matter", (
        'slug = "版本2"' in toml_frontmatter.read_text()))
    stdin_fix = run(
        [sys.executable, str(TARGET), "--kind", "prose", "--fix", "-"],
        input="測試。\n", check=False, capture_output=True, text=True)
    check("safe fix rejects standard input", (
        stdin_fix.returncode == 2
        and "does not accept standard input" in stdin_fix.stderr))
    missing_result = run(
        [sys.executable, str(TARGET), "--format", "json",
         str(root / "missing.md")],
        check=False, capture_output=True, text=True)
    missing_payload = json.loads(missing_result.stdout)
    check("missing input path fails", (
        missing_result.returncode == 1
        and missing_payload["count"] == 1
        and missing_payload["findings"][0]["code"] == "input.missing"))

    thematic_break = root / "thematic-break.md"
    thematic_break.write_text("---\n" + FIXTURES["masked_colloquial"] + "\n")
    check("unclosed front matter marker remains prose", any(
        item.code == "wording.discourse-filler" for item in strict_lint_file(
            thematic_break, "prose", "general", None, None)))
    frontmatter = root / "frontmatter.md"
    frontmatter.write_text(
        "---\nslug: " + FIXTURES["masked_colloquial"] + "\n---\n內容已更新。\n")
    check("closed front matter is excluded", not any(
        item.code == "wording.discourse-filler" for item in strict_lint_file(
            frontmatter, "prose", "general", None, None)))
    multiline_code = root / "multiline-code.md"
    multiline_code.write_text(
        "說明 ``" + FIXTURES["masked_colloquial"].replace("已經", "\n已經")
        + "`` 完成。\n")
    check("multiline code span is excluded", not any(
        item.code.startswith("wording.") for item in strict_lint_file(
            multiline_code, "prose", "general", None, None)))
    html_code = root / "html-code.md"
    html_code.write_text(
        "<pre>" + FIXTURES["masked_colloquial"] + "</pre>\n<code>"
        + FIXTURES["colloquial_alert"] + "</code>\n")
    check("HTML code elements are excluded", not any(
        item.code.startswith("wording.") for item in strict_lint_file(
            html_code, "prose", "general", None, None)))
    pandoc_anchor = root / "pandoc-anchor.md"
    pandoc_anchor.write_text("# 標題 {#其實}\n\n內容已更新。\n")
    check("Pandoc attributes are excluded", not any(
        item.code == "wording.discourse-filler" for item in strict_lint_file(
            pandoc_anchor, "prose", "general", None, None)))

    markdown_url = root / "url.md"
    markdown_url.write_text("[文件](https://例子.中国/奔跑)\n")
    check("Markdown link destination is excluded", not strict_lint_file(
        markdown_url, "prose", "general", None, None))
    css_url = root / "url.css"
    css_url.write_text("a { background: url(https://例子.中国/图.png); }\n")
    check("CSS URL is not a comment", not strict_lint_file(
        css_url, "source", "general", None, None))
    uppercase_ts = root / "component.TS"
    uppercase_ts.write_text("// " + FIXTURES["bad_comment"] + "\n")
    check("uppercase source suffix is recognized", any(
        item.code == "comments.language" for item in strict_lint_file(
            uppercase_ts, "source", "general", None, None)))
    tsx_fence = root / "tsx-fence.md"
    tsx_fence.write_text("```tsx\n// " + FIXTURES["bad_comment"] + "\n```\n")
    check("TSX fenced comment is recognized", any(
        item.code == "comments.language" for item in strict_lint_file(
            tsx_fence, "source", "general", None, None)))
    template_comment = root / "template.ts"
    template_comment.write_text(
        "const value = `${foo({a: 1}) /* " + FIXTURES["bad_comment"] + " */}`;\n")
    check("nested template expression comment is recognized", any(
        item.code == "comments.language" for item in strict_lint_file(
            template_comment, "source", "general", None, None)))
    shell_single_quote = root / "single-quote.sh"
    shell_single_quote.write_text("echo 'a\\' # " + FIXTURES["bad_comment"] + "\n")
    check("shell single quote closes after a backslash", any(
        item.code == "comments.language" for item in strict_lint_file(
            shell_single_quote, "source", "general", None, None)))
    toml_string = root / "multiline.toml"
    toml_string.write_text(
        "value = \"\"\"\n# 中文資料\n\"\"\"\n# " + FIXTURES["bad_comment"] + "\n")
    toml_comments = [item for item in strict_lint_file(
        toml_string, "source", "general", None, None)
                     if item.code == "comments.language"]
    check("TOML multiline strings are not comments", (
        len(toml_comments) == 1 and toml_comments[0].line == 4))
    multiline_comment = root / "multiline.c"
    multiline_comment.write_text("/*\n * " + FIXTURES["bad_comment"] + "\n */\n")
    multiline_findings = [item for item in strict_lint_file(
        multiline_comment, "source", "general", None, None)
                          if item.code == "comments.language"]
    check("multiline comment reports the Chinese line", (
        len(multiline_findings) == 1 and multiline_findings[0].line == 2))

    standard_pr = root / "standard-pr.md"
    standard_pr.write_text(
        "本次 PR 主要針對通知調整。測試全部通過。確保所有功能正常。\n")
    standard_pr_codes = {item.code for item in LINT.lint_file(
        standard_pr, "pr-body", "general", None, None)}
    check("standard PR rejects work diary and routine claims", {
        "vcs.routine-tests", "vcs.work-diary",
    } <= standard_pr_codes)
    human_claude = root / "human-claude.txt"
    human_claude.write_text(
        "fix: update parser\n\nCo-authored-by: Claude Dupont <claude.dupont@example.org>\n")
    check("human named Claude is allowed", not any(
        item.code == "vcs.ai-attribution" for item in LINT.lint_file(
            human_claude, "commit-message", "general", None, None)))
    attribution_line = root / "attribution-line.txt"
    attribution_line.write_text(
        "fix: update parser\n\nCo-authored-by: Claude <noreply@anthropic.com>\n")
    ai_lines = [item.line for item in LINT.lint_file(
        attribution_line, "commit-message", "general", None, None)
                if item.code == "attribution.ai"]
    check("AI attribution reports its own line", ai_lines == [3])

    warning_only = root / "warning.md"
    warning_only.write_text("服務執行的很快。\n")
    warning_default = run(
        [sys.executable, str(TARGET), "--kind", "prose", str(warning_only)],
        check=False, capture_output=True, text=True)
    warning_strict = run(
        [sys.executable, str(TARGET), "--kind", "prose", "--fail-level",
         "warning", str(warning_only)],
        check=False, capture_output=True, text=True)
    check("advisory findings do not fail by default", (
        warning_default.returncode == 0 and "advisory" in warning_default.stderr))
    check("warning fail level is available for CI", warning_strict.returncode == 1)

    simplified_sentence = root / "simplified.md"
    simplified_sentence.write_text(FIXTURES["simplified_login"] + "\n")
    check("locale catches common Simplified characters", any(
        item.code == "locale.wrong-script" for item in LINT.lint_file(
            simplified_sentence, "prose", "general", None, None, "zh-TW")))
    queen = root / "queen.md"
    queen.write_text("皇后大道位於香港。\n")
    check("ambiguous queen character is allowed", not any(
        item.code.startswith("locale.") for item in LINT.lint_file(
            queen, "prose", "general", None, None)))
    locale_terms = root / "locale-terms.md"
    locale_terms.write_text("zh-CN 使用“用户”，zh-TW 使用「使用者」。\n")
    check("explicit locale comparison is allowed", not any(
        item.code.startswith("locale.") for item in LINT.lint_file(
            locale_terms, "prose", "general", None, None, "zh-TW")))
    ordinary_run = root / "ordinary-run.md"
    ordinary_run.write_text("運動員在操場奔跑。安裝上游提供的套件。\n")
    check("ordinary run and upstream wording are allowed", not any(
        item.code in {"wording.colloquial-run", "wording.colloquial-install"}
        for item in LINT.lint_file(
            ordinary_run, "prose", "general", None, None, style="strict")))
    colloquial_alert = root / "colloquial-alert.md"
    colloquial_alert.write_text(FIXTURES["colloquial_alert"] + "\n")
    alert_codes = {item.code for item in LINT.lint_file(
        colloquial_alert, "prose", "general", None, None, style="strict")}
    check("colloquial alert wording is rejected", {
        "wording.colloquial", "wording.colloquial-failure",
    } <= alert_codes)

    nested_button = root / "nested-button.html"
    nested_button.write_text("<button><span>儲存變更。</span></button>\n")
    check("nested HTML button is checked in all mode", any(
        item.code == "ui.control-punctuation" for item in LINT.lint_file(
            nested_button, "all", "general", None, None, style="ui")))
    aria_label = root / "aria.html"
    aria_label.write_text('<button aria-label="儲存Redis">x</button>\n')
    check("HTML accessible name uses typography rules", any(
        item.code == "typography.cjk-latin-spacing" for item in LINT.lint_file(
            aria_label, "all", "general", None, None, style="ui")))
    casual_label = root / "casual-label.html"
    casual_label.write_text('<input aria-label="抱歉，出了點問題" />\n')
    check("HTML accessible name uses UI wording rules", any(
        item.code == "wording.ui-casual" for item in LINT.lint_file(
            casual_label, "all", "general", None, None, style="ui")))
    escaped_ui = root / "escaped-ui.json"
    escaped_ui.write_text('{"button": "\\u5132\\u5b58\\u8b8a\\u66f4\\u3002"}\n')
    check("escaped JSON UI value is decoded", any(
        item.code == "ui.control-punctuation" for item in LINT.lint_file(
            escaped_ui, "all", "general", None, None, style="ui")))
    escaped_prose = root / "escaped-prose.json"
    escaped_prose.write_text('{"message": "\\u5176\\u5be6\\u5df2\\u7d93\\u641e\\u5b9a\\u3002"}\n')
    check("escaped JSON prose is decoded", any(
        item.code == "wording.discourse-filler" for item in LINT.lint_file(
            escaped_prose, "prose", "general", None, None, style="strict")))
    escaped_emoji = root / "escaped-emoji.json"
    escaped_emoji.write_text('{"message": "\\ud83d\\ude00"}\n')
    check("escaped JSON Emoji is decoded", any(
        item.code == "style.emoji" for item in LINT.lint_file(
            escaped_emoji, "prose", "general", None, None, style="strict")))
    emoji_url = root / "emoji-url.md"
    emoji_url.write_text("[連結](https://example.org/😀)\n")
    check("Emoji in a URL is excluded", not any(
        item.code == "style.emoji" for item in LINT.lint_file(
            emoji_url, "prose", "general", None, None, style="strict")))
    minified_json = root / "minified.json"
    minified_json.write_text('{"class":"' + "字" * 200 + '","message":"正常"}\n')
    check("minified JSON values are checked independently", not any(
        item.code == "prose.paragraph-length" for item in LINT.lint_file(
            minified_json, "prose", "general", None, None, style="ui")))

    invalid_directory = root / "invalid-directory"
    invalid_directory.mkdir()
    (invalid_directory / "broken.md").write_bytes(b"\xff\xfe\x00")
    invalid_result = run(
        [sys.executable, str(TARGET), "--format", "json", str(invalid_directory)],
        check=False, capture_output=True, text=True)
    invalid_payload = json.loads(invalid_result.stdout)
    check("invalid UTF-8 text in a directory is reported", (
        invalid_result.returncode == 1
        and invalid_payload["findings"][0]["code"] == "io.read"))

    common_simplified = root / "common-simplified.md"
    common_simplified.write_text(FIXTURES["simplified_country"] + "\n")
    check("locale catches common country character", any(
        item.code == "locale.wrong-script" for item in LINT.lint_file(
            common_simplified, "prose", "general", None, None, "zh-TW")))
    neighborhood = root / "neighborhood.md"
    neighborhood.write_text("里民大會於明日舉行。\n")
    check("Traditional neighborhood wording is allowed", not any(
        item.code.startswith("locale.") for item in LINT.lint_file(
            neighborhood, "prose", "general", None, None)))
    terminology_comparison = root / "terminology-comparison.md"
    terminology_comparison.write_text(
        "簡體中文使用“软件”，繁體中文使用「軟體」。\n")
    check("terminology comparison is excluded", not any(
        item.code in {"locale.wrong-script", "terminology.locale"}
        for item in LINT.lint_file(
            terminology_comparison, "prose", "general", None, None, "zh-TW")))

    hardlink_source = root / "hardlink-source.md"
    hardlink_alias = root / "hardlink-alias.md"
    hardlink_source.write_text("版本2。\n")
    os.link(hardlink_source, hardlink_alias)
    hardlink_before = hardlink_source.read_bytes()
    hardlink_result = run(
        [sys.executable, str(TARGET), "--kind", "prose", "--fix",
         str(hardlink_source)],
        check=False, capture_output=True, text=True)
    check("safe fix refuses files with hard links", (
        hardlink_result.returncode == 1
        and "multiple hard links" in hardlink_result.stdout
        and hardlink_source.read_bytes() == hardlink_before
        and hardlink_alias.read_bytes() == hardlink_before
        and hardlink_source.stat().st_ino == hardlink_alias.stat().st_ino))

    nested_rust = root / "nested.rs"
    nested_rust.write_text(
        "/* outer /* inner */ " + FIXTURES["bad_comment"] + " */\n")
    check("nested Rust comment is recognized", any(
        item.code == "comments.language" for item in strict_lint_file(
            nested_rust, "source", "general", None, None)))
    supplementary_han = root / "supplementary.js"
    supplementary_han.write_text("// 𠀀\n")
    check("supplementary Han comment is recognized", any(
        item.code == "comments.language" for item in strict_lint_file(
            supplementary_han, "source", "general", None, None)))
    unicode_separator = root / "unicode-separator.md"
    unicode_separator.write_text(
        "正常。\u2028" + FIXTURES["masked_colloquial"] + "\n")
    separator_lines = [item.line for item in strict_lint_file(
        unicode_separator, "prose", "general", None, None)
                       if item.code == "wording.discourse-filler"]
    check("Unicode line separator advances diagnostics", separator_lines == [2])

    multiline_button = root / "multiline-button.html"
    multiline_button.write_text(
        "<button>\n  <span>刪除。</span>\n</button>\n")
    button_lines = [item.line for item in LINT.lint_file(
        multiline_button, "all", "general", None, None, style="ui")
                    if item.code == "ui.control-punctuation"]
    check("multiline button reports the text line", button_lines == [2])
    reference_link = root / "reference-link.md"
    reference_link.write_text("[這裡][guide]\n\n[guide]: /guide\n")
    check("reference-style generic link is rejected", any(
        item.code == "markdown.generic-link" for item in LINT.lint_file(
            reference_link, "prose", "general", None, None, style="readme")))
    wrapped_list = root / "wrapped-list.md"
    wrapped_list.write_text("- 第一項。\n  補充說明\n- 第二項\n")
    check("wrapped list keeps punctuation context", any(
        item.code == "markdown.list-punctuation" for item in LINT.lint_file(
            wrapped_list, "prose", "general", None, None, style="readme")))
    negative_limit = run(
        [sys.executable, str(TARGET), "--paragraph-limit=-1", str(markdown_clean)],
        check=False, capture_output=True, text=True)
    check("negative paragraph limit is rejected", (
        negative_limit.returncode == 2
        and "greater than zero" in negative_limit.stderr))
    obvious_comment = root / "obvious-comment.py"
    obvious_comment.write_text("# 建立空列表\nitems = []\n")
    check("optional comment audit catches syntax narration", any(
        item.code == "comments.obvious" for item in LINT.lint_file(
            obvious_comment, "source", "general", None, None,
            comment_audit=True)))
    rationale_comment = root / "rationale-comment.py"
    rationale_comment.write_text(
        "# Keep insertion order for the serialized compatibility format.\nitems = []\n")
    check("optional comment audit retains rationale", not any(
        item.code == "comments.obvious" for item in LINT.lint_file(
            rationale_comment, "source", "general", None, None,
            comment_audit=True)))
    translated_upstream = root / "translated-upstream.md"
    translated_upstream.write_text(FIXTURES["translated_upstream_name"] + "\n")
    upstream_findings = LINT.lint_file(
        translated_upstream, "prose", "general", None, None, "zh-TW")
    check("translated upstream name is flagged", len([
        item for item in upstream_findings
        if item.code == "terminology.preserved"]) == 1)
    check("guarded name finding stays advisory", all(
        item.severity == "warning" for item in upstream_findings
        if item.code == "terminology.preserved"))
    translated_inline = root / "translated-inline.md"
    translated_inline.write_text(FIXTURES["translated_upstream_inline"] + "\n")
    check("guarded name is found in inline code", any(
        item.code == "terminology.preserved" for item in LINT.lint_file(
            translated_inline, "prose", "general", None, None, "zh-TW")))
    translated_case = root / "translated-case.md"
    translated_case.write_text(FIXTURES["translated_upstream_case"] + "\n")
    check("guarded name allows case and plural variation", any(
        item.code == "terminology.preserved" for item in LINT.lint_file(
            translated_case, "prose", "general", None, None, "zh-TW")))
    unrelated_substring = root / "unrelated-substring.md"
    unrelated_substring.write_text(FIXTURES["unrelated_name_substring"] + "\n")
    check("guarded name requires an English word boundary", not any(
        item.code == "terminology.preserved" for item in LINT.lint_file(
            unrelated_substring, "prose", "general", None, None, "zh-TW")))
    fenced_name = root / "fenced-name.md"
    fenced_name.write_text(FIXTURES["translated_upstream_fence"] + "\n")
    check("guarded name in a fence is excluded", not any(
        item.code == "terminology.preserved" for item in LINT.lint_file(
            fenced_name, "prose", "general", None, None, "zh-TW")))
    untraced = root / "untraced-rendering.md"
    untraced.write_text(FIXTURES["untraced_rendering"] + "\n")
    check("guarded name needs its English form present", not any(
        item.code == "terminology.preserved" for item in LINT.lint_file(
            untraced, "prose", "general", None, None, "zh-TW")))
    project_terms = root / "terms.json"
    project_terms.write_text(json.dumps({"preserve_translations": [{
        "en": "binhost", "domain": "gentoo", "reject": ["二進位主機"],
        "note": "binhost is the service name used in this repository"}]},
        ensure_ascii=False))
    project_guarded = root / "project-guarded.md"
    project_guarded.write_text(FIXTURES["project_guarded_name"] + "\n")
    check("project terms extend the guarded names", any(
        item.code == "terminology.preserved" for item in LINT.lint_file(
            project_guarded, "prose", "general", None, None, "zh-TW",
            extra_terms=LINT.load_terms(project_terms))))
    invalid_terms = root / "invalid-terms.json"
    invalid_terms.write_text(json.dumps({"preserve_translations": [{
        "en": "binhost", "domain": "gentoo", "note": "missing reject"}]}))
    invalid_result = subprocess.run(
        [sys.executable, str(TARGET), "--terms", str(invalid_terms),
         str(project_guarded)], capture_output=True, text=True)
    check("invalid project terms are a CLI error",
          invalid_result.returncode == 2
          and "reject must be" in invalid_result.stderr
          and "Traceback" not in invalid_result.stderr)
    check("bundled seeds stay out of unrelated projects", not any(
        item.code == "terminology.preserved" for item in LINT.lint_file(
            project_guarded, "prose", "general", None, None, "zh-TW")))
    huge_page = root / "huge-page.md"
    huge_page.write_text(FIXTURES["huge_page_article"] + "\n")
    check("huge page article keeps its own term", not any(
        item.code == "terminology.preserved" for item in LINT.lint_file(
            huge_page, "prose", "general", None, None, "zh-TW")))

raise SystemExit(1 if failures else 0)
