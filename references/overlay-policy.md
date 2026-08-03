# gentoo-zh overlay writing rules

Source: [gentoo-zh/overlay AGENTS.md](https://github.com/gentoo-zh/overlay/blob/master/AGENTS.md), read on 2026-08-03.

Read the live source before overlay work. Use this file as a compact working copy of
the writing, commit, PR, and comment rules, not as a replacement for the repository
file.

## Common writing standard

- Keep commit messages, PRs, comments, notes, and replies precise, plain, and short.
- Name concrete variables, phases, USE flags, `FEATURES`, eclasses, and commands.
- Use current Gentoo terminology; do not invent a paraphrase or adjective.
- State cause and effect explicitly. Do not use vague connectors such as `相應`.
- Use Simplified or Traditional Chinese consistently and avoid regional slang.
- Do not put ordinary Chinese terms in full-width brackets. Use backticks only for
  identifiers and literal values.

## Commit and PR text

- Use `pkgdev`'s final English subject verbatim as the PR title.
- Use `category/package: summary`; a bump is `category/package: add NEW`, optionally
  followed by `, drop OLD`.
- For a non-package change, begin the subject with the affected eclass, path, or
  filename so the scope is identifiable without the body.
- Keep the subject on one line and at most 69 characters where the prefix permits.
- Add a body only when the subject cannot carry the reason.
- Put only the reason in the body. Do not narrate steps, restate the diff, repeat the
  title, report routine passing tests or scans, or explain mechanisms a Gentoo
  reviewer already knows. Link the relevant upstream source when it supplies the
  evidence.
- The subject already states the package, version, and add/drop operation. State each
  value once and do not open the body with `更新到 <version>` or another title restatement.
- Give each changed dependency, phase, patch, USE flag, `RESTRICT`, or revbump its own
  causal line. Do not invent causality or attach an unrelated fact as a parenthetical.
- For a large rewrite or upstream restructure, name the rewritten scope instead of
  inventorying each edit. Use one causal line such as `因為上游修改了 X，所以重寫 Y`;
  add another line only for an unexpected behavior change.
- Put variables, atoms, commands, options, and `FEATURES` values in backticks.
- Write the PR body in Chinese when the directing human writes in Chinese; otherwise
  use English. Never mix both languages in one body.
- Use the same rationale in the commit and PR body. Do not list tested architectures;
  the template and CI carry routine results. Mention a test only when it forced a change.
- A routine or behavior-neutral issue fix needs only bare `Closes #N`.
- Keep overlay GitHub issues out of `pkgdev commit -b/--bug` and `-c/--closes`; those
  options use bare numbers for Gentoo Bugzilla and full URLs for other trackers.
- Do not add AI attribution, generated-by trailers, or any `Co-Authored-By` trailer.
- Let `pkgdev` generate trailers and use the contributor's real identity and email,
  never a GitHub noreply address.
- Keep one logical change per clean squashed commit; use one commit per package in a
  multi-package PR. Every commit must leave its ebuild, `Manifest`, metadata, licenses,
  files, and eclasses complete and installable. Land shared prerequisites first.
- Commit with `pkgdev commit --scan false --signoff --gpg-sign`; omit `--gpg-sign` only
  when GPG is unavailable. Do not use raw `git commit`.
- Preserve the PR template. Put the description above
  `<!-- Please put the pull request description above -->`, leave its checklist intact,
  and mark only checks that ran.
- Before `gh pr create` or `gh pr edit`, show the exact title, body, and files and get
  confirmation for that PR, including a draft. A batch instruction is not confirmation
  for each PR.
- After publication, watch CI and correct failures from the job logs.

The repository's required completion report is a separate handoff containing branch,
remote, base, changed files, command results, skipped checks, and remaining risks. Do
not copy that report into the PR description.

## Code comments

- Prefer clear naming, established helpers, direct control flow, and simple structure.
- Keep comments only for non-obvious intent, constraints, trade-offs, or workarounds
  that future maintainers must preserve.
- Do not restate eclass-documented assignments, declarations, commands, standard
  settings, or QA suppressions such as `QA_PREBUILT` and `QA_SONAME`.
- Preserve useful existing comments unless they are outdated or incorrect.

This skill adds one stricter cross-repository rule requested by the maintainer:
retained code and configuration comments must be concise English, not Chinese.
