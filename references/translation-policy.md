# Technical translation policy

Translation quality is measured by preserved terminology, reference, scope, and verifiable
facts, not by fluency. A fluent rendering of a misread term states a different fact with
more confidence than the source did.

## Separate the three operations

Translation, polishing, and fact checking are separate passes. Finish terminology before
rhythm and paragraph structure. Polishing may not change a confirmed term, number,
condition, path, or code literal.

A language model is not a terminology authority. It cannot know whether an English phrase
is an identifier, a data structure, a subsystem, an implementation detail, or an ordinary
noun in the current project. When a term cannot be verified, keeping the English form is
more accurate than choosing a plausible rendering.

Passing `chinese_lint.py` does not verify terminology, kernel mechanics, API semantics, or
a performance conclusion. Those need upstream documentation, project usage, or a citable
authority.

## Classify before translating

Assign every English fragment to one class, then apply its treatment.

| Class | Treatment | Example |
| --- | --- | --- |
| Identifier, command, path, flag, system call | Keep verbatim in code formatting | `GET_CSUMS`, `openat2(2)`, `/proc/filesystems` |
| Upstream name without a settled Chinese term | Keep the English name; explain its role once only when the reader needs it | `folio`, `swap table`, `sub-scheduler` |
| General concept with an established target-locale term | Verify the authority, then use that term | cache, load balancing, memory reclaim, regular file |
| Ordinary narrative text | Rewrite in the target locale, keeping subject, condition, and causality | `在高負載下`, `僅適用於特定工作負載` |

None of the following justifies translating a term: a dictionary entry exists, machine
translation produced one, the Chinese reads smoothly, another project used it, or the
English word looks like an ordinary noun.

## Known failure modes

- Dropping the head of the phrase. The head of `cache-aware load balancing` is load
  balancing; a scheduler rendering removes the mechanism and widens the change.
- Treating neighbouring concepts as synonyms. `folio` is not `page`; `large folios` and
  `huge folios` are specific objects, and 大頁 names a huge page instead.
- Turning an implementation name into a category. `dm-inlinecrypt` and
  `device-mapper target` are named implementations, not storage targets or encryption
  mechanisms.
- Breaking code and API semantics. `OPENAT2_REGULAR`, `O_EMPTYPATH`, `LOOKUP_EMPTY`,
  `/dev/tbstreamX`, `read(2)`, and `write(2)` are not translatable text. Whether
  `file descriptor` takes an established Chinese term depends on locale convention; its
  referent and API behavior never change.
- Promoting a scoped observation to a general conclusion. Keep the workload, baseline,
  time range, and test condition attached to every measured claim.
- Choosing the delivery language from the chat script. The deliverable's locale comes from
  the explicit request and the source contract, not from the script of the latest message.

## Decision order

1. Fix the deliverable's locale, region, and audience; one writing system throughout.
2. List every identifier, API, path, subsystem, data structure, protocol name, and
   performance assertion in the source.
3. Read upstream documentation, commit messages, or source comments to confirm each term's
   object, operation, boundary, and difference from neighbouring concepts.
4. Choose by evidence rank: project usage, upstream documentation, an authoritative
   terminology database, then other citable sources. Dictionaries and corpora supply
   candidates only.
5. Keep the English form when no stable Chinese term exists. Do not coin one for
   consistency of appearance.
6. Only then adjust grammar, rhythm, and structure.

## Constraints

- Do not translate identifiers, commands, paths, APIs, device nodes, configuration keys, or
  kernel symbols.
- Do not generalize an implementation name into a product category, design goal, or
  user-visible feature.
- Do not delete a qualifier, comparison baseline, test condition, unit, or uncertainty.
- Do not turn `尚未發現`, `可用於`, `預計`, or `在某些場景中` into a commitment.
- Do not settle kernel terminology from model memory, word frequency, or fluency.
- Do not mix Simplified and Traditional Chinese. When regional terms differ and the target
  region is unstated, keeping the English term beats picking one region's rendering.
- Do not accept a smoother rewrite before the source meaning is confirmed.

A guarded name is a project decision, not a fixed list. `references/technical-terms.json`
carries a small seed under `preserve_translations`; a project supplies its own names with
`chinese_lint.py --terms <file>`, using the same fields and overriding a seed by `en`. The
linter reports a rendering only when the document also contains the English name, and
reports it as a warning under `terminology.preserved`. Confirm the object before accepting
or dismissing one.

## Before delivery

- The locale matches the source contract or the explicit request.
- Every code literal, identifier, path, command, and API is unchanged.
- Every translated technical term has upstream, project, or authoritative support.
- Every retained English term has a stated reason: identifier, upstream name, or no stable
  target-locale term.
- Every performance, regression, security, and compatibility claim keeps its original
  condition, scope, and attribution.
- No abstract name was replaced by a similar-looking ordinary noun.
