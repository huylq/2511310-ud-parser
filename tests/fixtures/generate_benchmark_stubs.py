"""Generates `benchmark/{vlsp_ner,uit_vsfc,viquad}_stub.jsonl` -- Project 9's
format-shape stand-ins for the three CLAUDE.md benchmark suites (VLSP shared
tasks, UIT-VSFC, ViQuAD).

NOT THE REAL BENCHMARKS. These are hand-authored, small (10-15 rows each),
and exist only so Project 9's harness has something of the right *shape* to
run its scoring code against before the real benchmark data is sourced and
licensed -- every row also carries `"stub_note"` saying so explicitly, so a
report generated from these can never be mistaken for a real score. Real
VLSP/UIT-VSFC/ViQuAD releases have their own licenses and must be obtained
separately; do not point Project 9's real benchmark run at this file.

Run: python tests/fixtures/generate_benchmark_stubs.py
"""
from __future__ import annotations

import json
from pathlib import Path

OUT_DIR = Path(__file__).parent / "benchmark"

_STUB_NOTE = "format-shape stand-in only -- not the real shared-task data"

# ---- VLSP-shaped NER stand-in: BIO tags over whitespace tokens, labels PER/LOC/ORG/MISC ----
VLSP_NER = [
    {"tokens": ["Nguyễn", "Văn", "A", "làm", "việc", "tại", "Hà", "Nội", "."],
     "ner_tags": ["B-PER", "I-PER", "I-PER", "O", "O", "O", "B-LOC", "I-LOC", "O"]},
    {"tokens": ["Bộ", "Giáo", "dục", "và", "Đào", "tạo", "công", "bố", "lịch", "thi", "."],
     "ner_tags": ["B-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "O", "O", "O", "O", "O"]},
    {"tokens": ["Ngân", "hàng", "Nhà", "nước", "giữ", "nguyên", "lãi", "suất", "."],
     "ner_tags": ["B-ORG", "I-ORG", "I-ORG", "I-ORG", "O", "O", "O", "O", "O"]},
    {"tokens": ["Trần", "Thị", "B", "và", "Lê", "Văn", "C", "gặp", "nhau", "ở", "Đà", "Nẵng", "."],
     "ner_tags": ["B-PER", "I-PER", "I-PER", "O", "B-PER", "I-PER", "I-PER", "O", "O", "O", "B-LOC", "I-LOC", "O"]},
    {"tokens": ["Đội", "tuyển", "bóng", "đá", "quốc", "gia", "thắng", "trận", "."],
     "ner_tags": ["O", "O", "O", "O", "O", "O", "O", "O", "O"]},  # negative case: no entities
    {"tokens": ["Tập", "đoàn", "FPT", "ra", "mắt", "sản", "phẩm", "mới", "tại", "Thành", "phố", "Hồ", "Chí", "Minh", "."],
     "ner_tags": ["B-ORG", "I-ORG", "I-ORG", "O", "O", "O", "O", "O", "O", "B-LOC", "I-LOC", "I-LOC", "I-LOC", "I-LOC", "O"]},
    {"tokens": ["Nam", "."],
     "ner_tags": ["B-PER", "O"]},  # degenerate case: single-token sentence with one entity
    {"tokens": ["Trường", "Đại", "học", "Bách", "khoa", "Hà", "Nội", "tuyển", "sinh", "."],
     "ner_tags": ["B-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "O", "O", "O"]},
    {"tokens": ["WHO", "cảnh", "báo", "về", "dịch", "bệnh", "mới", "."],
     "ner_tags": ["B-ORG", "O", "O", "O", "O", "O", "O", "O"]},  # adversarial: acronym-only org
    {"tokens": ["Chính", "phủ", "Việt", "Nam", "và", "Nhật", "Bản", "ký", "hiệp", "định", "."],
     "ner_tags": ["B-ORG", "I-ORG", "I-LOC", "I-LOC", "O", "B-LOC", "I-LOC", "O", "O", "O", "O"]},
    {"tokens": ["Sở", "Y", "tế", "Thành", "phố", "Hồ", "Chí", "Minh", "họp", "khẩn", "."],
     "ner_tags": ["B-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "O", "O", "O"]},
    {"tokens": ["Ông", "Nguyễn", "Văn", "A", "là", "Bộ", "trưởng", "Bộ", "Y", "tế", "."],
     "ner_tags": ["O", "B-PER", "I-PER", "I-PER", "O", "B-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "O"]},
]

# ---- UIT-VSFC-shaped student-feedback sentiment stand-in ----
UIT_VSFC = [
    {"text": "Giảng viên dạy rất nhiệt tình và dễ hiểu.", "sentiment": "positive", "topic": "lecturer"},
    {"text": "Chương trình học quá nặng so với thời lượng.", "sentiment": "negative", "topic": "training_program"},
    {"text": "Cơ sở vật chất phòng học khá ổn, có máy chiếu đầy đủ.", "sentiment": "positive", "topic": "facility"},
    {"text": "Giảng viên đến trễ nhiều buổi, sinh viên phải chờ.", "sentiment": "negative", "topic": "lecturer"},
    {"text": "Chương trình học nói chung là bình thường, không có gì đặc biệt.", "sentiment": "neutral", "topic": "training_program"},
    {"text": "Wifi trong trường yếu, khó truy cập tài liệu online.", "sentiment": "negative", "topic": "facility"},
    {"text": "Giảng viên nhiệt tình giải đáp thắc mắc ngoài giờ học.", "sentiment": "positive", "topic": "lecturer"},
    {"text": "Lịch thi được thông báo đúng hạn.", "sentiment": "neutral", "topic": "training_program"},
    {"text": "", "sentiment": "neutral", "topic": "other"},  # degenerate case: empty text
    {"text": "Thư viện mở cửa muộn, sinh viên khó sắp xếp thời gian ôn tập, rất bất tiện.", "sentiment": "negative", "topic": "facility"},
    {"text": "Bài giảng có ví dụ thực tế sinh động, dễ áp dụng vào bài tập.", "sentiment": "positive", "topic": "lecturer"},
    {"text": "khong co gi de noi ca", "sentiment": "neutral", "topic": "other"},  # adversarial: non-diacritic register
]

# ---- ViQuAD-shaped extractive QA stand-in ----
# `answer_start` is deliberately NOT hand-typed here -- it is computed by
# `main()` from `context.index(answer_text)` below, so a miscounted offset
# fails the generator loudly instead of silently shipping a wrong fixture.
VIQUAD = [
    {
        "context": "Bộ Giáo dục và Đào tạo công bố lịch thi tốt nghiệp trung học phổ thông năm nay vào tháng Sáu.",
        "question": "Bộ Giáo dục và Đào tạo công bố lịch thi vào tháng nào?",
        "answer_text": "tháng Sáu",
    },
    {
        "context": "Ngân hàng Nhà nước giữ nguyên lãi suất điều hành trong quý này, theo thông báo hôm thứ Hai.",
        "question": "Ai giữ nguyên lãi suất điều hành?",
        "answer_text": "Ngân hàng Nhà nước",
    },
    {
        "context": "Đội tuyển bóng đá quốc gia giành chiến thắng trong trận đấu giao hữu tối qua tại Hà Nội.",
        "question": "Trận đấu giao hữu diễn ra ở đâu?",
        "answer_text": "Hà Nội",
    },
    {
        "context": "Thành phố Hà Nội triển khai thêm tuyến xe buýt điện phục vụ người dân từ đầu năm sau.",
        "question": "Thành phố nào triển khai thêm tuyến xe buýt điện?",
        "answer_text": "Hà Nội",
    },
    {
        "context": "Các nhà khoa học công bố nghiên cứu mới về biến đổi khí hậu tại đồng bằng sông Cửu Long.",
        "question": "Nghiên cứu mới nói về hiện tượng gì?",
        "answer_text": "biến đổi khí hậu",
    },
    {
        "context": "Chính phủ ban hành nghị định hướng dẫn thi hành luật đất đai sửa đổi kể từ đầu tháng tới.",
        "question": "Ai ban hành nghị định hướng dẫn thi hành luật đất đai sửa đổi?",
        "answer_text": "Chính phủ",
    },
    {
        "context": "Bệnh viện trung ương tổ chức chương trình khám sức khỏe miễn phí cho người cao tuổi.",
        "question": "Chương trình khám sức khỏe miễn phí dành cho ai?",
        "answer_text": "người cao tuổi",
    },
    {
        "context": "Trường đại học quốc gia công bố kết quả tuyển sinh đợt hai vào cuối tuần này.",
        "question": "Trường đại học quốc gia công bố kết quả tuyển sinh đợt mấy?",
        "answer_text": "đợt hai",
    },
    {
        "context": "Sở Giao thông Vận tải thông báo kế hoạch sửa chữa cầu đường trong tháng tới.",
        "question": "Cơ quan nào thông báo kế hoạch sửa chữa cầu đường?",
        "answer_text": "Sở Giao thông Vận tải",
    },
    {
        # degenerate case: answer at the very end of the context, single word
        "context": "Tập đoàn công nghệ trong nước ra mắt sản phẩm phần mềm dịch thuật tiếng Việt.",
        "question": "Sản phẩm mới dịch ngôn ngữ nào?",
        "answer_text": "tiếng Việt",
    },
]


def _write(name: str, records: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{name}_stub.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for record in records:
            record = {**record, "stub_note": _STUB_NOTE}
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote {len(records)} rows to {out}")


def _resolve_viquad_answer_starts(records: list[dict]) -> list[dict]:
    resolved = []
    for r in records:
        start = r["context"].index(r["answer_text"])  # raises ValueError if not a substring
        resolved.append({**r, "answer_start": start})
    return resolved


def main() -> None:
    viquad = _resolve_viquad_answer_starts(VIQUAD)
    for r in viquad:
        found = r["context"][r["answer_start"]:r["answer_start"] + len(r["answer_text"])]
        assert found == r["answer_text"], f"answer_start mismatch for {r['question']!r}"

    _write("vlsp_ner", VLSP_NER)
    _write("uit_vsfc", UIT_VSFC)
    _write("viquad", viquad)


if __name__ == "__main__":
    main()
