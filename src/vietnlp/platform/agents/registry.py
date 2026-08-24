"""Sub-agent definitions: role, prompt, model route, and validator.

CLAUDE.md rule 2: DeepSeek output never enters Gold unvalidated. That rule is
enforced structurally here -- an Agent cannot be constructed without a validator,
and `Agent.run` returns only validated output. There is no code path that returns
a raw model response to a caller.

Adding an agent means adding its validator. If you cannot write a validator for a
task, that task is not ready to be automated.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Callable

from .client import AgentClient, Result
from .policy import Route, route


class ValidationFailed(ValueError):
    """Model output rejected. The caller must dead-letter it, never coerce it."""


@dataclass(frozen=True)
class Agent:
    """One sub-agent: a task, a prompt, and the validator that gates its output."""

    name: str
    task: str                       # resolves to a model via policy.route
    prompt_version: str             # bump on ANY prompt edit; invalidates cache
    system_prompt: str
    validate: Callable[[Any, str], Any]
    json_mode: bool = True
    description: str = ""

    @property
    def route(self) -> Route:
        return route(self.task)

    def run(self, client: AgentClient, source_text: str, **fmt) -> tuple[Any, Result]:
        """Execute and validate. Raises ValidationFailed rather than returning junk."""
        user_content = source_text.format(**fmt) if fmt else source_text
        result = client.run(
            self.task,
            self.system_prompt,
            user_content,
            prompt_version=self.prompt_version,
            json_mode=self.json_mode,
        )
        try:
            parsed = result.json() if self.json_mode else result.content
        except ValueError as exc:
            raise ValidationFailed(f"{self.name}: response was not valid JSON: {exc}") from exc
        return self.validate(parsed, source_text), result


# --------------------------------------------------------------------------------
# Validators. Each is pure and cheap -- that is what makes the cheap model safe.
# --------------------------------------------------------------------------------

_UPOS = frozenset(
    "ADJ ADP ADV AUX CCONJ DET INTJ NOUN NUM PART PRON PROPN PUNCT SCONJ SYM VERB X".split()
)
_REGISTERS = frozenset({"formal", "informal", "teencode", "non_diacritic", "mixed"})
_NER_LABELS = frozenset({"PER", "LOC", "ORG", "MISC"})


def _validate_quality(parsed: Any, _source: str) -> dict:
    if not isinstance(parsed, dict) or "score" not in parsed:
        raise ValidationFailed(f"expected object with 'score', got {type(parsed).__name__}")
    score = parsed["score"]
    if not isinstance(score, (int, float)) or not 0 <= score <= 5:
        raise ValidationFailed(f"score {score!r} outside 0-5")
    return {"score": float(score), "reason": str(parsed.get("reason", ""))[:500]}


def _validate_register(parsed: Any, _source: str) -> dict:
    label = parsed.get("register") if isinstance(parsed, dict) else None
    if label not in _REGISTERS:
        raise ValidationFailed(f"register {label!r} not in {sorted(_REGISTERS)}")
    return {"register": label}


def _validate_pos(parsed: Any, source: str) -> list[dict]:
    """Every tag must be in the UD tagset and every form must occur in the source.

    The form check is what makes a cheap model safe here: a hallucinated token
    cannot survive a substring test against the sentence it claims to come from.
    """
    tokens = parsed.get("tokens") if isinstance(parsed, dict) else parsed
    if not isinstance(tokens, list) or not tokens:
        raise ValidationFailed("expected non-empty 'tokens' list")
    normalized_source = unicodedata.normalize("NFC", source)
    out = []
    for i, tok in enumerate(tokens):
        if not isinstance(tok, dict):
            raise ValidationFailed(f"token {i} is not an object")
        form, upos = tok.get("form"), tok.get("upos")
        if not isinstance(form, str) or not form:
            raise ValidationFailed(f"token {i} has no form")
        if upos not in _UPOS:
            raise ValidationFailed(f"token {i} upos {upos!r} not a UD tag")
        # A Vietnamese word may be multi-syllable ("sinh vien"); check each syllable
        # is present rather than the joined form, which may differ in spacing.
        for syllable in unicodedata.normalize("NFC", form).split():
            if syllable not in normalized_source:
                raise ValidationFailed(
                    f"token {i} syllable {syllable!r} absent from source -- hallucinated"
                )
        out.append({"form": form, "upos": upos})
    return out


def _validate_ner(parsed: Any, source: str) -> list[dict]:
    """Locate each entity in the source ourselves; the model only names them.

    We asked the model for character offsets first. It returned spans off by two on
    the very first live sentence -- LLMs cannot count characters, and Vietnamese
    diacritics make it worse. Asking for offsets is asking for a task the model
    cannot do, so we compute them here instead.

    The anti-hallucination guarantee is unchanged and is in fact stronger: an entity
    whose text does not occur in the source cannot be located, so it is rejected.
    """
    spans = parsed.get("entities") if isinstance(parsed, dict) else parsed
    if not isinstance(spans, list):
        raise ValidationFailed("expected 'entities' list")

    normalized = unicodedata.normalize("NFC", source)
    out: list[dict] = []
    # Track a cursor per surface form so a repeated entity maps to successive
    # occurrences rather than all collapsing onto the first one.
    cursors: dict[str, int] = {}

    for i, span in enumerate(spans):
        if not isinstance(span, dict):
            raise ValidationFailed(f"entity {i} is not an object")
        text, label = span.get("text"), span.get("label")
        if not isinstance(text, str) or not text.strip():
            raise ValidationFailed(f"entity {i} has no text")
        if label not in _NER_LABELS:
            raise ValidationFailed(f"entity {i} label {label!r} not in {sorted(_NER_LABELS)}")

        needle = unicodedata.normalize("NFC", text)
        start = normalized.find(needle, cursors.get(needle, 0))
        if start < 0:
            # Either a hallucinated entity, or a real one the model has already
            # reported more times than it occurs. Both are rejections.
            raise ValidationFailed(
                f"entity {i} text {text!r} does not occur in the source -- hallucinated"
            )
        end = start + len(needle)
        cursors[needle] = end
        out.append({"start": start, "end": end, "label": label, "text": needle})

    return out


_SEXP_TOKEN = re.compile(r"\(|\)|[^\s()]+")


def _validate_logical_form(parsed: Any, _source: str) -> dict:
    """Balanced-parens check on the S-expression.

    This is a well-formedness gate, not a correctness gate. Semantic correctness is
    the type checker's job in `semantics/`; this only guarantees the form parses.
    """
    form = parsed.get("form") if isinstance(parsed, dict) else None
    if not isinstance(form, str) or not form.strip():
        raise ValidationFailed("expected non-empty 'form' string")
    depth = 0
    for token in _SEXP_TOKEN.findall(form):
        if token == "(":
            depth += 1
        elif token == ")":
            depth -= 1
            if depth < 0:
                raise ValidationFailed("unbalanced S-expression: closed before open")
    if depth != 0:
        raise ValidationFailed(f"unbalanced S-expression: {depth} unclosed paren(s)")
    return {"form": form.strip(), "predicates": sorted(set(parsed.get("predicates", [])))}


# --------------------------------------------------------------------------------
# The registry
# --------------------------------------------------------------------------------

_VI = (
    "You process Vietnamese text. Vietnamese is syllable-segmented, not "
    "word-segmented: whitespace separates syllables, and a word may span several "
    "(e.g. 'sinh vien' is one word, two syllables). Preserve diacritics exactly as "
    "given. Reply with JSON only, no prose, no markdown fence."
)

AGENTS: dict[str, Agent] = {
    a.name: a
    for a in [
        Agent(
            name="quality-scorer",
            task="quality_score",
            prompt_version="v1",
            description="Rates document fitness for the corpus. Bulk stage, cheap model.",
            system_prompt=(
                f"{_VI}\n\nRate the document's fitness for a Vietnamese language corpus "
                "on 0-5: 5 = clean natural prose; 3 = usable with noise; 0 = machine "
                "translation, spam, or not Vietnamese. "
                'Reply {"score": <number>, "reason": "<short>"}.'
            ),
            validate=_validate_quality,
        ),
        Agent(
            name="register-classifier",
            task="language_register",
            prompt_version="v1",
            description="Labels register. Feeds the formal/informal balance metric.",
            system_prompt=(
                f"{_VI}\n\nClassify the register as exactly one of: formal, informal, "
                "teencode, non_diacritic (Vietnamese written without diacritics), mixed. "
                'Reply {"register": "<label>"}.'
            ),
            validate=_validate_register,
        ),
        Agent(
            name="pos-tagger",
            task="pos_tagging",
            prompt_version="v1",
            description="Proposes UD POS tags. Consulted only where parsers disagree.",
            system_prompt=(
                f"{_VI}\n\nSegment into words and tag each with a Universal "
                "Dependencies v2 UPOS tag. Use only forms that appear in the input. "
                'Reply {"tokens": [{"form": "...", "upos": "..."}]}.'
            ),
            validate=_validate_pos,
        ),
        Agent(
            name="ner-bootstrapper",
            task="ner_bootstrap",
            prompt_version="v2",
            description="Proposes named entities; offsets are computed locally, not asked for.",
            system_prompt=(
                f"{_VI}\n\nFind named entities. Copy each entity's text EXACTLY as it "
                "appears in the input, including diacritics. Do not report character "
                "positions. Labels: PER (person), LOC (place), ORG (organisation), "
                "MISC. List an entity once per occurrence. "
                'Reply {"entities": [{"text": "...", "label": "..."}]}.'
            ),
            validate=_validate_ner,
        ),
        Agent(
            name="semantic-parser",
            task="semantic_parse",
            prompt_version="v1",
            description="UD -> neo-Davidsonian FOL. Reasoning model; low volume.",
            system_prompt=(
                f"{_VI}\n\nTranslate the sentence into a neo-Davidsonian first-order "
                "logical form as an S-expression, with an event variable and thematic "
                "roles (agent, theme, location, time). Example for 'Nam mua mot cuon "
                "sach o Ha Noi': (exists (e x) (and (buy e) (agent e nam_1) (theme e x) "
                "(book x) (location e hanoi_1) (past e))). "
                'Reply {"form": "<s-expression>", "predicates": ["..."]}.'
            ),
            validate=_validate_logical_form,
        ),
    ]
}


def get(name: str) -> Agent:
    try:
        return AGENTS[name]
    except KeyError:
        raise KeyError(f"unknown agent {name!r}; known: {', '.join(sorted(AGENTS))}") from None
