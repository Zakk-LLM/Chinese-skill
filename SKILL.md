---
name: chinese-skill
description: Enforce concise, professional Chinese across articles, pasted text, chat, README files, documentation, UI copy, alerts, logs, tests, source code, comments, reviews, commits, and pull requests. Use when Claude, Codex, or OpenCode writes, rewrites, polishes, improves, translates, reviews, or audits Chinese; when producing technical or professional articles; when text may contain grammatical errors, literal or machine-like translation, formulaic AI wording, emoji, weak computing, programming, Linux, or Gentoo terminology, colloquial wording, invented terms, mixed languages or locales, missing causality, complex sentences, obvious comments, repetition, or excessive detail; and whenever preparing Chinese PR or review text for gentoo-zh repositories.
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
- Use standard Chinese that readers in China, Taiwan, Hong Kong, Singapore, and
  Malaysia can understand without local slang. A locale's established technical term,
  such as `程式碼`, remains valid when the artifact uses that locale.
- Keep technical terms in their established English form when translation reduces precision.
- Use backticks for identifiers and literal values. Do not wrap ordinary Chinese terms in `「」` or `『』`.
- Do not add Emoji when the selected style rejects it.

Use the locale-appropriate term meaning execution for a command, script, phase, test, or action. Use the term meaning operation for an ongoing program, service, system, or deployed code version. Do not replace either with a colloquial motion verb.

Read [references/writing-policy.md](references/writing-policy.md) when rewriting or auditing more than a short paragraph.

## Write and revise prose

For an article, pasted passage, rewrite, polish, or translation, first identify the
audience, purpose, locale, facts, required terms, and allowed degree of change. Preserve
code, commands, links, quotations, numbers, and verified claims unless the user asks to
change them.

Use the requested operation precisely:

- Write: organize the verified facts before drafting.
- Rewrite: reorganize sentences and paragraphs while preserving meaning.
- Polish: correct grammar, wording, rhythm, and terminology without adding facts.
- Shorten: remove repetition, framing, examples, and background that are not required.
- Professionalize: replace conversational or promotional language with evidence,
  constraints, measured effects, and established domain terms.

Default to a conservative rewrite when the user gives no detailed style contract:
preserve meaning and formatting, use the source locale, remove clear formulaic wording,
split confusing sentences, and return only the revised text. Ask before changing the
audience, position, factual claim, quotation, or technical meaning.

For a cross-regional audience, keep one script throughout the artifact and prefer shared
standard vocabulary. Do not combine Simplified and Traditional variants to display both.
When no precise shared Chinese term exists, retain the established English term or define
the selected locale term once; do not replace a correct local technical term merely
because another region uses a different term.

## Load details only when needed

Use the standard style unless the user or repository requests `strict`, `academic`,
`technical`, `readme`, or `ui`. Strict style rejects Emoji, Chinese code comments,
formulaic framing, short quoted terms, and fixed prose limits. The other styles retain
only the constraints appropriate to their document type.

Keep context use proportional to the task:

1. Use this file for the core workflow.
2. Read only the one task policy named below. Read a second policy only when the task
   crosses both domains.
3. Do not open a corpus JSON file or lexicon manifest by default. Retrieve one pattern or
   one source with the lookup scripts. Read a complete data file only when maintaining or
   validating that file.

When maintaining corpus metadata, run `scripts/verify_corpora.py` and
`scripts/test_corpora.py`. Do not run the network verifier for ordinary writing tasks.

- For articles, rewrites, translations, long passages, or comment audits, read
  [references/writing-policy.md](references/writing-policy.md).
- For README writing or revision, read
  [references/readme-style.md](references/readme-style.md). If a concrete structure or
  sentence pattern is still needed, run `scripts/corpus_lookup.py readme --list`, then
  retrieve one entry with `--pattern`.
- For UI copy, message catalogs, notifications, forms, errors, confirmations, tooltips,
  or accessible names, read [references/ui-style.md](references/ui-style.md). If the
  interface contract does not settle the wording, retrieve only the relevant UI pattern
  with `scripts/corpus_lookup.py ui --pattern <id>`.
- For terminology, localization, Gentoo, Linux, or disputed wording, read
  [references/lexicon-policy.md](references/lexicon-policy.md), then use
  `scripts/lexicon_lookup.py` for the disputed term. Do not load a complete dictionary.
- For commits, PRs, reviews, issue replies, or release notes, read
  [references/pr-policy.md](references/pr-policy.md).
- For gentoo-zh overlay work, read the live repository `AGENTS.md`, then
  [references/overlay-policy.md](references/overlay-policy.md). The live file wins.

Repository instructions and accepted examples define the audience, locale, terminology,
format, template, and confirmation rule. Ask before proceeding only when an unresolved
choice would change meaning or cause an external action.

Use the shortest form that preserves the decision, evidence, impact, and required action.
Delete obvious comments. Follow the repository's comment language; strict and
gentoo-overlay styles require concise English comments for non-obvious invariants,
security boundaries, compatibility constraints, trade-offs, or workarounds.

Never sign as an AI. Remove model attribution from every file, commit, PR, review, and
comment. Human trailers with a real address remain allowed.

Run `scripts/chinese_lint.py <paths>` before completing a wording audit. Use `-` for
standard input. Treat findings as candidates; grammar warnings, logic, meaning, and
comment value still require manual review. Use `--fix` only for deterministic typography;
it does not authorize automatic wording or grammar changes. Command variants and profile
rules are documented in the task-specific references and `README.md`.

## Final check

Before sending or publishing Chinese text, verify:

1. The first sentence states the outcome or issue.
2. Every sentence adds a distinct fact, reason, impact, or action.
3. Terms match the repository and ecosystem.
4. No colloquial transition or operation verb, invented term, needless English, or locale mixing remains.
5. Regional technical terms remain understandable or are defined once for the audience.
6. No paragraph repeats the title, diff, list, or previous paragraph.
7. Every retained comment passes the comment gate and follows the repository language.
8. PR and commit text contains rationale, not a work diary or routine test report.
9. A revised draft did not grow without a new required fact.
10. No disallowed Emoji or decorative symbol remains under the selected style.
11. The response ends when the requested information is complete.
