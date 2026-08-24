"""Rule 2: DeepSeek output never enters Gold unvalidated.

These tests attack the validators with the failure modes that actually occur --
hallucinated tokens, invented offsets, out-of-tagset labels -- because the
validator is the only thing standing between a cheap model and the treebank.
"""

import pytest

from vietnlp.platform.agents.registry import AGENTS, ValidationFailed, get


def test_every_agent_has_a_validator_and_a_prompt_version():
    for name, agent in AGENTS.items():
        assert callable(agent.validate), f"{name} has no validator"
        assert agent.prompt_version, f"{name} has no prompt version"
        assert agent.description, f"{name} has no description"


def test_unknown_agent_raises_with_suggestions():
    with pytest.raises(KeyError, match="unknown agent"):
        get("no-such-agent")


# ---- quality scorer ----------------------------------------------------------

def test_quality_score_accepts_valid():
    assert get("quality-scorer").validate({"score": 4, "reason": "clean"}, "x")["score"] == 4.0


@pytest.mark.parametrize("bad", [{"score": 9}, {"score": -1}, {"score": "high"}, {}, []])
def test_quality_score_rejects_out_of_range_or_malformed(bad):
    with pytest.raises(ValidationFailed):
        get("quality-scorer").validate(bad, "x")


# ---- register ----------------------------------------------------------------

def test_register_rejects_invented_label():
    with pytest.raises(ValidationFailed, match="not in"):
        get("register-classifier").validate({"register": "academic"}, "x")


def test_register_accepts_non_diacritic():
    """Non-diacritic Vietnamese is a register we track, not noise to discard."""
    assert get("register-classifier").validate({"register": "non_diacritic"}, "x")["register"] == "non_diacritic"


# ---- POS tagger --------------------------------------------------------------

SENT = "Sinh viên đại học Hà Nội học rất chăm chỉ."


def test_pos_accepts_multisyllable_vietnamese_words():
    """'sinh viên' is one word spanning two whitespace-separated syllables."""
    out = get("pos-tagger").validate(
        {"tokens": [{"form": "Sinh viên", "upos": "NOUN"}, {"form": "học", "upos": "VERB"}]},
        SENT,
    )
    assert out[0]["form"] == "Sinh viên"


def test_pos_rejects_hallucinated_token():
    """The substring check is what makes the cheap model safe for this task."""
    with pytest.raises(ValidationFailed, match="hallucinated"):
        get("pos-tagger").validate(
            {"tokens": [{"form": "Sài Gòn", "upos": "PROPN"}]}, SENT
        )


def test_pos_rejects_non_ud_tag():
    with pytest.raises(ValidationFailed, match="not a UD tag"):
        get("pos-tagger").validate({"tokens": [{"form": "học", "upos": "Nc"}]}, SENT)


def test_pos_rejects_empty_token_list():
    with pytest.raises(ValidationFailed, match="non-empty"):
        get("pos-tagger").validate({"tokens": []}, SENT)


# ---- NER ---------------------------------------------------------------------
#
# The model names entities; we locate them. These tests pin that contract, which
# exists because the model returned offsets off by two on the first live sentence.

def test_ner_locates_the_entity_itself():
    out = get("ner-bootstrapper").validate(
        {"entities": [{"text": "Hà Nội", "label": "LOC"}]}, SENT
    )
    assert SENT[out[0]["start"]:out[0]["end"]] == "Hà Nội"


def test_ner_rejects_hallucinated_entity():
    """An entity absent from the source cannot be located, so it cannot pass."""
    with pytest.raises(ValidationFailed, match="hallucinated"):
        get("ner-bootstrapper").validate(
            {"entities": [{"text": "Sài Gòn", "label": "LOC"}]}, SENT
        )


def test_ner_rejects_label_outside_the_scheme():
    with pytest.raises(ValidationFailed, match="not in"):
        get("ner-bootstrapper").validate(
            {"entities": [{"text": "Hà Nội", "label": "CITY"}]}, SENT
        )


def test_ner_maps_repeats_to_successive_occurrences():
    """Two mentions of one name must not collapse onto the same span."""
    text = "Hà Nội và Hà Nội."
    out = get("ner-bootstrapper").validate(
        {"entities": [{"text": "Hà Nội", "label": "LOC"}, {"text": "Hà Nội", "label": "LOC"}]},
        text,
    )
    assert out[0]["start"] != out[1]["start"]
    assert [text[e["start"]:e["end"]] for e in out] == ["Hà Nội", "Hà Nội"]


def test_ner_rejects_more_repeats_than_the_source_contains():
    with pytest.raises(ValidationFailed, match="hallucinated"):
        get("ner-bootstrapper").validate(
            {"entities": [{"text": "Hà Nội", "label": "LOC"}] * 2}, SENT
        )


def test_ner_tolerates_unicode_normalisation_differences():
    """The same word in NFD from the model must still match NFC source text."""
    import unicodedata
    nfd = unicodedata.normalize("NFD", "Hà Nội")
    out = get("ner-bootstrapper").validate({"entities": [{"text": nfd, "label": "LOC"}]}, SENT)
    assert out[0]["text"] == "Hà Nội"


# ---- semantic parser ---------------------------------------------------------

GOOD_FORM = "(exists (e x) (and (buy e) (agent e nam_1) (theme e x) (book x) (past e)))"


def test_logical_form_accepts_balanced_sexp():
    out = get("semantic-parser").validate({"form": GOOD_FORM, "predicates": ["buy", "book"]}, "x")
    assert out["predicates"] == ["book", "buy"]


@pytest.mark.parametrize("bad", ["(and (buy e)", "(and (buy e)))", ")(", ""])
def test_logical_form_rejects_unbalanced_sexp(bad):
    with pytest.raises(ValidationFailed):
        get("semantic-parser").validate({"form": bad}, "x")
