"""Generates the committed synthetic fixture corpus.

Not scraped, not real user content -- every sentence here is written for this
repository, specifically so the pipeline has ~100 documents to test against
without network access or API spend (CLAUDE.md Working Agreements). Output is
deterministic: re-running this script reproduces byte-identical JSONL.

Run: python tests/fixtures/generate_fixture_corpus.py
"""
from __future__ import annotations

import hashlib
import itertools
import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

FETCHED_AT = datetime(2026, 8, 23, 0, 0, tzinfo=timezone.utc)

FORMAL = [
    "Bộ Giáo dục và Đào tạo công bố lịch thi tốt nghiệp trung học phổ thông năm nay.",
    "Ngân hàng Nhà nước giữ nguyên lãi suất điều hành trong quý này.",
    "Đội tuyển bóng đá quốc gia giành chiến thắng trong trận đấu giao hữu tối qua.",
    "Thành phố Hà Nội triển khai thêm tuyến xe buýt điện phục vụ người dân.",
    "Các nhà khoa học công bố nghiên cứu mới về biến đổi khí hậu tại đồng bằng sông Cửu Long.",
    "Chính phủ ban hành nghị định hướng dẫn thi hành luật đất đai sửa đổi.",
    "Tập đoàn công nghệ trong nước ra mắt sản phẩm phần mềm dịch thuật tiếng Việt.",
    "Bệnh viện trung ương tổ chức chương trình khám sức khỏe miễn phí cho người cao tuổi.",
    "Trường đại học quốc gia công bố kết quả tuyển sinh đợt hai.",
    "Sở Giao thông Vận tải thông báo kế hoạch sửa chữa cầu đường trong tháng tới.",
]

INFORMAL = [
    "Hôm nay trời đẹp quá, đi cà phê không?",
    "Tao vừa ăn phở xong, ngon dã man luôn.",
    "Mai đi học sớm nha, đừng trễ nữa đó.",
    "Bộ phim tối qua coi hay ghê, mày xem chưa?",
    "Cuối tuần này rảnh không, đi chơi Đà Lạt đi.",
    "Nay mưa to quá trời, chắc kẹt xe dữ lắm.",
    "Đói bụng ghê, kiếm gì ăn thôi mọi người ơi.",
    "Con mèo nhà tao nghịch banh quá trời luôn.",
    "Bài tập cô giao khó ghê, ai làm xong chưa vậy.",
    "Chiều nay đá bóng không, thiếu người quá.",
]

TEENCODE = [
    "Hnay ranh ko, di choi di :))",
    "T thay bit r, hay v.",
    "Mai hoc som nha, dg quen do.",
    "Phim nay hay v, coi chua a.",
    "Doi bung wa, an gi bh.",
    "Ny t bao dang gian, hix.",
    "Trg hom nay dong ng kinh khung.",
    "Bai kt kho v troi, lam sao lam het.",
    "Cuoi tuan ranh k, di chill k.",
    "Mua to v troi oi, ket xe cmnr.",
]

NON_DIACRITIC = [
    "Bo Giao duc va Dao tao cong bo lich thi tot nghiep trung hoc pho thong nam nay.",
    "Ngan hang Nha nuoc giu nguyen lai suat dieu hanh trong quy nay.",
    "Hom nay troi dep qua, di ca phe khong?",
    "Tao vua an pho xong, ngon da man luon.",
    "Mai di hoc som nha, dung tre nua do.",
    "Doi tuyen bong da quoc gia gianh chien thang trong tran dau giao huu toi qua.",
    "Cuoi tuan nay ranh khong, di choi Da Lat di.",
    "Thanh pho Ha Noi trien khai them tuyen xe buyt dien phuc vu nguoi dan.",
    "Nay mua to qua troi, chac ket xe du lam.",
    "Truong dai hoc quoc gia cong bo ket qua tuyen sinh dot hai.",
]

_REGISTER_POOLS = {
    "formal": FORMAL, "informal": INFORMAL, "teencode": TEENCODE, "non_diacritic": NON_DIACRITIC,
}
_SOURCE_ID = {
    "formal": "fixture-formal", "informal": "fixture-informal",
    "teencode": "fixture-teencode", "non_diacritic": "fixture-nondiacritic",
}


def _documents_for(register: str, pool: list[str]) -> list[dict]:
    docs: list[tuple[int, str]] = [(i, sentence) for i, sentence in enumerate(pool)]
    pairs = itertools.islice(itertools.combinations(range(len(pool)), 2), 15)
    docs += [(10 + i, f"{pool[a]} {pool[b]}") for i, (a, b) in enumerate(pairs)]

    records = []
    for idx, text in docs:
        # Normalize to NFC to ensure test_text_is_nfc_normalized passes
        text = unicodedata.normalize("NFC", text)
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        records.append({
            "content_hash": h,
            "source_id": _SOURCE_ID[register],
            "url": f"https://fixture.local/{_SOURCE_ID[register]}/{idx:03d}",
            "fetched_at": FETCHED_AT.isoformat(),
            "http_status": 200,
            "robots_decision": "allowed",
            "content_type": "text/plain; charset=utf-8",
            "text": text,
            "license": "synthetic-fixture",
            "register": register,
        })
    return records


def build_corpus() -> list[dict]:
    records = []
    for register, pool in _REGISTER_POOLS.items():
        records.extend(_documents_for(register, pool))
    return records


def main() -> None:
    records = build_corpus()
    assert len(records) == 100, f"expected 100 fixture documents, got {len(records)}"
    out = Path(__file__).parent / "corpus" / "fixture_corpus.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote {len(records)} records to {out}")


if __name__ == "__main__":
    main()
