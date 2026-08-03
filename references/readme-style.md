# README writing policy

## Use the repository contract first

Read the repository instructions, current README, contribution guide, templates, and
supported commands before editing. Preserve required headings, badges, links, locale
switches, command syntax, and project-specific terms. A repository rule overrides this
reference.

For gentoo-zh overlay, read the live `README.md` and the target locale file. They define
project-specific entry points and contribution conventions. Do not treat their wording
as a universal template or include them in the historical cutoff.

## Write for tasks

Open with one sentence that names the project, its type, and its primary purpose. Then
include only sections needed by the intended reader:

1. requirements or supported environment;
2. installation;
3. the shortest working usage path;
4. configuration or compatibility constraints;
5. contribution, support, and license links.

Order prerequisites before the action that depends on them. Put a command next to the
sentence that explains its input or observable result. Keep uncommon cases in separate
documentation and link them from the relevant task.

Do not add a section merely because another README has it. A library, command-line tool,
service, package repository, and reference collection need different structures.

## Use direct sentences

- State what the project is, what the command does, or what condition applies.
- Use headings that name tasks or subjects, such as `安裝`, `使用`, and `參與貢獻`.
- Use imperative sentences for required actions and declarative sentences for facts.
- Define a term once; use the same form throughout the file.
- Keep one complete example for the common path.
- Explain only non-obvious constraints, inputs, results, and recovery actions.

Remove article narration, era-setting introductions, promotional adjectives, work
diaries, repeated navigation, and conclusions that restate the introduction. Do not use
Emoji as section decoration. Avoid local slang, honorific filler, rhetorical questions,
and appeals for support unless the repository explicitly requires them.

## Learn professional prose, not casual tone

README text may follow the logic of a serious technical article when it defines a
concept, compares designs, explains a constraint, or records a compatibility decision.
Use the relevant professional pattern only when the passage needs that function.

- Define a term by category and distinguishing property, not by analogy or slogan.
- Put scope, version, environment, and assumptions before the claim they limit.
- Separate facts, observations, inferences, decisions, and recommendations.
- Support a conclusion with the preceding evidence; do not insert a causal connector
  when the relationship is only sequential or coincidental.
- Compare alternatives on the same named dimensions.
- Give each complete sentence a subject and predicate unless the preceding sentence
  supplies an unambiguous subject.
- Place conditions and modifiers next to the action or claim they limit.
- Keep the grammatical subject stable. Replace ambiguous pronouns with the exact object.
- Keep headings and parallel list items in the same grammatical form.
- Use complete sentences. Do not imitate chat fragments, rhetorical questions, audience
  address, jokes, or conversational transitions found in a source.

For a long explanation, use the `technical` or `academic` style and read
`writing-policy.md`. The README should retain only the portion required to install, use,
evaluate, or contribute to the project.

## Use the historical corpus carefully

`readme-corpus.json` records structural observations from Chinese open-source README
revisions dated no later than 2019. The cutoff reduces the likelihood of generated prose;
it does not prove that every line was written without automated assistance. Each pinned
file records its Git blob identifier, and each corpus-derived pattern names at least two
supporting sources. Patterns marked `policy` are editorial rules, not source findings.

The corpus stores no source excerpts. Use its patterns for information order and sentence
function, not as text to copy. Each source also lists defects that must not be learned.
Old commands, terminology, badges, links, and compatibility claims are evidence about the
old revision only.

Do not open the full corpus during ordinary README work. List the available identifiers,
then retrieve only the required pattern or source:

```bash
python3 scripts/corpus_lookup.py readme --list
python3 scripts/corpus_lookup.py readme --pattern identity
python3 scripts/corpus_lookup.py readme --source gogs-2019
```

Use the `readme` lint style for a draft:

```bash
python3 scripts/chinese_lint.py --kind prose --style readme README.md
```

The linter also checks skipped heading levels, trailing full stops in headings, generic
link text, inconsistent list punctuation, deterministic Chinese typography, and terms
that change form within one document. `--fix` changes only deterministic typography and
heading punctuation. It cannot verify commands, compatibility, audience coverage,
missing prerequisites, list grammar, or whether a section is useful.
