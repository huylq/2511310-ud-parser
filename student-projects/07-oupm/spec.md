# Project 7: OUPM Entity Resolution — Design

Compact skeleton — see `student-projects/01-word-seg-pos/spec.md` for the
full worked-example depth this compresses.

## Goal

```
cluster(entities: list[interfaces.ner.NamedEntity], chains: list[interfaces.ner.CorefChain]) -> list[interfaces.oupm.EntityCluster]
```

Cluster mentions (possibly across documents) into entities, inferring the
number of distinct entities rather than assuming it — this is the
"open-universe" part. Consumes Project 3's output (stub or real) and
Project 5's ontology types. Test data:
`tests/fixtures/oupm/oupm_coref_probe.jsonl` — **PROVISIONAL**, see
`tests/fixtures/oupm/PROVISIONAL.md`. 12 documents, each built around one
specific entity-resolution trap (surname collision, diacritic variant,
honorific stripping, same-name-different-people, and more — see the
PROVISIONAL doc's full table).

## Generative structure & Vietnamese name channel — from `.claude/agents/oupm-modeler.md`

Fold this in whole; it is your standard, not a suggestion:

> Generative structure:
> ```
> #Entity      ~ CRP(alpha)
> type(e)      ~ Categorical(ontology classes)
> canonical(e) ~ NameModel(type(e))
> entity(m)    ~ CRP assignment
> surface(m)   ~ NoisyName(canonical(entity(m)))
> ```
>
> The Vietnamese name channel is the part that generic coreference
> systems get wrong:
>
> - **Surnames carry almost no information.** Roughly 40% of the
>   population is `Nguyễn`. A surname match is close to worthless as
>   evidence; a system that weights it like an English surname will
>   over-merge catastrophically.
> - **Given-name reference is the norm.** `Nguyễn Văn Nam` is referred to
>   as `Nam`, not `Nguyễn`. This is the opposite of English convention.
> - **Middle names** (`Văn`, `Thị`) are near-deterministic gender markers
>   and weak identity evidence.
> - **Honorifics** (`anh`, `chị`, `ông`, `bà`, `em`, `cô`) attach to given
>   names and are not part of the name.
> - **Diacritic-stripped variants** must map to the same canonical form:
>   `Nguyen Van Nam` and `Nguyễn Văn Nam` are one person.
>
> Sampler discipline:
> - Metropolis-Hastings with **split-merge moves** over the mention
>   partition. Gibbs alone mixes far too slowly over partitions — it
>   cannot move two mentions together.
> - Report R-hat and effective sample size. A chain that has not mixed
>   produces confident nonsense, and the posterior over entity count is
>   exactly where it shows.
> - Evaluate with B-cubed, CEAF and MUC. Report all three; B-cubed alone
>   hides systematic over-merging.
>
> When a result looks too good, check for leakage from the canonical name
> into the mention features before believing it.

A full MCMC sampler is ambitious for 15 weeks alongside coursework — a
well-justified simpler clustering approach (e.g. agglomerative clustering
over a hand-designed similarity function that correctly encodes the
Vietnamese-name-channel facts above, with `posterior` as a similarity-
derived confidence rather than a true MCMC posterior) is an acceptable,
honestly-scoped submission. Document in `TESTING.md` which approach you
took and why — this is exactly the kind of design trade-off the professor
wants to see reasoned about, not hidden.

## Non-Goals

- Ontology modelling (Project 5) or NER/coref within one document
  (Project 3) — you consume both.
- A production-grade MCMC implementation with full convergence
  diagnostics, unless you choose to attempt it.

## Testing

Required input classes: a surname-collision case correctly NOT merged, a
diacritic-variant case correctly merged, `degenerate`, `adversarial`.

Golden invariant: B³/CEAF/MUC against the probe's gold clustering (or a
simpler precision/recall on cluster membership if you scope down the
evaluation — document which you used and why).
