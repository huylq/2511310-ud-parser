# Project 3: NER & Coreference Resolution — Design

Compact skeleton — see `student-projects/01-word-seg-pos/spec.md` for the
full worked-example depth this compresses.

## Goal

```
extract_entities(sentence: interfaces.linguistics.SegmentedSentence) -> list[interfaces.ner.NamedEntity]
resolve_coref(entities: list[NamedEntity]) -> list[interfaces.ner.CorefChain]
```

Consumes Project 1's output (stub or real). NER labels one of
`PER`/`LOC`/`ORG`/`MISC` per span; `token_start`/`token_end` are 0-based,
end-exclusive indices into the SAME sentence's tokens — a span is a
Python slice, never a character offset (see `interfaces/ner.py`'s own
anti-hallucination note: locate spans against the source yourself, never
trust a model-reported offset). Coreference groups mentions across
sentences of the same document that refer to the same entity.

## Linguistic grounding

Full names are single PER spans, never split at given/family name
boundary — Vietnamese names are Family + Middle + Given
(`Nguyễn Văn Nam`), and per `.claude/agents/oupm-modeler.md` (Project 7's
persona, directly relevant here too): **given-name reference is the
norm** — `Nguyễn Văn Nam` is later referred to as `Nam`, not `Nguyễn`
(the opposite of English convention). Honorifics (`anh`, `chị`, `ông`,
`bà`, `em`, `cô`) attach to given names and are **not part of the
name span** — exclude them.

## Non-Goals

- Entity clustering across a whole corpus / open-universe entity count
  inference (Project 7 — you produce mention-level chains within one
  document; Project 7 consumes your output for cross-document
  resolution).
- Ontology class assignment (Project 5 — you only emit `PER`/`LOC`/`ORG`/
  `MISC`, a coarse NER label, not an ontology class).

## Testing

Required input classes (gate step 7): a full name that must NOT be split
at a name-part boundary, an honorific that must be excluded from the
span, a degenerate case (sentence with zero entities — a valid, common
case, not an error), an adversarial case.

Golden invariant: entity text occurs verbatim (NFC-normalized) at its
claimed span (reuse the pattern from
`platform/agents/registry.py::_validate_ner`).
