# Lexicon policy

## Source order

Choose terminology in this order:

1. active repository instructions and accepted text;
2. the named project's official documentation and identifiers;
3. Gentoo Devmanual or Linux kernel documentation for their own concepts;
4. official terminology databases for the requested locale, starting with the
   bundled NAER cross-strait computing terms;
5. OpenCC, the MediaWiki regional tables, and CC-CEDICT as conversion or dictionary
   evidence;
6. McBopomofo, jieba, and Moegirl as candidate or boundary corpora only.

A lower source never overrides a higher source. Frequency, dictionary presence, and
character conversion do not prove that a term is correct in context.

## Locale handling

Determine both script and region. `zh-CN`, `zh-TW`, `zh-HK`, and generic Traditional
Chinese may use different words even when the characters convert cleanly. Follow the
user and repository; do not force Taiwan vocabulary merely because the text is
Traditional Chinese.

Use OpenCC for conversion diagnostics, not automatic acceptance. Review every
one-to-many character mapping and every regional phrase change in context.

`chinese_lint.py --regional` derives regional vocabulary from the OpenCC phrase
tables and the MediaWiki conversion tables, so it reports candidates rather than
decided terms. `technical-terms.json` outranks it, `regional_exceptions` in
`wording.json` records forms that are correct in both regions, and every remaining
finding needs a human decision. The check stays opt-in for that reason.

## Technical terminology

Preserve product names, commands, APIs, variables, file names, package atoms, Gentoo
metadata keys, ebuild phase functions, eclasses, `USE` flags, `SLOT`, subslot, and
EAPI names. Translate surrounding prose, not identifiers.

For Gentoo and Linux, verify the concept in upstream documentation before choosing a
Chinese term. For development terminology, prefer the repository's existing term;
otherwise use the relevant platform terminology database.

## Corpus limits

CC-CEDICT proves that a headword and its paired form were recorded; it does not prove
the word is suitable for technical prose. Unihan supplies character relationships,
not word conversion.

McBopomofo supplies Traditional Chinese input candidates and frequencies. It contains
several regional and competing forms, so presence is not approval.

The jieba dictionary supplies word boundaries only. The linter uses it, CC-CEDICT, and
McBopomofo to suppress a match that sits inside a longer word; word frequency there is
not evidence of correct terminology.

NAER records official Taiwan terms with their Mainland counterparts. A row often lists
several accepted Chinese forms; choose by domain and repository usage instead of taking
the first form.

The optional Moegirl source supplies article titles and proper names across popular
culture. Use it to check spelling or preserve a known title. Do not use it to decide
grammar, register, technical terminology, or professional tone.

## Required evidence

When changing a disputed term, record the requested locale, domain, selected source,
source form, rejected alternative, and contextual reason. If authoritative sources
conflict, show the alternatives and ask the directing human.

Run `scripts/lexicon_lookup.py` for evidence. Never describe a term as authoritative
when the result comes only from a candidate corpus.

`scripts/lexicon_lookup.py --reference` lists the external databases that are not
bundled, each with its authority label. `official-terminology` and `upstream-project`
outrank `vendor-terminology`, which outranks `community-translation`. Record which
source supplied the accepted form.
