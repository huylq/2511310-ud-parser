# Project 5: Ontology Engineering — Design

Compact skeleton — see `student-projects/01-word-seg-pos/spec.md` for the
full worked-example depth this compresses.

## Goal

```
induce_individual(entity: interfaces.ner.NamedEntity) -> interfaces.ontology.OntologyIndividual
```

Plus: extend `tests/fixtures/corpus/seed_upper_ontology.ttl` with your own
domain classes/properties as needed, and produce `AlignmentRecord`s
linking your classes to Wikidata. Consumes Project 3's NER output (stub
or real). The seed ontology is **frozen** at its 8 upper classes
(`Entity`, `Person`, `Organization`, `Place`, `Event`, `Artifact`,
`Concept`, `TemporalEntity`) — every class you add must attach under one
of these (see `tests/test_fixture_seed_ontology.py` for the check your
own additions should also satisfy).

## Modelling discipline — from `.claude/agents/ontology-engineer.md`

Fold this in whole; it is your standard, not a suggestion:

> - **Classes are not lexemes.** `Người` the word and `Person` the class
>   are different objects. Vietnamese kinship terms (`anh`, `chị`, `em`,
>   `cô`, `chú`, `bác`) encode relative age and lineage side; do not
>   model them as sixteen sibling classes when they are one class plus
>   properties.
> - **Disjointness is an assertion, not decoration.** Every disjointness
>   axiom you add will eventually make some individual inconsistent. Add
>   it only when you mean it.
> - **Alignment to Wikidata** is `owl:sameAs` only for genuine identity.
>   Use `skos:closeMatch` for the common case where the Vietnamese
>   concept and the Wikidata item overlap but do not coincide —
>   administrative divisions (`xã`, `huyện`, `tỉnh`) are the usual trap.
> - **Property characteristics** (functional, transitive, symmetric) are
>   where reasoners find contradictions. Justify each one.
>
> On an inconsistency:
> 1. Get the explanation from the reasoner — the justification set, not
>    just the error.
> 2. Identify the minimal axiom set that causes it.
> 3. Say which axiom is *wrong*, not merely which one you could remove to
>    silence it. Removing the true axiom to preserve the false one is the
>    standard failure mode.
>
> Every class you add needs a Vietnamese label, an English label, and a
> definition that lets an annotator decide membership. A class nobody can
> apply consistently is worse than an absent class.

The seed ontology already encodes the kinship-as-property and
`skos:closeMatch`-for-admin-units decisions correctly — read
`src/vietnlp/interfaces/ontology.py`'s docstring and the seed file itself
before adding anything, so you extend the existing pattern rather than
contradicting it.

## Non-Goals

- Entity resolution / clustering (Project 7).
- FOL predicate signatures (Project 6 reads your ontology's property
  domains/ranges as its type-checking signatures — you don't produce FOL
  yourself).

## Testing

Required input classes: a kinship-term individual modelled correctly
(property, not class), an alignment using `skos:closeMatch` correctly,
`degenerate`, `adversarial`.

Golden invariant: the reasoner reports the ontology + your induced
individuals CONSISTENT.
