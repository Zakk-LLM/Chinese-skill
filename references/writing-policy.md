# Chinese writing policy

## Order of information

Write in this order when the fields exist:

1. result or failure;
2. concrete evidence;
3. impact;
4. required action.

Omit absent fields. Do not add an introduction or final recap.

## Check grammar and logic

- Give every finite statement a clear subject when context does not supply one.
- Place modifiers next to the word they modify.
- Replace pronouns such as `這個`, `它`, and `相關內容` when more than one referent is possible.
- Distinguish fact, inference, decision, and required action. Do not present an inference as evidence.
- State a cause only when it is verified. Use an explicit causal link when the conclusion depends on it.
- Remove a connector when the two clauses have no causal, contrastive, or sequential relationship.
- Keep one time frame and one point of view within a procedure.

Read the completed paragraph aloud by clause. A grammatical sentence can still be illogical; verify that each conclusion follows from the preceding evidence.

## Rewrite translations by meaning

- Identify the source statement's fact, actor, action, condition, and effect before writing Chinese.
- Rebuild the sentence in natural Chinese order. Do not preserve English syntax merely because it is grammatical.
- Use the term accepted by the repository, platform, or standard. Do not create a Chinese equivalent for an identifier or established technical name.
- Remove source-language filler, duplicated subjects, nominalized verbs, unnecessary passive voice, and translated metaphors.
- Do not mix English words into Chinese for emphasis. Retain English only for identifiers, commands, product names, protocol names, or established technical terms.
- Do not mix Simplified and Traditional Chinese in one artifact unless the artifact deliberately contains separate locale fixtures.

Machine translation may provide a draft, never evidence that terminology, grammar, or causality is correct. Compare the final text with the source meaning rather than the source sentence shape.

## Replace colloquial operations wording

Use the direct verb for an action and a precise state for a continuing process. Name
the installed version, expected version, failed operation, missing value, or retained
object. Avoid conversational negation when a precise state is available.

The linter's disallowed forms are stored in `wording.json`; deliberate examples used
by regression tests are isolated in `copy-fixtures.json`.

## Remove discourse filler

Delete introductory and transitional phrases that add no fact, relationship, or
instruction. State the fact directly and do not replace one filler phrase with
another. The maintained forms are in `wording.json`.

## Avoid AI-style and invented wording

Reject marketing language, unsupported absolutes, vague abstractions, and ad-hoc
coinages. The maintained forms are in `wording.json`.

Name the actual variable, phase, service, file, state transition, or user action.
Do not anthropomorphize software. Do not create a novel label when the ecosystem
already has a term.

## Keep Chinese native

- Choose Simplified or Traditional Chinese from the user and repository context.
- Use standard Mandarin that is readily understood across regions.
- Do not translate English syntax word for word.
- Preserve established technical names such as `USE`, `RESTRICT`, `SRC_URI`,
  `systemd`, and `nginx`.
- Do not insert English adjectives where a concrete Chinese description is clearer.
- Use Chinese punctuation in Chinese sentences and ASCII punctuation inside code.

## Comment gate

Ask in order:

1. Does the comment repeat an assignment, command, function call, option, type, or
   obvious branch? Delete it.
2. Does it explain standard language, framework, eclass, or tool behavior? Delete it
   or link the authoritative source outside the code when needed.
3. Can a clearer name or smaller function express the intent? Refactor instead.
4. Does a future maintainer need a non-obvious invariant, security boundary,
   compatibility constraint, trade-off, or workaround? Keep one concise English
   comment.

Do not add comments for QA suppressions merely to restate the suppression. Do not
write incident narratives in code. Put operational history in an issue or commit
rationale when it remains relevant.

Preserve required license notices, SPDX identifiers, generated-file warnings, tool
directives, and necessary lint suppressions. Keep their mandated syntax unchanged.
If a suppression needs a rationale, state only the non-obvious false positive,
constraint, or remaining risk; do not explain what the directive does.

Before adding or rewriting a comment, confirm the repository's language and format rules. If no rule or accepted pattern answers a material choice, ask the directing human. Do not add a comment merely because the code changed.

## Do not teach established mechanics

Assume the reviewer understands the programming language, framework, build system, version control, and standard repository workflow. Do not explain syntax, obvious control flow, routine commands, or facts already shown by the diff. Explain only the non-obvious constraint or decision needed to assess or maintain the change.

Apply this rule to comments, README files, developer documentation, reviews, commit bodies, and PR bodies. Necessary onboarding material is not obvious by definition; state the intended audience before including it.

## Length control

- Remove duplicate context already visible in the title, diff, error, or command.
- Keep normal paragraphs within four sentences.
- Split independent findings into bullets; do not add a prose summary of the bullets.
- Use one example unless multiple examples establish different behavior.
- Do not report routine passing checks unless the user requested them or a test changed
  the implementation decision.
- Stop after the answer, decision, or actionable list is complete.
