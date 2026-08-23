"""The cost table is the product here, so it gets tested like one."""

import pytest

from vietnlp.platform.agents.policy import (
    Model, UnknownTask, all_tasks, estimate_usd, route,
)


def test_unknown_task_raises_rather_than_defaulting():
    """A silent default model would be a silent bill."""
    with pytest.raises(UnknownTask, match="no route for task"):
        route("some_task_nobody_defined")


def test_bulk_curation_tasks_never_use_the_reasoner():
    """These run over the whole corpus; the reasoner would dominate the budget."""
    for task in ("quality_score", "language_register", "pii_flag", "boilerplate_check"):
        assert route(task).model is Model.CHAT, f"{task} must stay on the cheap model"


def test_reasoner_reserved_for_low_volume_hard_tasks():
    for task in ("semantic_parse", "ontology_induction", "parse_adjudication"):
        r = route(task)
        assert r.model is Model.REASONER
        assert r.batch_size == 1, "reasoner tasks are per-item by design"


def test_every_route_is_cacheable_and_deterministic():
    """Temperature > 0 would make cached responses misleading."""
    for task in all_tasks():
        r = route(task)
        assert r.cacheable
        assert r.temperature == 0.0
        assert r.max_output_tokens > 0
        assert r.rationale, f"{task} has no documented rationale"


def test_reasoner_costs_more_than_chat_for_same_work():
    """Guards against a pricing override that silently inverts the incentive."""
    chat = estimate_usd(Model.CHAT, 1000, 500)
    reasoner = estimate_usd(Model.REASONER, 1000, 500)
    assert reasoner > chat


def test_cache_hits_are_cheaper_than_misses():
    miss = estimate_usd(Model.CHAT, 1000, 100, cache_hit_tokens=0)
    hit = estimate_usd(Model.CHAT, 1000, 100, cache_hit_tokens=1000)
    assert hit < miss


def test_cache_hit_tokens_cannot_exceed_input():
    with pytest.raises(ValueError, match="exceeds input_tokens"):
        estimate_usd(Model.CHAT, 100, 10, cache_hit_tokens=200)
