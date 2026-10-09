# Project 2 — Vietnamese UD Dependency Parsing

This repository contains the coursework for student 2511310, Lê Quốc Huy.
Read `student-projects/02-ud-parsing/spec.md`, `plan.md`, `project.md`, and
`DESIGN.md` before changing the parser.

## Scope

Implement `parse(sentence: SegmentedSentence) -> DependencyParse` at
`src/vietnlp/linguistics/ud_parser.py`. Parser tests belong at
`tests/test_linguistics_ud_parser*.py`; design and research documents belong
under `student-projects/02-ud-parsing/`.

Project 1 supplies the input contract and its frozen segmentation stub.
The two documents under `student-projects/01-word-seg-pos/` are retained as
references named by Project 2's spec and plan. Implementing segmentation
or POS tagging is outside this project's scope.

## Rules

1. Preserve Vietnamese diacritics and the input token sequence. Whitespace
   tokens from the stub are syllables, not reliable word segmentation.
2. AI-drafted treebank annotations remain provisional until reviewed and
   approved by the professor. Do not present them as validated gold data.
3. Follow UD v2 and UD_Vietnamese-VTB; cite the attachment conventions.
4. Preserve the supplied interface schemas, validators, tagsets, fixture
   contents, and gate logic. Report defects instead of changing contracts.
5. Use offline tests. No API calls, databases, Docker, or other students'
   real implementations are required to develop the parser.
6. Start TDD when parser implementation begins. Validate both per-token
   schema and the single-rooted, cycle-free tree invariant. The parser's
   own output must carry `source="real"`.

## Commands

Install: `python -m pip install -e ".[dev]"`.
Inherited checks: `python -m pytest tests -q`.
Project gate: `python student-projects/_gate/gate.py 02-ud-parsing --base project-02-base`.

`project-02-base` marks this repository's packaging baseline for checking
subsequent parser changes. The original course tag `curriculum-base`
remains the reference for the original curriculum repository. Gate checks
requiring the real parser and its own tests will not pass during research.
