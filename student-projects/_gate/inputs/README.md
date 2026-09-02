# Gate input loaders

One file per project, `<slug>.py`, each exposing a `build_inputs()`
function that `gate.py`'s step 3 (schema conformance) calls to build the
list of inputs a project's producer function is run over.

**Professor-owned, not student-owned** -- these live under `_gate/`
(forbidden to every project, same as `interfaces/**`) rather than inside
a project's own `student-projects/<slug>/` directory, so a project's own
`owned_paths` never need to include gate-wiring code. A loader typically
does one of two things:

- reads raw fixture data directly (Project 1, which starts from plain
  sentence text), or
- runs an upstream project's **stub** generator
  (`interfaces.stubs.*`) over the fixture data to build realistic,
  schema-conformant input objects (every other project) -- this is the
  same "build against the stub from day one" mechanism described in
  `student-projects/README.md`, applied to the gate itself.

A loader must never import a student's own submission module (that would
make the gate's input depend on the very code being graded); it only
imports frozen `interfaces`/`interfaces.stubs` code and reads frozen
fixture files.
