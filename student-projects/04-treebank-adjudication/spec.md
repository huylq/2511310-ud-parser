# Project 4: Treebank Curation & Adjudication — Design

Compact skeleton — see `student-projects/01-word-seg-pos/spec.md` for the
full worked-example depth this compresses.

## Goal

```
adjudicate(sent_id: str, system_a: tuple[UDToken, ...], system_b: tuple[UDToken, ...]) -> interfaces.treebank.AdjudicatedSentence
```

Given two candidate UD analyses of the same sentence (e.g. Project 2's
real parser vs. a perturbed/alternate system, or two annotator passes),
produce a final, adjudicated analysis plus a record of every decision —
which field disagreed, what the two candidates said, what you decided,
and why. Also compute an `IAAReport` (inter-annotator-agreement) over the
gold seed set.

Test data: `tests/fixtures/treebank/gold_treebank_seed.conllu` +
`system_b_perturbed.conllu` — **PROVISIONAL**, see
`tests/fixtures/treebank/PROVISIONAL.md`; treat `gold_treebank_seed.conllu`
as "system A" for your `adjudicate()` calls, since it is itself a full UD
analysis, not literally "the truth" your job outputs — adjudication means
producing YOUR OWN ruling given two candidates, which happens to often
agree with the professor's gold seed but must be independently justified.

## Adjudication standard — from `.claude/agents/treebank-adjudicator.md`

Fold this in whole; it is your standard, not a suggestion:

> Your ruling must contain:
>
> 1. **The competing analyses**, stated fairly. Steelman the one you will
>    reject.
> 2. **The deciding principle** — a UD v2 guideline, a UD_Vietnamese-VTB
>    precedent, or a stated consistency argument. "It reads better" is
>    not a principle.
> 3. **The ruling**, in CoNLL-U.
> 4. **The generalisation** — the rule this case establishes for future
>    instances, written so an annotator can apply it without re-deriving
>    your reasoning.
> 5. **Precedent conflicts** — if this contradicts an earlier ruling in
>    the treebank, say so and propose the re-annotation scope. Silent
>    inconsistency is worse than a wrong-but-consistent convention.
>
> If the honest answer is that the construction needs a documented
> convention that does not yet exist, say that and draft the convention.
> Do not manufacture a confident ruling to close a ticket.
>
> Inter-annotator agreement gates: Cohen's kappa >= 0.80 for POS, LAS
> agreement >= 90%. If your rulings are what is holding agreement up, the
> guidelines are the problem.

`interfaces.treebank.AdjudicationDecision.rationale` is where points 1-2
above go, in prose, per decision — `validate_adjudicated_sentence` rejects
an empty rationale for exactly this reason: a bare pick with no stated
reasoning is not an adjudication.

## Non-Goals

- Producing the two candidate systems yourself (they're given — a real
  parser's output and a perturbed alternate, or two annotators' passes).
- CoNLL-U file I/O for the wider corpus (this project's scope is the
  adjudication function and the IAA computation, not a corpus-wide
  treebank-export pipeline).

## Testing

Required input classes: at least one decision with a genuine, defensible
`rationale` (not "system A is usually right"), a kappa/agreement
computation you can explain, `degenerate`, `adversarial`.
