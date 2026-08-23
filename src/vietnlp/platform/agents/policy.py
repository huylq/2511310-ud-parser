"""Model routing policy: which model handles which task, and what it costs.

The whole point of this module is that no caller ever names a model. Callers name
a *task*; the policy decides the model. That keeps cost decisions in one reviewable
table instead of scattered across the pipeline.

Pricing is USD per 1M tokens and is CONFIGURATION, not truth. DeepSeek changes its
rates; verify against https://api-docs.deepseek.com/quick_start/pricing and override
via DEEPSEEK_PRICE_* env vars rather than editing estimates into code paths.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum


class Model(str, Enum):
    """DeepSeek models we are willing to spend money on."""

    CHAT = "deepseek-chat"          # V3-class: fast, cheap, no visible reasoning
    REASONER = "deepseek-reasoner"  # R1-class: slow, ~8x the output cost, thinks


@dataclass(frozen=True)
class Price:
    """USD per 1M tokens."""

    input_miss: float
    input_hit: float
    output: float


def _price(model: Model) -> Price:
    """Read pricing from env with documented defaults."""
    prefix = "DEEPSEEK_PRICE_" + ("CHAT" if model is Model.CHAT else "REASONER")
    defaults = {
        Model.CHAT: Price(0.27, 0.07, 1.10),
        Model.REASONER: Price(0.55, 0.14, 2.19),
    }[model]
    return Price(
        input_miss=float(os.getenv(f"{prefix}_IN_MISS", defaults.input_miss)),
        input_hit=float(os.getenv(f"{prefix}_IN_HIT", defaults.input_hit)),
        output=float(os.getenv(f"{prefix}_OUT", defaults.output)),
    )


@dataclass(frozen=True)
class Route:
    """The resolved plan for one task type."""

    task: str
    model: Model
    max_output_tokens: int
    temperature: float
    batch_size: int      # documents/sentences per request; 1 means no batching
    cacheable: bool      # may we reuse a prior response for identical input?
    rationale: str


# The cost table. Read this top to bottom when you want to know where money goes.
#
# Rule of thumb applied throughout: REASONER only where a wrong answer is expensive
# to detect downstream. Everything with a cheap validator (regex, schema, type
# checker, reasoner-consistency pass) runs on CHAT, because the validator catches
# what the cheap model gets wrong for free.
_ROUTES: dict[str, Route] = {
    # ---- Curation: high volume, cheap validators, always CHAT -------------------
    "quality_score": Route(
        task="quality_score",
        model=Model.CHAT,
        max_output_tokens=16,
        temperature=0.0,
        batch_size=20,
        cacheable=True,
        rationale="Returns a single integer. Batched 20x; reasoner here would be "
        "pure waste at ~100K documents.",
    ),
    "language_register": Route(
        task="language_register",
        model=Model.CHAT,
        max_output_tokens=24,
        temperature=0.0,
        batch_size=20,
        cacheable=True,
        rationale="Closed-set label (formal/informal/teencode/khong-dau). A "
        "classifier task, not a reasoning task.",
    ),
    "pii_flag": Route(
        task="pii_flag",
        model=Model.CHAT,
        max_output_tokens=128,
        temperature=0.0,
        batch_size=10,
        cacheable=True,
        rationale="Regex catches most Vietnamese PII (CCCD, phone); the model only "
        "adjudicates the residue.",
    ),
    "boilerplate_check": Route(
        task="boilerplate_check",
        model=Model.CHAT,
        max_output_tokens=64,
        temperature=0.0,
        batch_size=10,
        cacheable=True,
        rationale="Verifying trafilatura output kept the article and dropped the "
        "nav bar. Shallow judgement.",
    ),
    # ---- Linguistics: CHAT proposes, rules dispose -----------------------------
    "word_segmentation": Route(
        task="word_segmentation",
        model=Model.CHAT,
        max_output_tokens=512,
        temperature=0.0,
        batch_size=5,
        cacheable=True,
        rationale="underthesea/VnCoreNLP do the bulk. Model is consulted only on "
        "disagreement between the two engines.",
    ),
    "pos_tagging": Route(
        task="pos_tagging",
        model=Model.CHAT,
        max_output_tokens=768,
        temperature=0.0,
        batch_size=5,
        cacheable=True,
        rationale="UD tagset is closed and schema-validated on return, so a cheap "
        "model's errors are caught mechanically.",
    ),
    "ner_bootstrap": Route(
        task="ner_bootstrap",
        model=Model.CHAT,
        max_output_tokens=512,
        temperature=0.0,
        batch_size=5,
        cacheable=True,
        rationale="Span offsets are verified against the source string; "
        "hallucinated spans fail validation and never reach Gold.",
    ),
    # ---- Where reasoning actually pays for itself -------------------------------
    "parse_adjudication": Route(
        task="parse_adjudication",
        model=Model.REASONER,
        max_output_tokens=2048,
        temperature=0.0,
        batch_size=1,
        cacheable=True,
        rationale="Only invoked when two parsers disagree on a UD head/deprel. "
        "Low volume by construction, and a wrong head silently corrupts the "
        "treebank -- exactly the case worth paying for.",
    ),
    "semantic_parse": Route(
        task="semantic_parse",
        model=Model.REASONER,
        max_output_tokens=2048,
        temperature=0.0,
        batch_size=1,
        cacheable=True,
        rationale="UD -> neo-Davidsonian FOL is multi-step compositional work. "
        "CHAT produces well-formed but wrong scope; the type checker catches "
        "arity errors, not scope errors.",
    ),
    "ontology_induction": Route(
        task="ontology_induction",
        model=Model.REASONER,
        max_output_tokens=4096,
        temperature=0.0,
        batch_size=1,
        cacheable=True,
        rationale="Proposing class hierarchies and disjointness axioms. HermiT "
        "catches inconsistency but not a merely bad taxonomy.",
    ),
    "entity_disambiguation": Route(
        task="entity_disambiguation",
        model=Model.REASONER,
        max_output_tokens=1024,
        temperature=0.0,
        batch_size=1,
        cacheable=True,
        rationale="Hard OUPM cases only, after the noisy-name channel has already "
        "narrowed candidates. Reserved for genuine ambiguity.",
    ),
}

class UnknownTask(KeyError):
    """Raised for a task with no route. Never fall back to a default model."""


def route(task: str) -> Route:
    """Resolve a task name to its model plan.

    Unknown tasks raise. A silent default would be a silent bill.
    """
    try:
        return _ROUTES[task]
    except KeyError:
        known = ", ".join(sorted(_ROUTES))
        raise UnknownTask(f"no route for task {task!r}; known tasks: {known}") from None


def all_tasks() -> list[str]:
    return sorted(_ROUTES)


def estimate_usd(
    model: Model, input_tokens: int, output_tokens: int, cache_hit_tokens: int = 0
) -> float:
    """Cost of one call in USD. cache_hit_tokens is the prefix-cached slice."""
    if cache_hit_tokens > input_tokens:
        raise ValueError(
            f"cache_hit_tokens ({cache_hit_tokens}) exceeds input_tokens ({input_tokens})"
        )
    p = _price(model)
    miss = input_tokens - cache_hit_tokens
    return (
        miss * p.input_miss / 1_000_000
        + cache_hit_tokens * p.input_hit / 1_000_000
        + output_tokens * p.output / 1_000_000
    )
