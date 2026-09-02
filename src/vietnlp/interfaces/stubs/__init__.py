"""Deterministic, naive generators that unblock a downstream student
project from waiting on an upstream project's real implementation.

Every function here is cheap, offline, and deliberately linguistically
naive -- good enough to produce a schema-conformant object of the right
shape, never good enough to be worth copying into a real submission (and
every object it returns carries `source="stub"`, so the gate's provenance
check catches anyone who tries). See `interfaces/__init__.py` for the
`source` field's full rationale and `student-projects/README.md` for how
these fit into the 15-week build order.
"""

from __future__ import annotations
