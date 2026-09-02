"""Generates `treebank/gold_treebank_seed.conllu` and
`treebank/system_b_perturbed.conllu` -- Project 4's fixture.

PROVISIONAL: this is an AI-drafted first pass. Per CLAUDE.md rule 2 (model
output never enters Gold unvalidated) and the plan's review process, this
fixture is NOT frozen until the professor reviews and signs off -- see
`tests/fixtures/treebank/PROVISIONAL.md`.

20 sentences (10 formal + 10 informal), drawn verbatim from the single-
sentence pool in `tests/fixtures/generate_fixture_corpus.py` (FORMAL/
INFORMAL lists), hand-annotated with UPOS + UD v2 dependencies. Every
UPOS/deprel used is checked against the frozen sets in
`interfaces._common` / `platform.agents.registry` before writing -- an
unrecognized tag fails the generator loudly, matching this repo's own
"fail loud, never silently ship a bad fixture" convention (see
`generate_benchmark_stubs.py`'s `answer_start` resolution).

Multi-syllable words are written with underscore-joined FORMs (e.g.
"Giáo_dục"), the standard Vietnamese-treebank convention (VLSP/VTB/
PhoNLP), rather than embedding a literal space in a single CoNLL-U FORM
field.

`system_b_perturbed.conllu` is a SECOND, deliberately-perturbed annotation
of the same 20 sentences (same tokenization and order): 10 sentences carry
exactly one plausible, realistic annotator/parser disagreement each
(coordination scope, PP-attachment, compound-attachment, classifier-vs-
determiner confusion, topicalized-object deprel, modal-adverb scope --
never random noise); the other 10 are identical to gold, since real
systems agree on the easy majority. Every perturbed sentence documents
what differs and why it is plausible in a `# note = ...` comment.

Each sentence's tree is validated (single root, no cycles, every HEAD a
real in-sentence token) before writing, mirroring
`interfaces.ud.is_single_rooted_tree`.

Run: python tests/fixtures/generate_gold_treebank_seed.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from vietnlp.interfaces._common import UD_DEPREL  # noqa: E402
from vietnlp.platform.agents.registry import UPOS_TAGSET  # noqa: E402

OUT_DIR = Path(__file__).parent / "treebank"

# Token = (form, upos, head, deprel) -- head is 1-based; 0 means root.
Token = tuple[str, str, int, str]
Sentence = tuple[str, str, list[Token]]  # (sent_id, original text, tokens)

# ---------------------------------------------------------------------------
# Gold annotations. Source sentences are copied verbatim from the FORMAL /
# INFORMAL pools in generate_fixture_corpus.py.
# ---------------------------------------------------------------------------

_GOLD: list[Sentence] = [
    ("gold-f01", "Bộ Giáo dục và Đào tạo công bố lịch thi tốt nghiệp trung học phổ thông năm nay.", [
        ("Bộ", "PROPN", 5, "nsubj"),
        ("Giáo_dục", "PROPN", 1, "flat"),
        ("và", "CCONJ", 4, "cc"),
        ("Đào_tạo", "PROPN", 2, "conj"),
        ("công_bố", "VERB", 0, "root"),
        ("lịch", "NOUN", 5, "obj"),
        ("thi", "NOUN", 6, "compound"),
        ("tốt_nghiệp", "NOUN", 7, "compound"),
        ("trung_học", "NOUN", 8, "nmod"),
        ("phổ_thông", "ADJ", 9, "amod"),
        ("năm", "NOUN", 5, "obl"),
        ("nay", "DET", 11, "det"),
        (".", "PUNCT", 5, "punct"),
    ]),
    ("gold-f02", "Ngân hàng Nhà nước giữ nguyên lãi suất điều hành trong quý này.", [
        ("Ngân_hàng", "PROPN", 3, "nsubj"),
        ("Nhà_nước", "PROPN", 1, "flat"),
        ("giữ_nguyên", "VERB", 0, "root"),
        ("lãi_suất", "NOUN", 3, "obj"),
        ("điều_hành", "NOUN", 4, "compound"),
        ("trong", "ADP", 7, "case"),
        ("quý", "NOUN", 3, "obl"),
        ("này", "DET", 7, "det"),
        (".", "PUNCT", 3, "punct"),
    ]),
    ("gold-f03", "Đội tuyển bóng đá quốc gia giành chiến thắng trong trận đấu giao hữu tối qua.", [
        ("Đội_tuyển", "NOUN", 4, "nsubj"),
        ("bóng_đá", "NOUN", 1, "compound"),
        ("quốc_gia", "NOUN", 1, "compound"),
        ("giành", "VERB", 0, "root"),
        ("chiến_thắng", "NOUN", 4, "obj"),
        ("trong", "ADP", 7, "case"),
        ("trận_đấu", "NOUN", 4, "obl"),
        ("giao_hữu", "NOUN", 7, "compound"),
        ("tối", "NOUN", 7, "nmod"),
        ("qua", "ADJ", 9, "amod"),
        (".", "PUNCT", 4, "punct"),
    ]),
    ("gold-f04", "Thành phố Hà Nội triển khai thêm tuyến xe buýt điện phục vụ người dân.", [
        ("Thành_phố", "NOUN", 3, "nsubj"),
        ("Hà_Nội", "PROPN", 1, "flat"),
        ("triển_khai", "VERB", 0, "root"),
        ("thêm", "ADV", 3, "advmod"),
        ("tuyến", "NOUN", 3, "obj"),
        ("xe_buýt", "NOUN", 5, "compound"),
        ("điện", "ADJ", 6, "amod"),
        ("phục_vụ", "VERB", 5, "acl"),
        ("người_dân", "NOUN", 8, "obj"),
        (".", "PUNCT", 3, "punct"),
    ]),
    ("gold-f05", "Các nhà khoa học công bố nghiên cứu mới về biến đổi khí hậu tại đồng bằng sông Cửu Long.", [
        ("Các", "DET", 2, "det"),
        ("nhà_khoa_học", "NOUN", 3, "nsubj"),
        ("công_bố", "VERB", 0, "root"),
        ("nghiên_cứu", "NOUN", 3, "obj"),
        ("mới", "ADJ", 4, "amod"),
        ("về", "ADP", 7, "case"),
        ("biến_đổi", "NOUN", 4, "nmod"),
        ("khí_hậu", "NOUN", 7, "compound"),
        ("tại", "ADP", 10, "case"),
        ("đồng_bằng", "NOUN", 3, "obl"),
        ("sông", "NOUN", 10, "compound"),
        ("Cửu_Long", "PROPN", 11, "flat"),
        (".", "PUNCT", 3, "punct"),
    ]),
    ("gold-f06", "Chính phủ ban hành nghị định hướng dẫn thi hành luật đất đai sửa đổi.", [
        ("Chính_phủ", "NOUN", 2, "nsubj"),
        ("ban_hành", "VERB", 0, "root"),
        ("nghị_định", "NOUN", 2, "obj"),
        ("hướng_dẫn", "VERB", 3, "acl"),
        ("thi_hành", "NOUN", 4, "obj"),
        ("luật", "NOUN", 5, "nmod"),
        ("đất_đai", "NOUN", 6, "compound"),
        ("sửa_đổi", "VERB", 6, "acl"),
        (".", "PUNCT", 2, "punct"),
    ]),
    ("gold-f07", "Tập đoàn công nghệ trong nước ra mắt sản phẩm phần mềm dịch thuật tiếng Việt.", [
        ("Tập_đoàn", "NOUN", 5, "nsubj"),
        ("công_nghệ", "NOUN", 1, "compound"),
        ("trong", "ADP", 4, "case"),
        ("nước", "NOUN", 1, "nmod"),
        ("ra_mắt", "VERB", 0, "root"),
        ("sản_phẩm", "NOUN", 5, "obj"),
        ("phần_mềm", "NOUN", 6, "compound"),
        ("dịch_thuật", "NOUN", 7, "compound"),
        ("tiếng", "NOUN", 8, "nmod"),
        ("Việt", "PROPN", 9, "flat"),
        (".", "PUNCT", 5, "punct"),
    ]),
    ("gold-f08", "Bệnh viện trung ương tổ chức chương trình khám sức khỏe miễn phí cho người cao tuổi.", [
        ("Bệnh_viện", "NOUN", 3, "nsubj"),
        ("trung_ương", "ADJ", 1, "amod"),
        ("tổ_chức", "VERB", 0, "root"),
        ("chương_trình", "NOUN", 3, "obj"),
        ("khám", "VERB", 4, "acl"),
        ("sức_khỏe", "NOUN", 5, "obj"),
        ("miễn_phí", "ADJ", 4, "amod"),
        ("cho", "ADP", 9, "case"),
        ("người", "NOUN", 3, "obl"),
        ("cao_tuổi", "ADJ", 9, "amod"),
        (".", "PUNCT", 3, "punct"),
    ]),
    ("gold-f09", "Trường đại học quốc gia công bố kết quả tuyển sinh đợt hai.", [
        ("Trường", "NOUN", 4, "nsubj"),
        ("đại_học", "NOUN", 1, "compound"),
        ("quốc_gia", "NOUN", 1, "compound"),
        ("công_bố", "VERB", 0, "root"),
        ("kết_quả", "NOUN", 4, "obj"),
        ("tuyển_sinh", "NOUN", 5, "compound"),
        ("đợt", "NOUN", 5, "nmod"),
        ("hai", "NUM", 7, "nummod"),
        (".", "PUNCT", 4, "punct"),
    ]),
    ("gold-f10", "Sở Giao thông Vận tải thông báo kế hoạch sửa chữa cầu đường trong tháng tới.", [
        ("Sở", "PROPN", 4, "nsubj"),
        ("Giao_thông", "PROPN", 1, "flat"),
        ("Vận_tải", "PROPN", 1, "flat"),
        ("thông_báo", "VERB", 0, "root"),
        ("kế_hoạch", "NOUN", 4, "obj"),
        ("sửa_chữa", "VERB", 5, "acl"),
        ("cầu_đường", "NOUN", 6, "obj"),
        ("trong", "ADP", 9, "case"),
        ("tháng", "NOUN", 4, "obl"),
        ("tới", "ADJ", 9, "amod"),
        (".", "PUNCT", 4, "punct"),
    ]),
    ("gold-i01", "Hôm nay trời đẹp quá, đi cà phê không?", [
        ("Hôm_nay", "NOUN", 3, "obl"),
        ("trời", "NOUN", 3, "nsubj"),
        ("đẹp", "ADJ", 0, "root"),
        ("quá", "ADV", 3, "advmod"),
        (",", "PUNCT", 6, "punct"),
        ("đi", "VERB", 3, "parataxis"),
        ("cà_phê", "NOUN", 6, "obj"),
        ("không", "PART", 6, "discourse"),
        ("?", "PUNCT", 3, "punct"),
    ]),
    ("gold-i02", "Tao vừa ăn phở xong, ngon dã man luôn.", [
        ("Tao", "PRON", 3, "nsubj"),
        ("vừa", "ADV", 3, "advmod"),
        ("ăn", "VERB", 0, "root"),
        ("phở", "NOUN", 3, "obj"),
        ("xong", "ADV", 3, "advmod"),
        (",", "PUNCT", 7, "punct"),
        ("ngon", "ADJ", 3, "parataxis"),
        ("dã_man", "ADV", 7, "advmod"),
        ("luôn", "PART", 7, "discourse"),
        (".", "PUNCT", 3, "punct"),
    ]),
    ("gold-i03", "Mai đi học sớm nha, đừng trễ nữa đó.", [
        ("Mai", "NOUN", 2, "obl"),
        ("đi_học", "VERB", 0, "root"),
        ("sớm", "ADV", 2, "advmod"),
        ("nha", "PART", 2, "discourse"),
        (",", "PUNCT", 7, "punct"),
        ("đừng", "PART", 7, "advmod"),
        ("trễ", "VERB", 2, "parataxis"),
        ("nữa", "ADV", 7, "advmod"),
        ("đó", "PART", 7, "discourse"),
        (".", "PUNCT", 2, "punct"),
    ]),
    ("gold-i04", "Bộ phim tối qua coi hay ghê, mày xem chưa?", [
        ("Bộ_phim", "NOUN", 4, "obj"),
        ("tối", "NOUN", 1, "nmod"),
        ("qua", "ADJ", 2, "amod"),
        ("coi", "VERB", 0, "root"),
        ("hay", "ADJ", 4, "parataxis"),
        ("ghê", "ADV", 5, "advmod"),
        (",", "PUNCT", 9, "punct"),
        ("mày", "PRON", 9, "nsubj"),
        ("xem", "VERB", 4, "parataxis"),
        ("chưa", "ADV", 9, "advmod"),
        ("?", "PUNCT", 4, "punct"),
    ]),
    ("gold-i05", "Cuối tuần này rảnh không, đi chơi Đà Lạt đi.", [
        ("Cuối_tuần", "NOUN", 3, "obl"),
        ("này", "DET", 1, "det"),
        ("rảnh", "ADJ", 0, "root"),
        ("không", "PART", 3, "discourse"),
        (",", "PUNCT", 6, "punct"),
        ("đi_chơi", "VERB", 3, "parataxis"),
        ("Đà_Lạt", "PROPN", 6, "obl"),
        ("đi", "PART", 6, "discourse"),
        (".", "PUNCT", 3, "punct"),
    ]),
    ("gold-i06", "Nay mưa to quá trời, chắc kẹt xe dữ lắm.", [
        ("Nay", "NOUN", 2, "obl"),
        ("mưa", "VERB", 0, "root"),
        ("to", "ADJ", 2, "advmod"),
        ("quá", "ADV", 3, "advmod"),
        ("trời", "NOUN", 4, "fixed"),
        (",", "PUNCT", 8, "punct"),
        ("chắc", "ADV", 8, "advmod"),
        ("kẹt_xe", "VERB", 2, "parataxis"),
        ("dữ", "ADV", 8, "advmod"),
        ("lắm", "ADV", 8, "advmod"),
        (".", "PUNCT", 2, "punct"),
    ]),
    ("gold-i07", "Đói bụng ghê, kiếm gì ăn thôi mọi người ơi.", [
        ("Đói_bụng", "ADJ", 0, "root"),
        ("ghê", "ADV", 1, "advmod"),
        (",", "PUNCT", 4, "punct"),
        ("kiếm", "VERB", 1, "parataxis"),
        ("gì", "PRON", 4, "obj"),
        ("ăn", "VERB", 5, "acl"),
        ("thôi", "PART", 4, "discourse"),
        ("mọi_người", "NOUN", 4, "vocative"),
        ("ơi", "PART", 8, "discourse"),
        (".", "PUNCT", 1, "punct"),
    ]),
    ("gold-i08", "Con mèo nhà tao nghịch banh quá trời luôn.", [
        ("Con", "NOUN", 2, "clf"),
        ("mèo", "NOUN", 5, "nsubj"),
        ("nhà", "NOUN", 2, "nmod"),
        ("tao", "PRON", 3, "nmod"),
        ("nghịch", "VERB", 0, "root"),
        ("banh", "NOUN", 5, "obj"),
        ("quá", "ADV", 5, "advmod"),
        ("trời", "NOUN", 7, "fixed"),
        ("luôn", "PART", 5, "discourse"),
        (".", "PUNCT", 5, "punct"),
    ]),
    ("gold-i09", "Bài tập cô giao khó ghê, ai làm xong chưa vậy.", [
        ("Bài_tập", "NOUN", 4, "nsubj"),
        ("cô", "NOUN", 3, "nsubj"),
        ("giao", "VERB", 1, "acl"),
        ("khó", "ADJ", 0, "root"),
        ("ghê", "ADV", 4, "advmod"),
        (",", "PUNCT", 8, "punct"),
        ("ai", "PRON", 8, "nsubj"),
        ("làm", "VERB", 4, "parataxis"),
        ("xong", "ADV", 8, "advmod"),
        ("chưa", "ADV", 8, "advmod"),
        ("vậy", "PART", 8, "discourse"),
        (".", "PUNCT", 4, "punct"),
    ]),
    ("gold-i10", "Chiều nay đá bóng không, thiếu người quá.", [
        ("Chiều_nay", "NOUN", 2, "obl"),
        ("đá_bóng", "VERB", 0, "root"),
        ("không", "PART", 2, "discourse"),
        (",", "PUNCT", 5, "punct"),
        ("thiếu", "VERB", 2, "parataxis"),
        ("người", "NOUN", 5, "obj"),
        ("quá", "ADV", 5, "advmod"),
        (".", "PUNCT", 2, "punct"),
    ]),
]

# ---------------------------------------------------------------------------
# System B: perturbations by (sent_id, token_index (1-based), field, new_value, note).
# Everything not listed here is identical to gold for that sentence.
# ---------------------------------------------------------------------------
_PERTURBATIONS: dict[str, tuple[str, list[tuple[int, str, object]]]] = {
    "gold-f01": (
        "Coordination scope: system B attaches 'Đào_tạo' as a second conjunct "
        "directly under 'Bộ' rather than under 'Giáo_dục' -- a real ambiguity in "
        "whether 'A và B' modifies the head noun as two parallel conjuncts of one "
        "flat chain, or as a nested coordination.",
        [(4, "head", 1)],  # Đào_tạo's head: gold=2 (Giáo_dục) -> system B=1 (Bộ)
    ),
    "gold-f03": (
        "Compound-attachment ambiguity: does 'quốc gia' (national) modify 'bóng đá' "
        "(-> 'national football' as a sport) or 'đội tuyển' (-> 'national team')? "
        "System B attaches it to the closer noun 'bóng_đá'.",
        [(3, "head", 2)],  # quốc_gia's head: gold=1 (Đội_tuyển) -> system B=2 (bóng_đá)
    ),
    "gold-f05": (
        "PP-attachment ambiguity: does 'tại đồng bằng sông Cửu Long' locate the "
        "climate change phenomenon itself, or the act of announcing it? System B "
        "attaches the location low, inside the object NP, instead of to the verb.",
        [(10, "head", 8)],  # đồng_bằng's head: gold=3 (công_bố) -> system B=8 (khí_hậu)
    ),
    "gold-f07": (
        "Deprel disagreement on a bare proper-noun-as-modifier: 'tiếng Việt' "
        "(Vietnamese language) analyzed as a flat multiword name in gold, but as "
        "an ordinary adjectival modifier by system B.",
        [(10, "deprel", "amod")],  # Việt: gold deprel=flat -> system B=amod (head unchanged)
    ),
    "gold-f09": (
        "Nominal-modifier scope: does 'đợt hai' (round two) scope over 'kết quả' "
        "(the results) or over 'tuyển sinh' (the admissions process itself)? "
        "System B attaches it to the narrower head.",
        [(7, "head", 6)],  # đợt's head: gold=5 (kết_quả) -> system B=6 (tuyển_sinh)
    ),
    "gold-i02": (
        "UPOS disagreement on slang intensifier 'dã man': it can function as a "
        "manner adverb (gold) or be re-analyzed as a predicate adjective in a "
        "reduced construction (system B) -- a real category-boundary case for "
        "colloquial intensifiers.",
        [(8, "upos", "ADJ")],  # dã_man: gold ADV -> system B ADJ
    ),
    "gold-i04": (
        "Grammatical-relation disagreement on a topicalized object: 'Bộ phim' is "
        "fronted before the verb, which a parser trained on more rigid SVO data "
        "can misanalyze as the subject rather than the (pragmatically fronted) "
        "object of 'coi'.",
        [(1, "deprel", "nsubj")],  # Bộ_phim: gold deprel=obj -> system B=nsubj (head unchanged)
    ),
    "gold-i06": (
        "Modal-adverb scope across a parataxis boundary: does 'chắc' (probably) "
        "scope over the whole utterance (attaching to the first clause's root, "
        "system B) or just the second clause it linearly precedes (gold)?",
        [(7, "head", 2)],  # chắc's head: gold=8 (kẹt_xe) -> system B=2 (mưa)
    ),
    "gold-i08": (
        "Classifier vs. determiner confusion: 'con' is a numeral classifier "
        "(clf) in gold, but a generic parser unfamiliar with the Vietnamese "
        "classifier system commonly mislabels this token class as a determiner.",
        [(1, "deprel", "det")],  # Con: gold deprel=clf -> system B=det (head unchanged)
    ),
    "gold-i10": (
        "Temporal-scope ambiguity across a parataxis boundary: does 'chiều nay' "
        "(this afternoon) modify 'đá bóng' (playing football, gold) or 'thiếu "
        "người' (being short of people, system B)?",
        [(1, "head", 5)],  # Chiều_nay's head: gold=2 (đá_bóng) -> system B=5 (thiếu)
    ),
}


def _validate_upos_and_deprel(sentences: list[Sentence]) -> None:
    for sent_id, text, tokens in sentences:
        for i, (form, upos, head, deprel) in enumerate(tokens, start=1):
            if upos not in UPOS_TAGSET:
                raise ValueError(f"{sent_id} token {i} ({form!r}): upos {upos!r} not in UPOS_TAGSET")
            if deprel not in UD_DEPREL:
                raise ValueError(f"{sent_id} token {i} ({form!r}): deprel {deprel!r} not in UD_DEPREL")
            if not (0 <= head <= len(tokens)):
                raise ValueError(f"{sent_id} token {i} ({form!r}): head {head} out of range")


def _validate_tree_shape(sent_id: str, tokens: list[Token]) -> None:
    """Single root, every non-root head a real token, no cycles -- mirrors
    `interfaces.ud.is_single_rooted_tree`."""
    n = len(tokens)
    roots = [i for i, t in enumerate(tokens, start=1) if t[2] == 0]
    if len(roots) != 1:
        raise ValueError(f"{sent_id}: expected exactly 1 root, found {len(roots)}")
    by_idx = {i: t for i, t in enumerate(tokens, start=1)}
    for i in range(1, n + 1):
        seen = set()
        cur = i
        while by_idx[cur][2] != 0:
            if cur in seen:
                raise ValueError(f"{sent_id}: cycle detected starting at token {i}")
            seen.add(cur)
            cur = by_idx[cur][2]


def _apply_perturbation(sent_id: str, tokens: list[Token]) -> tuple[list[Token], str | None]:
    if sent_id not in _PERTURBATIONS:
        return list(tokens), None
    note, edits = _PERTURBATIONS[sent_id]
    tokens = list(tokens)
    for idx, field, value in edits:
        form, upos, head, deprel = tokens[idx - 1]
        if field == "head":
            head = value
        elif field == "deprel":
            deprel = value
        elif field == "upos":
            upos = value
        else:
            raise ValueError(f"unknown perturbation field {field!r}")
        tokens[idx - 1] = (form, upos, head, deprel)
    return tokens, note


def _render(sentences: list[tuple[str, str, list[Token], str | None]]) -> str:
    lines = []
    for sent_id, text, tokens, note in sentences:
        lines.append(f"# sent_id = {sent_id}")
        lines.append(f"# text = {text}")
        if note:
            lines.append(f"# note = {note}")
        for i, (form, upos, head, deprel) in enumerate(tokens, start=1):
            lines.append(f"{i}\t{form}\t_\t{upos}\t_\t_\t{head}\t{deprel}\t_\t_")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    _validate_upos_and_deprel(_GOLD)
    for sent_id, _text, tokens in _GOLD:
        _validate_tree_shape(sent_id, tokens)

    system_b: list[tuple[str, str, list[Token], str | None]] = []
    gold_rendered: list[tuple[str, str, list[Token], str | None]] = []
    for sent_id, text, tokens in _GOLD:
        gold_rendered.append((sent_id, text, tokens, None))
        perturbed_tokens, note = _apply_perturbation(sent_id, tokens)
        if note:
            _validate_upos_and_deprel([(sent_id, text, perturbed_tokens)])
            _validate_tree_shape(sent_id + " (system B)", perturbed_tokens)
        system_b.append((sent_id, text, perturbed_tokens, note))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "gold_treebank_seed.conllu").write_text(_render(gold_rendered), encoding="utf-8")
    (OUT_DIR / "system_b_perturbed.conllu").write_text(_render(system_b), encoding="utf-8")

    n_perturbed = sum(1 for _, _, _, note in system_b if note)
    print(f"wrote {len(_GOLD)} sentences to gold_treebank_seed.conllu")
    print(f"wrote {len(system_b)} sentences to system_b_perturbed.conllu ({n_perturbed} perturbed)")


if __name__ == "__main__":
    main()
