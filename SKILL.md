---
name: chinese-skill
description: Enforce concise, professional Chinese across every file and developer workflow, including chat, README files, documentation, UI copy, alerts, logs, tests, source code, comments, reviews, commits, and pull requests. Use when Claude, Codex, or OpenCode writes, rewrites, reviews, or audits Chinese; when text may contain grammatical errors, literal or machine-like translation, weak computing, programming, Linux, or Gentoo terminology, colloquial wording, invented terms, mixed languages or locales, missing causality, obvious comments, repetition, or excessive detail; and whenever preparing Chinese PR or review text for gentoo-zh repositories.
---

# Chinese Writing Control

## Keep the rules alive

Read this file at the start of every work item. Read it again after context compaction, summary restoration, a long tool run, task switching, or any sign that earlier instructions may have been lost. Before sending user-visible text or preparing a commit, PR, or review, run the final check below.

Read repository instruction files again at the same checkpoints. Repository-specific terminology and formats override this skill; this skill still governs clarity, brevity, comments, and Chinese style.

## Write directly

- Lead with the result, fact, failure, or required action.
- Use concrete names: files, variables, phases, commands, services, versions, and states.
- State causality explicitly with `因為…所以…` when the reason matters.
- Remove preambles, recap paragraphs, repeated conclusions, self-evaluation, and rhetorical transitions.
- Do not invent terms, metaphors, or vague labels. Use the ecosystem's established term.
- Keep one idea per sentence and one reason per paragraph.
- Match the requested locale. Do not mix Simplified and Traditional Chinese in one artifact.
- Keep technical terms in their established English form when translation reduces precision.
- Use backticks for identifiers and literal values. Do not wrap ordinary Chinese terms in `「」` or `『』`.

Use the locale-appropriate term meaning execution for a command, script, phase, test, or action. Use the term meaning operation for an ongoing program, service, system, or deployed code version. Do not replace either with a colloquial motion verb.

Read [references/writing-policy.md](references/writing-policy.md) when rewriting or auditing more than a short paragraph.

## Verify terminology

Read [references/lexicon-policy.md](references/lexicon-policy.md) before translating,
normalizing, or disputing a term. Repository and ecosystem usage outrank every bundled
dictionary.

Search all terminology layers with:

```bash
python3 <skill-dir>/scripts/lexicon_lookup.py '<term>'
```

Replace `<skill-dir>` with the directory containing this `SKILL.md`.

The result labels each source's authority. NAER supplies official Taiwan and Mainland
computing terms; OpenCC and the MediaWiki tables supply conversion and regional
evidence; CC-CEDICT supplies headwords; Unihan supplies character variants. THUOCL
and Rime essay supply domain candidates and word-boundary evidence only.

McBopomofo supplies Traditional Chinese input candidates. Optional Moegirl and Chinese
Wikipedia snapshots supply names and titles after installation with
`sync_lexicons.py --source <source>`. Never cite a candidate corpus as professional
terminology evidence. Keep each optional source's license and attribution with it.

When the bundled sources disagree or the term is absent, list the external terminology
databases to consult, then verify the term in the highest-authority one that covers the
domain:

```bash
python3 <skill-dir>/scripts/lexicon_lookup.py --reference
```

Preserve Gentoo metadata, package atoms, ebuild phases, commands, APIs, variables, and
identifiers. For Gentoo or Linux concepts, verify upstream documentation before choosing
a Chinese term.

## Resolve the contract first

Before writing a code comment, commit, PR, or review, read the repository instructions and recent accepted examples. Determine the audience, locale, terminology, required template, title format, body format, and confirmation rule.

If these facts remain unclear and the choice would materially change the result, ask the directing human before drafting or publishing. Do not invent a format, infer an unverified cause, or translate a convention from another repository.

## Control length

Default to the shortest text that preserves the decision, evidence, impact, and next action.

- Chat update: one short paragraph or a small list.
- Alert or log: condition, impact, and action; normally one line each.
- Code comment: one to three lines.
- Review finding: severity, location, concrete failure, and required correction.
- PR body: rationale only. Do not narrate the implementation, repeat the diff, list routine passing tests, or retell the review history.

