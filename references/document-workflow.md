# Substantial document workflow

Use this workflow only for a new document or a major structural rewrite. Do not use it
for a short passage, UI string, PR body, commit message, or local wording correction.

## Set the document contract

Read the repository template, adjacent documents, accepted terminology, and requested
locale. Resolve only the fields that change the result:

- primary audience and what they already know;
- document purpose and the decision or task it must support;
- required template, scope, and exclusions;
- verified facts, sources, examples, and commands;
- expected outcome and any required approval.

Infer a field from repository evidence when the answer is clear. Combine unresolved
material questions into one short request; do not conduct an interview for routine facts.
If the source omits a target, location, prerequisite, command argument, or acceptance
condition required by the requested scope, ask before drafting. When the missing detail is
outside the intended scope, narrow the title and opening sentence instead of implying that
the document covers it.

## Choose the document function

Choose one primary function for each section. A complete document may contain several
functions, but do not mix them within one paragraph or procedure.

- Tutorial: lead a learner through a controlled exercise that produces a known result.
- How-to guide: give an experienced reader the shortest supported path to a stated task.
- Reference: record complete, consistent facts for lookup without tutorial narration.
- Explanation: establish concepts, reasons, constraints, and trade-offs without posing as
  an operating procedure.

Move long background out of a procedure. Move task steps out of reference material. A
README remains an entry point and should link detailed material instead of containing all
four functions.

## Establish the evidence boundary

Before drafting, separate source facts, user-provided claims, observations, inferences,
decisions, proposals, and future commitments. Record the source or basis internally when
the distinction is not obvious.

Do not convert an unsupported improvement, reliability, completeness, or future-behavior
claim into polished factual prose. Ask for the missing baseline, measurement, mechanism,
scope, public commitment, or issue. If the format permits placeholders, mark the missing
evidence instead. Never replace one unverifiable claim with another.

Verify commands, options, API fields, UI labels, versions, and links against the supplied
artifact or an authoritative source. Preserve uncertainty when verification is unavailable.

## Draft procedures

- State prerequisites and applicable conditions before the dependent action.
- Start each step with the action; keep one required decision or action per item.
- Name the location or object instead of using directional language such as `上方` or
  `下方`.
- Put an observable result after the action only when the reader needs it to decide whether
  to continue.
- Describe failure recovery only when the source establishes the symptom, cause, and
  available action. If no recovery exists, state that constraint directly.
- Do not interrupt ordered steps with background, commentary, or unrelated alternatives.

Avoid generic checks such as `確認正常` and generic recovery such as `重試看看`. Name the
expected state, output, version, or acceptance condition.

## Test the reader contract

Apply a fresh-reader test to a substantial document when ambiguity, missing context, or a
wrong action would materially affect the reader. Skip it for minor edits.

When a fresh agent is available, provide only the document and three to five realistic
reader questions. Ask it to identify unsupported answers, ambiguous references, hidden
prerequisites, contradictions, and steps whose success cannot be observed. Do not reveal
the intended answer or the earlier conversation.

Without a fresh agent, perform the same checks against the document alone. Revise only
the failed contract; do not add general background to make the document appear complete.

## Prune the result

Remove paragraphs that do not change a reader's decision, action, interpretation, or
ability to verify the result. After repeated revisions, compare section and paragraph
counts with the earlier draft. Growth requires a new fact, decision, constraint, or
required example.

Source provenance is stored in `writing-sources.json`. Retrieve one pattern when evidence
is needed instead of loading the full source index:

```bash
python3 scripts/corpus_lookup.py writing --list
python3 scripts/corpus_lookup.py writing --pattern reader-test
```
