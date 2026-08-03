# Pull request and review policy

## Confirm the repository contract

Read the active repository instructions, PR template, commit template, contribution guide, and recent accepted examples. Confirm the target branch, scope, locale, title convention, body convention, required checks, and whether exact text needs approval.

If a material choice is still unknown, ask before drafting a comment, commit, PR, or review. Do not copy the gentoo-zh format into an unrelated repository. Do not invent an issue reference, cause, test result, or acceptance condition.

## Write the smallest useful PR body

Use the title for what changed. Use the body only for facts a reviewer cannot infer
from the diff and needs to judge the change.

Prefer this shape:

```text
Because <verified cause>, <behavior or constraint>; therefore <required change>.

Closes #N
```

Use numbered points only for independent causal changes. Do not add headings for a
single reason.

The standard style follows the repository's template and imposes no additional heading,
block, list, or character limit. Under the strict style, keep the authored description
within 600 non-space characters, four semantic blocks, and five list items. The
gentoo-zh overlay limits are 360 characters, three blocks, and four list items.
`Closes #N` does not consume a block.

Treat every sentence as having a cost. Keep it only when deleting it would hide a
verified cause, review constraint, non-obvious impact, or required issue link. Under
the strict style, do not add summary, change, or testing headings and do not turn the
diff into an inventory. Repository-required headings always take precedence.

When revising an existing draft, do not increase its character, block, heading, or
list-item count unless the revision adds a required fact that was absent. Replacing
colloquial or imprecise wording is not permission to add an explanation.

## Never sign as an AI

Do not add `Generated with`, `AI-Generated-By`, `Claude-Session`, a `Co-authored-by` naming a
model, or any other trailer that credits a model or agent, in any repository and in any
artifact. This rule has no exception for tooling defaults; remove the trailer before
committing. `chinese_lint.py` enforces it for every kind and profile.

Trailers that credit people stay allowed. `Co-authored-by: Alice <alice@example.org>` and
`Signed-off-by: Zakk <zakk@example.org>` pass in every profile; only a routing address such
as `@users.noreply.github.com` is rejected, because a sign-off needs the contributor's real
email.

## Exclude work-diary content

Do not include:

- how many review findings existed;
- a chronological account of attempts;
- statements that all checks are green;
- a list of commands that passed;
- claims that the change is comprehensive;
- praise or criticism of the previous implementation;
- a repeated summary after the body;
- details already visible in the diff.
- `本次 PR`, `主要包含`, `已完成`, `已完善`, `已補齊`, or similar narration;
- first-person accounts such as `我已修改` or `我們新增`;
- unsupported assurances such as `全面支援`, `確保全部正確`, or `所有功能正常`.

Mention a test only when its result changed the design decision or proves a subtle
counterexample that the reviewer cannot infer otherwise.

## Preserve required templates

Do not remove, reorder, rewrite, or summarize a repository's required template. Put
free-form text in the location named by its marker and tick only checks that ran.
Character, block, heading, list, and routine-test rules apply to the authored
description, not the unchanged template. A completion report requested by repository
instructions remains a separate handoff; do not paste it into the PR body.

## Return the requested artifact only

When the user asks for a PR title or body that will be pasted or submitted, return the
exact artifact without an assistant introduction, explanation, review summary, or
closing recap. If repository policy requires approval before publication, present the
exact title, body, and file list as separate labeled fields; add nothing to those fields.

## Review comments

Start with severity and location when reviewing code. State the concrete failing input
or state, its impact, and the acceptance condition. Do not address the author, speculate
about intent, or pad the finding with praise.

Example:

```text
P1 — `publish.sh:49`: a missing or non-numeric `SIZE` skips validation and reaches the
transfer phase. Require exactly one integer `SIZE` per stanza and abort before ssh or
rsync; add missing, duplicate, and non-numeric fixtures.
```

Use the repository's review format when one exists. Otherwise confirm the expected severity and location notation before producing a review intended for submission.
