"""Week 3 CoNLL-U reader tests."""

from pathlib import Path

import pytest

from vietnlp.linguistics.ud_parser import read_conllu

# Check metadata and tokens for two sentences, including the final sentence at EOF.
TWO_SENTENCE_CONLLU = """# sent_id = hc-021
# text = Trưa nay chúng tôi đi ăn trưa ở nhà hàng mới
# register = informal
# synthetic = false
# constructions =
# uncertain = false
# notes = Projection: Trưa nay, chúng tôi và nhà hàng dùng âm tiết đầu làm đại diện, các cạnh nội bộ dùng dep. Đi là root, ăn là xcomp theo cấu trúc chuỗi động từ (SVC).
1	Trưa	_	X	_	_	5	obl	_	_
2	nay	_	X	_	_	1	dep	_	_
3	chúng	_	X	_	_	5	nsubj	_	_
4	tôi	_	X	_	_	3	dep	_	_
5	đi	_	X	_	_	0	root	_	_
6	ăn	_	X	_	_	5	xcomp	_	_
7	trưa	_	X	_	_	6	obj	_	_
8	ở	_	X	_	_	9	case	_	_
9	nhà	_	X	_	_	6	obl	_	_
10	hàng	_	X	_	_	9	dep	_	_
11	mới	_	X	_	_	9	amod	_	_

# sent_id = hc-022
# text = Chiều ngày 24/10/2026, do trời mưa nhiều nên nhiều chuyến xe khách bị chậm giờ khởi hành.
# register = formal
# synthetic = false
# constructions = clf_noun
# uncertain = false
# notes = Projection: xe khách và khởi hành dùng âm tiết đầu làm đại diện, các cạnh nội bộ dùng dep. Chậm là root, mưa là advcl chỉ nguyên nhân phụ thuộc vào chậm thông qua liên từ do.
1	Chiều	_	X	_	_	14	obl	_	_
2	ngày	_	X	_	_	1	nmod	_	_
3	24/10/2026,	_	X	_	_	2	nmod	_	_
4	do	_	X	_	_	6	mark	_	_
5	trời	_	X	_	_	6	nsubj	_	_
6	mưa	_	X	_	_	14	advcl	_	_
7	nhiều	_	X	_	_	6	advmod	_	_
8	nên	_	X	_	_	14	mark	_	_
9	nhiều	_	X	_	_	11	det	_	_
10	chuyến	_	X	_	_	11	clf	_	_
11	xe	_	X	_	_	14	nsubj	_	_
12	khách	_	X	_	_	11	dep	_	_
13	bị	_	X	_	_	14	aux	_	_
14	chậm	_	X	_	_	0	root	_	_
15	giờ	_	X	_	_	14	obj	_	_
16	khởi	_	X	_	_	15	nmod	_	_
17	hành.	_	X	_	_	16	dep	_	_"""

# Tuple fields: ID, FORM, UPOS, HEAD, DEPREL.
EXPECTED_TOKENS = (
    (
        (1, "Trưa", "X", 5, "obl"),
        (2, "nay", "X", 1, "dep"),
        (3, "chúng", "X", 5, "nsubj"),
        (4, "tôi", "X", 3, "dep"),
        (5, "đi", "X", 0, "root"),
        (6, "ăn", "X", 5, "xcomp"),
        (7, "trưa", "X", 6, "obj"),
        (8, "ở", "X", 9, "case"),
        (9, "nhà", "X", 6, "obl"),
        (10, "hàng", "X", 9, "dep"),
        (11, "mới", "X", 9, "amod"),
    ),
    (
        (1, "Chiều", "X", 14, "obl"),
        (2, "ngày", "X", 1, "nmod"),
        (3, "24/10/2026,", "X", 2, "nmod"),
        (4, "do", "X", 6, "mark"),
        (5, "trời", "X", 6, "nsubj"),
        (6, "mưa", "X", 14, "advcl"),
        (7, "nhiều", "X", 6, "advmod"),
        (8, "nên", "X", 14, "mark"),
        (9, "nhiều", "X", 11, "det"),
        (10, "chuyến", "X", 11, "clf"),
        (11, "xe", "X", 14, "nsubj"),
        (12, "khách", "X", 11, "dep"),
        (13, "bị", "X", 14, "aux"),
        (14, "chậm", "X", 0, "root"),
        (15, "giờ", "X", 14, "obj"),
        (16, "khởi", "X", 15, "nmod"),
        (17, "hành.", "X", 16, "dep"),
    ),
)


