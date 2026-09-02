# Benchmark format-shape stand-ins

`vlsp_ner_stub.jsonl`, `uit_vsfc_stub.jsonl`, `viquad_stub.jsonl` -- small
(10-12 row), hand-authored files shaped like the three CLAUDE.md benchmark
suites (VLSP shared tasks, UIT-VSFC, ViQuAD).

**These are NOT the real benchmarks.** They exist only so Project 9's
harness has something of the right shape to build and test its scoring
code against before the real, licensed benchmark releases are sourced.
Every row carries a `"stub_note"` field saying so explicitly -- a
`BenchmarkReport` produced from one of these must always carry a non-empty
`stub_note` too (see `interfaces.export.BenchmarkReport.stub_note`), so a
number generated from a stand-in can never be quoted as if it were the
real shared-task score.

Regenerate with `python tests/fixtures/generate_benchmark_stubs.py`
(deterministic, hand-authored content; `viquad_stub.jsonl`'s
`answer_start` offsets are computed, not typed by hand, so a bad offset
fails the generator loudly instead of shipping silently -- see
`test_fixture_benchmark_stubs.py`).

When the real datasets are obtained and licensed, they replace these files
at the same relative path under `tests/fixtures/benchmark/` (or under a
separate, non-fixture data path if their license does not permit
redistribution in this repo) -- see Project 9's `spec.md`.
