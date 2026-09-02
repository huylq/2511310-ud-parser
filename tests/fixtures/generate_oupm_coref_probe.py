"""Generates `oupm/oupm_coref_probe.jsonl` and
`oupm/oupm_coref_probe_gold_clusters.jsonl` -- Project 7's entity-resolution
fixture.

PROVISIONAL: this is an AI-drafted first pass. Per CLAUDE.md rule 2 (model
output never enters Gold unvalidated) and the plan's review process, this
fixture is NOT frozen until the professor reviews and signs off -- see
`tests/fixtures/oupm/PROVISIONAL.md`.

12 synthetic documents, each hand-designed around one of the specific
entity-resolution traps `.claude/agents/oupm-modeler.md` and the plan's I/O
contract table name: bare-surname collision (two different people sharing
a common surname must NOT merge), diacritic-variant spelling of the same
name (CLAUDE.md's own `hoà` vs `hòa` example), honorific stripping
(`anh`/`chi`/`ong`/`ba` + given name referring back to a full name),
nickname-to-full-name linking, an identical full name belonging to two
different people (must NOT merge -- disambiguated only by co-occurring
context, never string identity alone), middle-name-dropped variants, an
organization acronym-vs-full-name variant, and one easy baseline (exact
repeats) as a sanity control.

Mentions are hand-specified as `(sentence_index, phrase, label, occurrence)`
-- `token_start`/`token_end` are resolved automatically by locating
`phrase.split()` as a contiguous run within `sentence.split()`, so a
miscounted manual offset cannot silently ship (mirrors
`generate_benchmark_stubs.py`'s ViQuAD `answer_start` resolution).

Run: python tests/fixtures/generate_oupm_coref_probe.py
"""
from __future__ import annotations

import json
from pathlib import Path

OUT_DIR = Path(__file__).parent / "oupm"


def _find_span(tokens: list[str], phrase: str, occurrence: int = 0) -> tuple[int, int]:
    """Locates the `occurrence`-th (0-based) contiguous run of
    `phrase.split()` within `tokens`. Raises `ValueError` if not found --
    a resolution failure here means the hand-authored doc/phrase pair
    disagree, and must be fixed at the source, never silently skipped."""
    needle = phrase.split()
    n, m = len(tokens), len(needle)
    found = 0
    for i in range(n - m + 1):
        if tokens[i:i + m] == needle:
            if found == occurrence:
                return i, i + m
            found += 1
    raise ValueError(f"phrase {phrase!r} (occurrence {occurrence}) not found in {tokens!r}")


