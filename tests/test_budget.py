"""Rule 5: budget caps hard-stop. These tests are the enforcement.

Each test sets the caps it needs so that exactly one rule can trip. A shared
fixture makes these tests interfere: the daily cap fires during a test about flow
scoping and the assertion passes for the wrong reason.
"""

import pytest

from vietnlp.platform.agents.budget import BudgetExceeded, BudgetLedger
from vietnlp.platform.agents.policy import Model

# Reference costs, from the default price table:
#   CHAT     5,000,000 in  +         0 out = $1.35
#   REASONER   200,000 in  +   100,000 out = $0.329
CHAT_BIG_SPEND = 1.35
REASONER_SPEND = 0.329


@pytest.fixture
def make_ledger(tmp_path):
    counter = iter(range(1000))

    def _make(*, flow=1000.0, daily=1000.0, total=1000.0):
        return BudgetLedger(
            tmp_path / f"spend-{next(counter)}.db",
            flow_cap_usd=flow, daily_cap_usd=daily, total_cap_usd=total,
        )

    return _make


def _burn_chat(ledger, flow_run_id):
    ledger.record(
        flow_run_id=flow_run_id, task="quality_score", model=Model.CHAT,
        input_tokens=5_000_000, cached_tokens=0, output_tokens=0,
    )


def test_affordable_call_passes(make_ledger):
    ledger = make_ledger(flow=1.0)
    assert ledger.check_affordable("flow-1", Model.CHAT, 100, 10) > 0


def test_flow_cap_aborts_rather_than_warning(make_ledger):
    ledger = make_ledger(flow=0.01)
    _burn_chat(ledger, "flow-1")
    with pytest.raises(BudgetExceeded, match="flow budget would be exceeded"):
        ledger.check_affordable("flow-1", Model.CHAT, 1000, 100)


def test_caps_are_scoped_per_flow(make_ledger):
    """One flow exhausting its allowance must not block an unrelated flow.

    Daily and total are set far above the burn so that only the flow cap can trip.
    """
    ledger = make_ledger(flow=0.01, daily=100.0, total=100.0)
    _burn_chat(ledger, "flow-1")

    with pytest.raises(BudgetExceeded, match="flow budget"):
        ledger.check_affordable("flow-1", Model.CHAT, 1000, 100)
    assert ledger.check_affordable("flow-2", Model.CHAT, 100, 10) > 0


def test_daily_cap_spans_flows(make_ledger):
    """Many small flows must not sum past the daily cap unnoticed.

    The flow cap is set high so it cannot fire; only the aggregate can.
    Four reasoner calls total ~$1.32, over the $1.00 daily cap.
    """
    ledger = make_ledger(flow=100.0, daily=1.0, total=100.0)
    for i in range(4):
        ledger.record(
            flow_run_id=f"flow-{i}", task="semantic_parse", model=Model.REASONER,
            input_tokens=200_000, cached_tokens=0, output_tokens=100_000,
        )
    assert ledger.spent("flow-0").day_usd > 1.0

    with pytest.raises(BudgetExceeded, match="daily budget"):
        ledger.check_affordable("flow-fresh", Model.REASONER, 1000, 1000)


def test_total_cap_is_the_last_line_of_defence(make_ledger):
    ledger = make_ledger(flow=100.0, daily=100.0, total=1.0)
    _burn_chat(ledger, "flow-1")
    with pytest.raises(BudgetExceeded, match="total budget"):
        ledger.check_affordable("flow-2", Model.CHAT, 1000, 100)


def test_spend_survives_reopening_the_ledger(tmp_path):
    """A budget that resets on container restart is not a budget."""
    db = tmp_path / "spend.db"
    first = BudgetLedger(db, flow_cap_usd=100.0, daily_cap_usd=100.0, total_cap_usd=100.0)
    first.record(
        flow_run_id="f", task="quality_score", model=Model.CHAT,
        input_tokens=1_000_000, cached_tokens=0, output_tokens=500_000,
    )
    recorded = first.spent("f").total_usd
    assert recorded > 0

    reopened = BudgetLedger(db, flow_cap_usd=100.0, daily_cap_usd=100.0, total_cap_usd=100.0)
    assert reopened.spent("f").total_usd == pytest.approx(recorded)
    assert reopened.spent("f").calls == 1


def test_estimate_is_checked_before_the_call_not_after(make_ledger):
    """A single call larger than the whole cap must be refused up front."""
    ledger = make_ledger(flow=0.001)
    with pytest.raises(BudgetExceeded):
        ledger.check_affordable("flow-1", Model.REASONER, 1_000_000, 100_000)
    assert ledger.spent("flow-1").calls == 0, "refused call must not be recorded as spend"


def test_nonpositive_cap_rejected(tmp_path):
    with pytest.raises(ValueError, match="must be positive"):
        BudgetLedger(tmp_path / "s.db", flow_cap_usd=0.0)
