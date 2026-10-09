# Vietnamese UD Dependency Parser

**Đồ án 02 — UD Dependency Parsing**

**Học viên: Lê Quốc Huy — 2511310**

Xây dựng parser theo Universal Dependencies v2 và quy ước UD_Vietnamese-VTB.
Hướng lựa chọn hiện tại là Rule-Based. Công việc đang ở giai đoạn nghiên cứu
và thiết kế; `ud_parser.py` chưa được triển khai.

## Báo cáo và yêu cầu

- [DESIGN.md](student-projects/02-ud-parsing/DESIGN.md): báo cáo nghiên cứu sáu cấu trúc và thiết kế sơ bộ.
- [DESIGN.docx](student-projects/02-ud-parsing/DESIGN.docx): bản Word của báo cáo.
- [spec.md](student-projects/02-ud-parsing/spec.md): mục tiêu và căn cứ ngôn ngữ.
- [plan.md](student-projects/02-ud-parsing/plan.md): kế hoạch thực hiện.
- [project.md](student-projects/02-ud-parsing/project.md): hợp đồng đầu vào, đầu ra và yêu cầu hoàn thành.

## Phạm vi repository

| Thành phần | Vai trò đối với đồ án 02 |
|---|---|
| `student-projects/02-ud-parsing/` | Yêu cầu, kế hoạch và bài làm của đồ án |
| `student-projects/01-word-seg-pos/spec.md`, `plan.md` | Tài liệu về đầu vào và ràng buộc được spec/plan của 02 tham chiếu |
| `src/vietnlp/interfaces/linguistics.py` và segmentation stub | Interface đầu vào từ đồ án 01 và đầu vào cố định để kiểm thử |
| `src/vietnlp/interfaces/ud.py`, `_common.py` và UD stub | Schema đầu ra, tập nhãn, validator, kiểm tra cây và ví dụ stub |
| `src/vietnlp/linguistics/` | Vị trí triển khai parser |
| `src/vietnlp/platform/agents/` | Chuỗi import cần để interface lấy các tập nhãn gốc từ `registry.py` |
| `tests/fixtures/corpus/` | Bộ câu, văn bản nguồn và danh sách từ nhiều âm tiết liên quan đầu vào |
| `tests/fixtures/treebank/` | Ví dụ UD để nghiên cứu; trạng thái PROVISIONAL được giữ nguyên |
| `tests/test_interfaces_*.py`, `tests/test_fixture_*.py` | Các kiểm tra kế thừa cho interface, stub và dữ liệu liên quan |
| `student-projects/_gate/` | Logic gate gốc và input loader của đồ án 02 |
| `.claude/agents/vietnamese-linguist.md` | Chuẩn ngôn ngữ được yêu cầu đọc trong đề bài |

Các mô-đun `registry`, `client`, `policy`, `budget`, `cache` được giữ vì
`interfaces/_common.py` import tập nhãn từ `registry`, và `registry` import
các mô-đun còn lại. Parser Rule-Based và các kiểm thử không gọi API.

Phần của đồ án 01 trong repo là tài liệu tham khảo, interface và stub.
Parser tiếp nhận `SegmentedSentence` nguyên trạng. Việc thay stub bằng đầu
ra thật của đồ án 01 được thực hiện khi giảng viên tích hợp sản phẩm cuối.

## Cài đặt và kiểm tra

Yêu cầu Python 3.11 trở lên. Trên Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest tests -q
```

Trên Linux hoặc macOS:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest tests -q
```

Các kiểm tra hiện có xác nhận bộ khung đầu vào, đầu ra và dữ liệu; chúng
chưa chứng minh parser thật đã hoàn thành. Kiểm thử parser sẽ bổ sung tại
`tests/test_linguistics_ud_parser*.py` theo tiến độ triển khai.

## Gate của đồ án

Khi triển khai parser, kiểm tra bằng:

```sh
python student-projects/_gate/gate.py 02-ud-parsing --base project-02-base
```

Gate gốc tạo môi trường tạm theo cấu trúc Linux/macOS. Trên Windows, sau khi
kiểm tra cài đặt sạch theo hướng dẫn trên, thêm `--skip-venv` để chạy các
bước còn lại. Bước cài đặt sạch trong gate cần chạy đầy đủ trên Linux/macOS
khi kiểm tra trước khi tích hợp.

`project-02-base` là mốc đóng gói repo riêng để kiểm tra các thay đổi tiếp
theo. Tag `curriculum-base` thuộc bộ khung môn học gốc. Khi tích hợp về repo
môn học, phân biệt các commit đóng gói này với các commit làm parser.
Gate chỉ hoàn tất khi có parser, kiểm thử riêng và tài liệu `TESTING.md`.

## Nguồn bộ khung

Yêu cầu, interface, stub, fixture và gate được kế thừa từ
[phunghx/VietnamesModel](https://github.com/phunghx/VietnamesModel).
Repository này được thu gọn cho phạm vi đồ án 02.
