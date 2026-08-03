#!/usr/bin/env python3
"""Regression tests for chinese_lint.py."""

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
from functools import partial


sys.dont_write_bytecode = True
TARGET = pathlib.Path(__file__).with_name("chinese_lint.py")
SPEC = importlib.util.spec_from_file_location("chinese_lint", TARGET)
LINT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LINT)
strict_lint_file = partial(LINT.lint_file, style="strict")
FIXTURES = json.loads((TARGET.parent.parent / "references" /
                       "copy-fixtures.json").read_text())


def check(name, condition):
    global failures
    print(f"{'PASS' if condition else 'FAIL'} {name}")
    failures += not condition


failures = 0
with tempfile.TemporaryDirectory() as base:
    root = pathlib.Path(base)
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
    yaml_data = root / "data.yaml"
    yaml_data.write_text("message: |\n  # 中文正文\n")
    check("YAML block scalar is not a comment", not any(
        "comments" in item[1]
        for item in strict_lint_file(yaml_data, "source", "general", None, 280)))
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

    stdin_result = subprocess.run(
        [sys.executable, str(TARGET), "--kind", "prose", "--style", "strict", "-"],
        input=FIXTURES["stdin_article"] + "\n", text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    check("standard input", stdin_result.returncode == 1
          and "narrating the article" in stdin_result.stdout)

    inline_code = root / "inline-code.md"
    inline_code.write_text("Pattern: `" + FIXTURES["stdin_article"] + "`\n")
    check("inline code is excluded from prose rules", not strict_lint_file(
        inline_code, "prose", "general", None, 280))

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
    check("selected locale disables consistency advice", not any(
        item.code.startswith("consistency.") for item in LINT.lint_file(
            mixed_terms, "prose", "general", None, None,
            "zh-TW", style="technical")))

    json_result = subprocess.run(
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
    clean_json_result = subprocess.run(
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
    fix_result = subprocess.run(
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
    second_fix = subprocess.run(
        fix_command, check=False, capture_output=True, text=True)
    check("safe fix is idempotent", (
        second_fix.returncode == 0
        and "fixed " not in second_fix.stdout
        and fix_target.read_bytes() == fixed_bytes))
    grammar_fix = root / "grammar-fix.md"
    grammar_fix.write_text(FIXTURES["grammar_defects"] + "\n")
    before_grammar_fix = grammar_fix.read_text()
    subprocess.run(
        [sys.executable, str(TARGET), "--kind", "prose", "--style",
         "technical", "--fix", str(grammar_fix)],
        check=False, capture_output=True, text=True)
    check("safe fix does not rewrite grammar", (
        grammar_fix.read_text() == before_grammar_fix))
    stdin_fix = subprocess.run(
        [sys.executable, str(TARGET), "--kind", "prose", "--fix", "-"],
        input="測試。\n", check=False, capture_output=True, text=True)
    check("safe fix rejects standard input", (
        stdin_fix.returncode == 2
        and "does not accept standard input" in stdin_fix.stderr))

raise SystemExit(1 if failures else 0)
