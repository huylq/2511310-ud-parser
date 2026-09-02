# TESTING.md — Project 1: Word Segmentation & POS Tagging

> **Template.** Fill in every section below with your own reasoning before
> submission. This is read by hand during manual review (see
> `student-projects/README.md`'s "The gate" section) — it is your
> demonstration that you understand your own implementation, not a
> restatement of the gate's mechanical checks. Delete this notice line
> when you submit.

## Segmentation approach

*What did you build (dictionary-based, statistical, hybrid), and why did
you choose it over the alternatives? Reference `DESIGN.md` from Task 1 if
useful.*

## Compound dictionary

*Where did your compound entries come from beyond
`tests/fixtures/corpus/known_compounds.txt`? How many entries? How would
you grow it further given more time?*

## Hard cases and how you resolved them

*For each of the following, state your decision and reasoning:*
- Compound ambiguity (e.g. `"học sinh"` vs. `"học"` + `"sinh"`)
- Reduplication
- Register-specific spelling (teencode, non-diacritic)

## POS tagging approach

*Closed-class word lists: how did you build them and how confident are
you they're complete? Open-class heuristics: what signals do you use to
distinguish `NOUN`/`VERB`/`ADJ`?*

## Your adversarial test case

*What is it, and what specifically does it stress-test? Why did you
expect it might be hard for your implementation?*

## Known limitations

*What do you know is imperfect or unhandled, and why did you decide not
to fix it in the time available?*

## DeepSeek refinement (if attempted)

*Your reconciliation rule between your rule-based tag and a DeepSeek
suggestion, and why you trust it not to introduce unvalidated model
output into a `source="real"` result (CLAUDE.md rule 2).*
