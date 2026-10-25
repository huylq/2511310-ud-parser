"""Week 3 CoNLL-U reader tests."""

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
    from vietnlp.linguistics.ud_parser import read_conllu

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
