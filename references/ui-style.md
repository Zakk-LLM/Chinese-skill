# Chinese UI writing policy

## Confirm the interface contract

Read the source message, component context, product glossary, locale guide, and nearby
accepted strings. Identify whether the text is a control label, field label, placeholder,
help text, status, validation message, error, confirmation, toast, tooltip, or accessible
name. The same sentence does not work for every surface.

Preserve message keys, placeholders, markup tokens, keyboard accelerators, shortcuts,
product names, and stable identifiers. Confirm the available action before promising it.

If an unknown surface, interface state, available action, placeholder meaning, character
budget, or target locale would change valid wording, ask for the smallest missing fact.
Otherwise return the requested strings in their existing key order or the requested
order. Do not add alternatives or commentary to paste-ready copy unless requested.

## Use the shortest complete form

- Use a direct verb for an action. Add the object only when context does not identify it.
- Use a noun phrase for a field, tab, column, section, or state label.
- Use a complete sentence for an explanation, error cause, consequence, or recovery step.
- Keep the subject explicit when more than one object is visible.
- Place the condition before the instruction it limits.
- Keep parallel controls and list items in the same grammatical form.
- Do not address the reader unless the distinction between user and system matters.

Do not use chat fragments, jokes, apologies, rhetorical questions, promotional claims,
Emoji, or exclamation marks. Replace `抱歉` and `出了點問題` with the failed operation.
Replace `點擊這裡` with the action or destination name.

## Match the interface state

- Pending: use one ongoing marker, such as `正在載入…` or `載入中`, not both.
- Success: state the completed action and object. Do not reuse a button label as a toast.
- Failure: state `無法 + action + object`; add a verified cause and available recovery.
- Validation: name the missing value, accepted form, range, or conflict beside the field.
- Empty: distinguish no data from no matching result before offering an action.
- Confirmation: name the action, object, irreversible effect, and safer alternative.

Do not claim success before the operation completes. Do not use an error message as an
empty state or a toast as the only persistent failure signal.

## Apply UI punctuation

Short buttons, menu items, labels, headings, tabs, and placeholders have no terminal
punctuation. Explanations and recovery instructions use normal Chinese punctuation.
Use `…` for an ongoing UI state or visible truncation; use `……` in ordinary Chinese prose.
Do not use three ASCII periods after Chinese text.

Preserve punctuation required by placeholders, code, paths, and keyboard syntax. Do not
copy English capitalization, colon placement, or question-mark style into Chinese.

## Keep locales separate

Author Simplified and Traditional catalogs separately. Do not derive one by character
replacement. Follow the locale's established technical terms while keeping the message
understandable to the product audience. A Cantonese catalog may use Cantonese; do not use
it as the source for cross-regional standard Chinese.

Keep one canonical source for repeated product names and actions. Keep identifiers and
enum values untranslated; translate them only at render time. Preserve every interpolation
placeholder exactly and verify it against the source message.

## Use the corpus as evidence, not copy

`ui-corpus.json` records patterns from pinned Grafana, Nextcloud, Mastodon, Discourse,
GNOME Control Center, and Visual Studio Code localization files. Every selected revision
predates 2022-11-30 and records its Git blob identifier. Each pattern names at least two
supporting projects. The cutoff and translator metadata reduce uncertainty but do not
prove how every string was authored or that every source string is suitable.

Every source contains wording that should not be copied. Use a pattern only when it fits
the current surface and repository. Prefer product terminology and native review over a
majority vote across old catalogs.

Do not open the full corpus during ordinary UI work. List the available surfaces, then
retrieve only the required pattern. Use `--locale` when evidence from one locale is
required:

```bash
python3 scripts/corpus_lookup.py ui --list
python3 scripts/corpus_lookup.py ui --pattern failure --locale zh-TW
python3 scripts/corpus_lookup.py ui --source grafana-2022
```

Check candidate text with the UI style:

```bash
python3 scripts/chinese_lint.py --kind prose --style ui path/to/catalog
```

For HTML-like files and direct JSON or YAML string entries, the linter recognizes common
button, label, title, tooltip, placeholder, `alt`, and `aria-label` surfaces. It rejects
terminal punctuation on those surfaces and exclamation marks in Chinese UI text.

Static checks cannot verify an unknown message key, the available recovery action,
placeholder parity, semantic accessible naming, parallel grammar, truncation, or the
rendered longest locale. Review those properties separately.
