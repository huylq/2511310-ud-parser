# Tài liệu đầu vào từ đồ án 01

Thư mục này giữ hai tài liệu gốc mà đồ án 02 dẫn chiếu:

- [spec.md](spec.md): ví dụ đặc tả đầy đủ và mô tả sản phẩm tách từ, POS.
- [plan.md](plan.md): ràng buộc chung được kế hoạch đồ án 02 tham chiếu.

Đầu vào phục vụ đồ án 02 nằm tại
`src/vietnlp/interfaces/linguistics.py` và
`src/vietnlp/interfaces/stubs/linguistics_stub.py`.
Parser được phát triển và chấm trên stub; khi tích hợp sản phẩm cuối,
giảng viên có thể thay bằng đầu ra thật của đồ án 01 cùng interface.

Hai tài liệu được giữ từ bộ khung
[VietnamesModel](https://github.com/phunghx/VietnamesModel), không phải
bài triển khai đồ án 01 trong repository này.