# Each doc: (doc_id, [sentence strings], [(sent_idx, phrase, label, occurrence), ...], [(canonical_name, [mention indices into the mentions list above]), ...])
_DOCS = [
    (
        "probe-01-surname-collision",
        [
            "Nguyễn Văn Nam phát biểu tại hội nghị hôm qua .",
            "Ông Nam cho biết chương trình sẽ triển khai vào tháng tới .",
            "Trong khi đó , Nguyễn Thị Lan cũng tham dự sự kiện .",
        ],
        [(0, "Nguyễn Văn Nam", "PER", 0), (1, "Nam", "PER", 0), (2, "Nguyễn Thị Lan", "PER", 0)],
        [("Nguyễn Văn Nam", [0, 1]), ("Nguyễn Thị Lan", [2])],
    ),
    (
        "probe-02-diacritic-variant",
        [
            "Nguyễn Thị Hòa là bác sĩ tại bệnh viện .",
            "Sau đó , Nguyễn Thị Hoà được mời phát biểu .",
        ],
        [(0, "Nguyễn Thị Hòa", "PER", 0), (1, "Nguyễn Thị Hoà", "PER", 0)],
        [("Nguyễn Thị Hòa", [0, 1])],
    ),
    (
        "probe-03-honorific-stripping",
        [
            "Trần Văn Bình là chủ tịch công ty .",
            "Anh Bình chia sẻ kế hoạch mở rộng kinh doanh .",
        ],
        [(0, "Trần Văn Bình", "PER", 0), (1, "Bình", "PER", 0)],
        [("Trần Văn Bình", [0, 1])],
    ),
    (
        "probe-04-nickname",
        [
            "Lê Thị Hương thường được gọi là Hương Nhỏ .",
            "Hương Nhỏ vừa đạt giải thưởng quốc gia .",
        ],
        [(0, "Lê Thị Hương", "PER", 0), (0, "Hương Nhỏ", "PER", 0), (1, "Hương Nhỏ", "PER", 0)],
        [("Lê Thị Hương", [0, 1, 2])],
    ),
    (
        "probe-05-same-name-different-people",
        [
            "Nguyễn Văn Hùng ở Hà Nội vừa nhận giải thưởng .",
            "Một Nguyễn Văn Hùng khác ở Cần Thơ bị xử phạt vì vi phạm giao thông .",
        ],
        [(0, "Nguyễn Văn Hùng", "PER", 0), (0, "Hà Nội", "LOC", 0),
         (1, "Nguyễn Văn Hùng", "PER", 0), (1, "Cần Thơ", "LOC", 0)],
        [("Nguyễn Văn Hùng (Hà Nội)", [0]), ("Hà Nội", [1]),
         ("Nguyễn Văn Hùng (Cần Thơ)", [2]), ("Cần Thơ", [3])],
    ),
    (
        "probe-06-org-acronym-variant",
        [
            "Tập đoàn FPT ra mắt sản phẩm phần mềm mới .",
            "FPT cho biết sẽ đầu tư thêm vào nghiên cứu trí tuệ nhân tạo .",
        ],
        [(0, "Tập đoàn FPT", "ORG", 0), (1, "FPT", "ORG", 0)],
        [("Tập đoàn FPT", [0, 1])],
    ),
    (
        "probe-07-honorific-plus-surname-collision",
        [
            "Chị Phạm Thị Mai là giáo viên tại trường .",
            "Mai nói rằng học sinh rất chăm chỉ .",
            "Một giáo viên khác , Phạm Văn Long , cũng được khen thưởng .",
        ],
        [(0, "Phạm Thị Mai", "PER", 0), (1, "Mai", "PER", 0), (2, "Phạm Văn Long", "PER", 0)],
        [("Phạm Thị Mai", [0, 1]), ("Phạm Văn Long", [2])],
    ),
    (
        "probe-08-multi-person-same-surname-stress",
        [
            "Trong lớp có ba bạn tên Nguyễn Văn An , Nguyễn Văn Bình và Nguyễn Văn Cường .",
            "Nguyễn Văn An đạt điểm cao nhất kỳ thi .",
        ],
        [(0, "Nguyễn Văn An", "PER", 0), (0, "Nguyễn Văn Bình", "PER", 0), (0, "Nguyễn Văn Cường", "PER", 0),
         (1, "Nguyễn Văn An", "PER", 0)],
        [("Nguyễn Văn An", [0, 3]), ("Nguyễn Văn Bình", [1]), ("Nguyễn Văn Cường", [2])],
    ),
    (
        "probe-09-middle-name-dropped",
        [
            "Đặng Thị Kim Ngân phát biểu khai mạc chương trình .",
            "Đặng Kim Ngân cảm ơn các đại biểu tham dự .",
        ],
        [(0, "Đặng Thị Kim Ngân", "PER", 0), (1, "Đặng Kim Ngân", "PER", 0)],
        [("Đặng Thị Kim Ngân", [0, 1])],
    ),
    (
        "probe-10-same-given-name-different-surname",
        [
            "Vũ Văn Sơn nhận bằng khen của thành phố .",
            "Đỗ Văn Sơn cũng có mặt tại buổi lễ , nhưng không được vinh danh .",
        ],
        [(0, "Vũ Văn Sơn", "PER", 0), (1, "Đỗ Văn Sơn", "PER", 0)],
        [("Vũ Văn Sơn", [0]), ("Đỗ Văn Sơn", [1])],
    ),
    (
        "probe-11-mixed-per-loc-labels",
        [
            "Bà Trịnh Thị Thu Hà đến thăm Đà Nẵng tuần trước .",
            "Thu Hà chia sẻ ấn tượng về chuyến đi .",
        ],
        [(0, "Trịnh Thị Thu Hà", "PER", 0), (0, "Đà Nẵng", "LOC", 0), (1, "Thu Hà", "PER", 0)],
        [("Trịnh Thị Thu Hà", [0, 2]), ("Đà Nẵng", [1])],
    ),
    (
        "probe-12-easy-baseline-exact-repeats",
        [
            "Hoàng Văn Đức tổ chức buổi hội thảo .",
            "Hoàng Văn Đức cảm ơn các diễn giả tham gia .",
            "Cuối chương trình , Hoàng Văn Đức tặng quà lưu niệm cho khách mời .",
        ],
        [(0, "Hoàng Văn Đức", "PER", 0), (1, "Hoàng Văn Đức", "PER", 0), (2, "Hoàng Văn Đức", "PER", 0)],
        [("Hoàng Văn Đức", [0, 1, 2])],
    ),
]


def build() -> tuple[list[dict], list[dict]]:
    probe_docs = []
    gold_docs = []
    for doc_id, sentences, mention_specs, clusters_spec in _DOCS:
        tokenized = [s.split() for s in sentences]
        mentions = []
        for sent_idx, phrase, label, occurrence in mention_specs:
            start, end = _find_span(tokenized[sent_idx], phrase, occurrence)
            sent_id = f"{doc_id}:{sent_idx}"
            mentions.append({
                "sent_id": sent_id,
                "mention_id": f"{sent_id}:{start}:{end}",
                "token_start": start,
                "token_end": end,
                "label": label,
                "text": phrase,
            })
        probe_docs.append({
            "doc_id": doc_id,
            "sentences": [{"sent_idx": i, "tokens": toks} for i, toks in enumerate(tokenized)],
            "mentions": mentions,
        })
        clusters = [
            {
                "cluster_id": f"{doc_id}:cluster-{i}",
                "canonical_name": name,
                "mention_ids": [mentions[idx]["mention_id"] for idx in indices],
            }
            for i, (name, indices) in enumerate(clusters_spec)
        ]
        gold_docs.append({"doc_id": doc_id, "clusters": clusters})
    return probe_docs, gold_docs


def main() -> None:
    probe_docs, gold_docs = build()
    assert len(probe_docs) == 12, len(probe_docs)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    probe_path = OUT_DIR / "oupm_coref_probe.jsonl"
    with probe_path.open("w", encoding="utf-8") as f:
        for doc in probe_docs:
            f.write(json.dumps(doc, ensure_ascii=False, sort_keys=True) + "\n")

    gold_path = OUT_DIR / "oupm_coref_probe_gold_clusters.jsonl"
    with gold_path.open("w", encoding="utf-8") as f:
        for doc in gold_docs:
            f.write(json.dumps(doc, ensure_ascii=False, sort_keys=True) + "\n")

    n_mentions = sum(len(d["mentions"]) for d in probe_docs)
    n_clusters = sum(len(d["clusters"]) for d in gold_docs)
    print(f"wrote {len(probe_docs)} docs / {n_mentions} mentions to {probe_path}")
    print(f"wrote {len(gold_docs)} docs / {n_clusters} gold clusters to {gold_path}")


if __name__ == "__main__":
    main()
