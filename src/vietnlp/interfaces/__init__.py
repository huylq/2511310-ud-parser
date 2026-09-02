"""Frozen cross-project contracts for the student-projects curriculum.

Each module here is the hand-off boundary between two of the 9 independent
student projects described in `student-projects/README.md`. Every module
exposes: one or more frozen dataclasses (a fixture-scale mirror of the real
Postgres Gold columns in
`platform/db/migrations/0001_core_schema.sql`), a pandera schema over the
flattened row-shape of that dataclass (same one-record-at-a-time idiom as
`acquisition/fixture_schema.py::FIXTURE_SCHEMA`), and a `validate_*` function
that raises `pandera.errors.SchemaError` on a nonconforming object.

Every dataclass carries a `source: Literal["stub", "real"]` field. A stub
generator (`interfaces.stubs.*`) always sets `"stub"`; a student's real
implementation must set `"real"`. This is what lets a downstream project
build against a real-shaped object from week 1 without waiting on an
upstream student to finish, and lets the per-project gate assert a
project's *own* output is genuinely real while what it *consumes* from an
upstream project is allowed to still be a stub.

DO NOT EDIT these contracts from inside a student branch -- they are in
every project's `forbidden_paths` (see `student-projects/_gate/`). A
genuine defect gets fixed here, once, by bumping the relevant module's
`SCHEMA_VERSION` and republishing to all 9 branches -- see
`student-projects/README.md`'s "Interface change control" section.
"""

from __future__ import annotations