Use a list only when several independent facts must remain separately actionable. Do not add a summary that repeats the list.
Do not add headings, change inventories, completion claims, or author narration to a PR body. When revising a draft, do not increase its characters, blocks, or list items unless a missing required fact justifies the increase. Apply the budgets in [references/pr-policy.md](references/pr-policy.md).

## Apply the comment gate

Delete a comment when the code, identifier, type, command, standard setting, or nearby control flow already says the same thing.

Keep a comment only when a future maintainer must preserve a non-obvious invariant, security boundary, compatibility constraint, trade-off, or workaround that cannot be expressed clearly in code. Write retained code and configuration comments in concise English, not Chinese.

Treat docstrings, shell comments, YAML comments, HTML comments, CSS comments, Markdown code-block comments, example configuration comments, and fixture comments as comments. Keep deliberate invalid-language test data in a dedicated fixture file, not in production code or test output.

Preserve required license notices, SPDX identifiers, generated-file warnings, tool directives, and necessary lint suppressions. These are metadata or tool controls, not explanatory comments; do not expand them into prose.

Read [references/writing-policy.md](references/writing-policy.md) before a comment sweep.

## Write commits, PRs, and reviews

Apply the same standard to commit subjects and bodies, PR titles and bodies, review comments, issue replies, release notes, and CI messages.

Do not submit or amend a commit, PR, or review until its format and scope are known. When confirmation is required, show the exact proposed text; do not substitute a description of it.

When asked to draft a title, body, comment, or commit message for direct use, return only that artifact unless the user asks for analysis. Do not surround it with an assistant preface, change log, or recap.

For gentoo-zh overlay work, read the live repository `AGENTS.md` at the start and after context compaction, then read [references/overlay-policy.md](references/overlay-policy.md). The live repository file wins if it changed.

For PR or commit work in any repository, read [references/pr-policy.md](references/pr-policy.md). Before calling `gh pr create` or `gh pr edit`, show the exact title, body, and files when repository policy requires confirmation.

## Audit deterministically

Run the linter before completing a wording sweep:

```bash
python3 <skill-dir>/scripts/chinese_lint.py <paths>
```

The default `all` mode checks Chinese wording, prose length, and supported code-comment
syntax in one pass. Use `--kind source` or `--kind prose` only for a deliberately
restricted check.

Add `--regional` to a locale sweep when regional vocabulary must be reviewed. It
derives candidates from the conversion tables, so every finding needs a decision:

```bash
python3 <skill-dir>/scripts/chinese_lint.py \
  --kind prose --locale zh-TW --regional <paths>
```

Specify the locale when regional terminology must be enforced:

```bash
python3 <skill-dir>/scripts/chinese_lint.py \
  --kind prose --locale zh-TW <paths>
```

For a commit message, the check also covers subject length, the blank second line,
and, with the overlay profile, English subject, `scope: summary` form, and AI
attribution trailers:

```bash
python3 <skill-dir>/scripts/chinese_lint.py \
  --kind commit-message --profile gentoo-overlay message.txt
```

For a gentoo-zh overlay PR body and title:

```bash
python3 <skill-dir>/scripts/chinese_lint.py \
  --kind pr-body --profile gentoo-overlay --title 'category/package: summary' body.txt
```

PR mode checks the authored description before a recognized repository-template marker. It enforces the profile's character, block, and list-item budgets and rejects headings, title repetition, work narration, completion claims, and routine passing reports.

Treat linter output as a minimum set, not proof that prose is good. A script cannot reliably determine grammar, translation quality, terminology, logic, or whether a comment is useful.

Manually review every Chinese passage in every file, including README files, HTML attributes, notifications, tests, fixtures, documentation, comments, docstrings, commit text, and PR text.

## Final check

Before sending or publishing Chinese text, verify:

1. The first sentence states the outcome or issue.
2. Every sentence adds a distinct fact, reason, impact, or action.
3. Terms match the repository and ecosystem.
4. No colloquial transition or operation verb, invented term, needless English, or locale mixing remains.
5. No paragraph repeats the title, diff, list, or previous paragraph.
6. Every retained comment passes the comment gate and is concise English.
7. PR and commit text contains rationale, not a work diary or routine test report.
8. A revised draft did not grow without a new required fact.
9. The response ends when the requested information is complete.
