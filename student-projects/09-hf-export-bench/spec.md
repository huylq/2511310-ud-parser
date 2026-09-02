# Project 9: HF Export & Benchmark Harness — Design

Compact skeleton — see `student-projects/01-word-seg-pos/spec.md` for the
full worked-example depth this compresses. This is the terminal project —
nothing downstream consumes its output.

## Goal

```
export_document(doc: dict) -> list[interfaces.export.ExportRow]
```

Denormalize `tests/fixtures/serving/gold_fixture.json`'s documents into
the flat, one-row-per-sentence `ExportRow` shape and write an HF-dataset-
shaped directory (a `datasets.Dataset`-loadable structure, or your own
JSONL-per-split layout if you don't want the `datasets` dependency —
document your choice), plus a dataset card documenting all four
`interfaces.export.REQUIRED_CARD_SECTIONS`. Also build a benchmark
harness that scores against the three format-shape stand-ins in
`tests/fixtures/benchmark/*_stub.jsonl` (VLSP NER, UIT-VSFC, ViQuAD —
**explicitly not the real shared-task data**, see
`tests/fixtures/benchmark/README.md`), producing `BenchmarkReport`s.

## Non-Goals

- Sourcing or licensing the real VLSP/UIT-VSFC/ViQuAD datasets (out of
  scope for the 15 weeks — the stand-ins exist exactly so you don't need
  to).
- Every other project's real annotation output — you export whatever
  `gold_fixture.json` contains today (stub-quality throughout, since no
  other project has necessarily merged real work yet); your export
  pipeline's correctness does not depend on annotation quality.

## The one hard requirement: dataset card completeness

`interfaces.export.validate_dataset_card()` checks for exactly four
sections: `register_taxonomy`, `normalization`, `license`,
`known_limitations`. The `normalization` section specifically must state
NFC normalization and that the original input-method form is preserved
upstream (CLAUDE.md's Vietnamese-specific notes) — a generic "text is
UTF-8 encoded" line does not satisfy this; be specific about NFC.

## Testing

Required input classes: at least one register represented, an NFC-
normalization check on exported text, `degenerate` (a document with zero
sentences, if your loader can produce one), `adversarial`.

Golden invariant (`tests/golden/test_hf_export_benchmark_golden.py`,
authored in a later pass): row count matches source; required
`BenchmarkReport` metric keys present with values in range; every
`BenchmarkReport` scored against a stand-in carries a non-empty
`stub_note`.
