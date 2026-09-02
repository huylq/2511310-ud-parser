"""Contract for `treebank/gold_treebank_seed.conllu` +
`system_b_perturbed.conllu` -- see `tests/fixtures/treebank/PROVISIONAL.md`
for what these are and are not. Structural checks only; linguistic
correctness is the professor's sign-off judgment call.
"""
from pathlib import Path

import pytest

from vietnlp.interfaces._common import UD_DEPREL
from vietnlp.interfaces.ud import DependencyParse, UDToken, is_single_rooted_tree, validate_dependency_parse
from vietnlp.platform.agents.registry import UPOS_TAGSET

TREEBANK_DIR = Path(__file__).parent / "fixtures" / "treebank"


def _parse_conllu(path: Path) -> dict[str, tuple[list[UDToken], str, str | None]]:
    """Returns {sent_id: (tokens, text, note)}."""
    sentences: dict[str, tuple[list[UDToken], str, str | None]] = {}
    sent_id = None
    text = None
    note = None
    tokens: list[UDToken] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# sent_id ="):
            sent_id = line.split("=", 1)[1].strip()
        elif line.startswith("# text ="):
            text = line.split("=", 1)[1].strip()
        elif line.startswith("# note ="):
            note = line.split("=", 1)[1].strip()
        elif line.strip() == "":
            if sent_id is not None:
                sentences[sent_id] = (tokens, text, note)
            sent_id, text, note, tokens = None, None, None, []
        else:
            idx, form, _lemma, upos, _xpos, _feats, head, deprel, _deps, _misc = line.split("\t")
            tokens.append(UDToken(idx=int(idx) - 1, form=form, upos=upos, head=int(head), deprel=deprel))
    return sentences


def _gold() -> dict[str, tuple[list[UDToken], str, str | None]]:
    return _parse_conllu(TREEBANK_DIR / "gold_treebank_seed.conllu")


def _system_b() -> dict[str, tuple[list[UDToken], str, str | None]]:
    return _parse_conllu(TREEBANK_DIR / "system_b_perturbed.conllu")


def test_files_exist():
    assert (TREEBANK_DIR / "gold_treebank_seed.conllu").exists()
    assert (TREEBANK_DIR / "system_b_perturbed.conllu").exists()


def test_between_20_and_30_sentences():
    assert 20 <= len(_gold()) <= 30


def test_both_files_have_the_same_sentence_ids_in_order():
    assert list(_gold()) == list(_system_b())


def test_every_gold_sentence_is_a_valid_single_rooted_tree():
    for sent_id, (tokens, _text, _note) in _gold().items():
        parse = DependencyParse(sent_id=sent_id, tokens=tuple(tokens), source="real")
        validate_dependency_parse(parse)
        assert is_single_rooted_tree(parse), f"{sent_id}: not a single-rooted tree"


def test_every_system_b_sentence_is_also_a_valid_single_rooted_tree():
    """A perturbation must still be a well-formed tree -- it models a
    plausible disagreement, not a broken parse."""
    for sent_id, (tokens, _text, _note) in _system_b().items():
        parse = DependencyParse(sent_id=sent_id, tokens=tuple(tokens), source="real")
        validate_dependency_parse(parse)
        assert is_single_rooted_tree(parse), f"{sent_id}: not a single-rooted tree"


def test_every_upos_and_deprel_is_in_the_frozen_tagsets():
    for sentences in (_gold(), _system_b()):
        for sent_id, (tokens, _text, _note) in sentences.items():
            for t in tokens:
                assert t.upos in UPOS_TAGSET, f"{sent_id}: {t.form} upos {t.upos!r}"
                assert t.deprel in UD_DEPREL, f"{sent_id}: {t.form} deprel {t.deprel!r}"


def test_exactly_10_sentences_are_perturbed_and_10_are_identical_to_gold():
    gold, system_b = _gold(), _system_b()
    perturbed = [sid for sid, (_t, _x, note) in system_b.items() if note]
    identical = [sid for sid in gold if gold[sid][0] == system_b[sid][0]]
    assert len(perturbed) == 10
    assert len(identical) == 10
    assert set(perturbed).isdisjoint(identical)


def test_every_perturbed_sentence_differs_from_gold_in_exactly_one_token():
    gold, system_b = _gold(), _system_b()
    for sent_id, (tokens, _text, note) in system_b.items():
        if not note:
            continue
        gold_tokens = gold[sent_id][0]
        diffs = [
            i for i, (g, b) in enumerate(zip(gold_tokens, tokens))
            if (g.upos, g.head, g.deprel) != (b.upos, b.head, b.deprel)
        ]
        assert len(diffs) == 1, f"{sent_id}: expected exactly 1 differing token, found {len(diffs)}"


def test_forms_are_never_perturbed_only_annotation_fields():
    """Tokenization must be identical between gold and system B -- only
    upos/head/deprel may differ, per the plan's design (same tokenization
    and order)."""
    gold, system_b = _gold(), _system_b()
    for sent_id in gold:
        gold_forms = [t.form for t in gold[sent_id][0]]
        b_forms = [t.form for t in system_b[sent_id][0]]
        assert gold_forms == b_forms, sent_id


def test_multi_syllable_compounds_use_underscore_not_space():
    for tokens, _text, _note in _gold().values():
        for t in tokens:
            assert " " not in t.form, f"FORM {t.form!r} contains a literal space"