def test_read_conllu_two_sentences_preserves_metadata_and_basic_nodes():
    """Read two sentences, including the last one at end of input."""
    sentences = read_conllu(TWO_SENTENCE_CONLLU)

    assert isinstance(sentences, list)
    assert len(sentences) == 2
    assert [sentence.metadata["sent_id"] for sentence in sentences] == [
        "hc-021", "hc-022",
    ]
    assert [sentence.metadata["text"] for sentence in sentences] == [
        "Trưa nay chúng tôi đi ăn trưa ở nhà hàng mới",
        "Chiều ngày 24/10/2026, do trời mưa nhiều nên nhiều chuyến xe khách bị chậm giờ khởi hành.",
    ]
    assert sentences[0].metadata["constructions"] == ""
    assert sentences[1].metadata["constructions"] == "clf_noun"

    for sentence, expected in zip(sentences, EXPECTED_TOKENS, strict=True):
        actual = tuple(
            (token.id, token.form, token.upos, token.head, token.deprel)
            for token in sentence.tokens
        )
        assert actual == expected, sentence.metadata["sent_id"]
        assert all(type(token.id) is int for token in sentence.tokens)
        assert all(type(token.head) is int for token in sentence.tokens)


@pytest.mark.parametrize("sentence_index", [0, 1], ids=["first_sentence", "second_sentence"])
@pytest.mark.parametrize(
    "case, reason",
    [
        ("missing_column", "expected 10 TAB-separated columns"),
        ("extra_column", "expected 10 TAB-separated columns"),
        ("noninteger_head", "HEAD must be an integer"),
        ("nonconsecutive_id", "IDs must be consecutive from 1"),
        ("head_outside_sentence", "HEAD is outside the sentence"),
    ],
)
def test_read_conllu_malformed_input_reports_line(sentence_index, case, reason):
    """Change one row and check the error reason and absolute source line."""
    lines = TWO_SENTENCE_CONLLU.splitlines()
    starts = [index for index, line in enumerate(lines) if line.startswith("1\t")]
    row_index = starts[sentence_index] + 1
    fields = lines[row_index].split("\t")

    if case == "missing_column":
        fields.pop()
    elif case == "extra_column":
        fields.append("_")
    elif case == "noninteger_head":
        fields[6] = "not-an-integer"
    elif case == "nonconsecutive_id":
        fields[0] = str(int(fields[0]) + 1)
    elif case == "head_outside_sentence":
        fields[6] = str(len(EXPECTED_TOKENS[sentence_index]) + 1)

    lines[row_index] = "\t".join(fields)

    with pytest.raises(ValueError, match=rf"\bline {row_index + 1}\b") as error:
        read_conllu("\n".join(lines))
    assert reason in str(error.value)


@pytest.mark.parametrize(
    "special_id, token_id, insert_before",
    [("3-4", 3, True), ("5.1", 5, False)],
    ids=["multiword_range", "empty_node"],
)
def test_read_conllu_skips_nonbasic_rows(special_id, token_id, insert_before):
    """Skip range/decimal rows without changing metadata or basic nodes."""
    lines = TWO_SENTENCE_CONLLU.splitlines()
    row_index = next(
        index for index, line in enumerate(lines) if line.startswith(f"{token_id}\t")
    )
    fields = lines[row_index].split("\t")
    fields[0] = special_id
    fields[2:] = ["_"] * 8
    insert_at = row_index if insert_before else row_index + 1
    lines.insert(insert_at, "\t".join(fields))

    sentences = read_conllu("\n".join(lines))

    assert len(sentences) == 2
    assert [sentence.metadata["sent_id"] for sentence in sentences] == [
        "hc-021", "hc-022",
    ]
    for sentence, expected in zip(sentences, EXPECTED_TOKENS, strict=True):
        actual = tuple(
            (token.id, token.form, token.upos, token.head, token.deprel)
            for token in sentence.tokens
        )
        assert actual == expected, sentence.metadata["sent_id"]


def test_read_conllu_hand_annotated_set_has_twenty_valid_trees():
    """Read all annotated sentences and validate their dependency trees."""
    from vietnlp.interfaces.ud import (
        DependencyParse,
        UDToken,
        is_single_rooted_tree,
        validate_dependency_parse,
    )

    data = (
        Path(__file__).resolve().parents[1]
        / "student-projects/02-ud-parsing/data/hand_annotated.conllu"
    )
    sentences = read_conllu(data.read_text(encoding="utf-8"))

    assert len(sentences) == 20
    assert sum(len(sentence.tokens) for sentence in sentences) == 254
    for sentence in sentences:
        tree = DependencyParse(
            sent_id=sentence.metadata["sent_id"],
            tokens=tuple(
                UDToken(
                    idx=token.id - 1,
                    form=token.form,
                    upos=token.upos,
                    head=token.head,
                    deprel=token.deprel,
                )
                for token in sentence.tokens
            ),
            source="real",
        )
        validate_dependency_parse(tree)
        assert is_single_rooted_tree(tree), tree.sent_id
