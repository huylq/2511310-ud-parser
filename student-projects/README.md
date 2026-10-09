# Project 2 — UD Dependency Parsing

Đồ án thực hiện: **02 — UD Dependency Parsing**, học viên **Lê Quốc Huy — 2511310**.

- [02-ud-parsing](02-ud-parsing/README.md): yêu cầu, kế hoạch, thiết kế và báo cáo của đồ án.
- [01-word-seg-pos](01-word-seg-pos/README.md): hai tài liệu tham khảo về đầu vào và ràng buộc được tài liệu 02 dẫn chiếu.
- [_gate](_gate/README.md): công cụ kiểm tra dùng cho đồ án 02.

## Input and output contracts

Đầu vào là `interfaces.linguistics.SegmentedSentence`, được tạo bằng
`interfaces.stubs.linguistics_stub.stub_segment()` khi phát triển và chấm bài.
Stub tách theo khoảng trắng và gán POS là `X`. Khi tích hợp sản phẩm cuối,
giảng viên có thể thay stub bằng bộ tách từ và POS thật của đồ án 01,
vẫn giữ nguyên interface.

Đầu ra là `interfaces.ud.DependencyParse`, với `source="real"`, nhãn thuộc
`UD_DEPREL`, đúng một root, các head hợp lệ và không có chu trình.

## Interface change control

Các interface, fixture và logic gate kế thừa từ bộ khung môn học được giữ
nguyên. Nếu phát hiện lỗi trong hợp đồng, báo cho giảng viên để sửa tại nguồn
và đồng bộ phiên bản; không tự thay đổi schema hoặc validator để bài làm vượt
qua kiểm tra.

## Fixture data status

`tests/fixtures/corpus/fixture_sentences.jsonl` là bộ câu cố định để phát triển
và kiểm thử parser. `fixture_corpus.jsonl` lưu các văn bản nguồn để đối chiếu
sentence ID, nội dung và vị trí câu. `known_compounds.txt` là tài liệu hỗ trợ
nhận diện từ nhiều âm tiết khi tìm hiểu đầu vào.

Các ví dụ trong `tests/fixtures/treebank/` vẫn ở trạng thái **PROVISIONAL**;
xem [PROVISIONAL.md](../tests/fixtures/treebank/PROVISIONAL.md). Chúng hỗ trợ
nghiên cứu cách gắn quan hệ, chưa phải dữ liệu gold đã được giảng viên duyệt.

## Checking progress

Chạy các kiểm tra kế thừa: `python -m pytest tests -q`.

Khi bắt đầu triển khai parser, chạy gate với mốc cấu trúc của repo riêng:

```sh
python student-projects/_gate/gate.py 02-ud-parsing --base project-02-base
```

Mốc này dùng để kiểm tra thay đổi tiếp theo trong phạm vi parser. Bộ khung gốc
của môn học vẫn dùng `curriculum-base`; các commit thu gọn repository là thay
đổi đóng gói, cần phân biệt với các commit triển khai parser khi tích hợp lại.
Gate chưa thể PASS khi parser và các kiểm thử riêng chưa được triển khai.

## Source

Yêu cầu, interface, stub, dữ liệu và gate được kế thừa từ
[VietnamesModel](https://github.com/phunghx/VietnamesModel).
