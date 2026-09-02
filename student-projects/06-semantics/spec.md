# Project 6: Semantics / FOL — Design

Compact skeleton — see `student-projects/01-word-seg-pos/spec.md` for the
full worked-example depth this compresses.

## Goal

```
to_logical_form(parse: interfaces.ud.DependencyParse) -> interfaces.semantics.LogicalForm
```

Translate a UD dependency parse into a neo-Davidsonian first-order
logical form, type-checked against Project 5's ontology predicate
signatures. Consumes Project 2's output (stub or real) and Project 5's
ontology (the frozen seed, or its extended real form once merged).

## Target representation & Vietnamese-specific problems — from `.claude/agents/semantics-engineer.md`

Fold this in whole; it is your standard, not a suggestion:

> The target representation: events are reified as variables, thematic
> roles are binary predicates, and the form serialises as an
> S-expression.
>
> *Nam mua một cuốn sách ở Hà Nội.*
> ```
> (exists (e x)
>   (and (buy e) (agent e nam_1) (theme e x) (book x)
>        (location e hanoi_1) (past e)))
> ```
>
> Vietnamese-specific problems you must handle rather than paper over:
>
> - **No inflectional tense.** Tense comes from particles (`đã`, `đang`,
>   `sẽ`) or from context, and is frequently absent. Emit an
>   underspecified temporal constraint rather than defaulting to present
>   — a false `(present e)` is worse than no tense predicate.
> - **Classifiers are not quantifiers.** `một cuốn sách` is `một` (one) +
>   `cuốn` (classifier) + `sách` (book). The classifier constrains the
>   sort of the noun; it does not bind a variable.
> - **Bare nouns** are number- and definiteness-neutral. `Tôi mua sách`
>   may be one book or many. Do not silently insert an existential with
>   cardinality one.
> - **Scope is underspecified by design.** Store the scope-neutral form
>   plus the constraint set. Committing to a reading at parse time throws
>   away information you cannot recover.
> - **Topic-comment structures** front a constituent that is not the
>   syntactic subject. The topic is not automatically the agent.
>
> Every form is type-checked against predicate signatures derived from
> the ontology. A type failure means one of three things — the parse is
> wrong, the ontology lacks the predicate, or the signature is wrong.
> Diagnose which. Do not widen a signature to `owl:Thing` to make a
> failure go away; that disables the check for everything.

`interfaces.semantics.is_balanced()` checks well-formedness only
(matched parens) — semantic/type correctness is entirely your
type-checker's job, reflected in `LogicalForm.type_checked`.

## Non-Goals

- UD parsing (Project 2) or ontology modelling (Project 5) — you consume
  both, you don't redesign either.
- A complete formal semantics for all of Vietnamese — scope to what the
  fixture corpus's sentence types actually require; document what's out
  of scope in `TESTING.md`.

## Testing

Required input classes: a classifier phrase handled correctly (not as a
quantifier), a tense-ambiguous sentence (underspecified, not defaulted),
`degenerate`, `adversarial`.

Golden invariant: balanced-parens + type-check pass rate over a
threshold.
