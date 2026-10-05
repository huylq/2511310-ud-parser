# Thiết kế sơ bộ — UD Dependency Parsing

**Báo cáo tuần 1 — Project 2**
**Lê Quốc Huy - 2511310**  

## 1. Hướng tiếp cận được lựa chọn

Hướng Rule-Based được lựa chọn vì phù hợp với phạm vi dự án và cho phép triển khai từng bước từ các cấu trúc đơn giản.

Đã nghiên cứu, đọc Relation Inventory của UD v2 và tìm hiểu khái niệm treebank: tập câu được gán nhãn cấu trúc cú pháp. Bước tiếp theo là đối chiếu thêm các ví dụ tiếng Việt để xác định cách lựa chọn quan hệ trong từng ngữ cảnh.

Parser dự kiến nhận `SegmentedSentence` và trả về `DependencyParse`, giữ nguyên token đầu vào, bổ sung `head`, `deprel` và đặt `source="real"` cho kết quả. Mục tiêu ban đầu là tạo cây hợp lệ cho các câu đơn giản, sau đó bổ sung quy tắc cho sáu cấu trúc được yêu cầu.

Stub hiện tách theo khoảng trắng và gán mọi token là `upos="X"`, nên quy tắc không thể chỉ dựa vào POS. Cách sử dụng từ, vị trí token và ngữ cảnh để nhận diện cấu trúc cần được xác định trong tuần 2.

## 2. Kết quả tìm hiểu sáu cấu trúc

Trong các ví dụ dưới đây, ký hiệu `quan_hệ(head, dependent)` có nghĩa là từ thứ hai phụ thuộc vào từ thứ nhất. 

### 2.1. Loại từ: cái, con, chiếc, cuốn

Không thể chọn nhãn chỉ dựa vào việc một từ có nằm trong danh sách loại từ hay không. Cần xem ngữ cảnh và từ mà loại từ phụ thuộc vào.

Trong ví dụ VTB có cụm “một con đường”, `con` phụ thuộc vào `một` bằng `clf`, còn `một` phụ thuộc vào `đường` bằng `nummod`. Ở ví dụ “Con đường biển Đông…”, VTB dùng `clf:det` để gắn `Con` vào `đường`. Như vậy, VTB có sự phân biệt giữa các cách dùng loại từ, thay vì luôn gắn loại từ trực tiếp vào danh từ bằng cùng một nhãn. [VTB: clf](https://universaldependencies.org/treebanks/vi_vtb/vi_vtb-dep-clf.html), [VTB: clf:det](https://universaldependencies.org/treebanks/vi_vtb/vi_vtb-dep-clf-det.html).

**Hướng áp dụng:** Với mẫu số từ + loại từ + danh từ, quy tắc dự kiến theo cách gắn trong ví dụ “một con đường”. Với loại từ đứng trực tiếp trước danh từ, phương án là giữ cách gắn của `clf:det` và biểu diễn bằng nhãn cơ bản `clf`, vì tập nhãn đầu ra được quy định trong UD_DEPREL không bao gồm nhãn con `clf:det`.

**Nội dung cần nghiên cứu thêm:** Kiểm tra thêm `cái`, `chiếc`, `cuốn` và các trường hợp mà chúng được dùng như danh từ thông thường. Corpus có câu “Con mèo nhà tao nghịch banh quá trời luôn.” để đối chiếu, nhưng câu này chưa đủ kiểm tra mọi loại từ.

### 2.2. Đẳng lập: cc và conj

Trong biểu diễn UD cơ bản, thành phần đẳng lập đầu tiên làm head của cấu trúc, các thành phần tiếp theo phụ thuộc vào nó bằng `conj`. Liên từ phụ thuộc vào thành phần đẳng lập mà nó đi cùng bằng `cc`. Ví dụ VTB cũng thể hiện cách gắn này. [UD: conj](https://universaldependencies.org/u/dep/conj.html), [UD: cc](https://universaldependencies.org/u/dep/cc.html), [VTB: cc](https://universaldependencies.org/treebanks/vi_vtb/vi_vtb-dep-cc.html).

**Hướng áp dụng:** Với ví dụ tự đặt “Lan và Nam”, cách gắn dự kiến là `conj(Lan, Nam)` và `cc(Nam, và)`. Phạm vi triển khai ban đầu tập trung vào các cấu trúc có liên từ rõ ràng như `và`, `hoặc`.

Corpus có câu “Bộ Giáo dục và Đào tạo công bố lịch thi tốt nghiệp trung học phổ thông năm nay.” Đây là ví dụ để tìm hiểu phạm vi đẳng lập trong một tên tổ chức. Tuy nhiên, stub tách `Giáo dục` và `Đào tạo` thành nhiều token, nên cần chốt cách chọn head của mỗi cụm mà vẫn giữ nguyên đầu vào.

### 2.3. Chuỗi động từ: đi mua, chạy ra

UD có `compound:svc` cho serial verb constructions. Trong ví dụ VTB “Rồi chuyển về tỉnh.”, `về` phụ thuộc vào `chuyển` bằng `compound:svc`. Đây là căn cứ ban đầu cho hướng chọn động từ đứng trước làm head trong nhóm cấu trúc tương ứng. [UD: compound:svc](https://universaldependencies.org/u/dep/compound-svc.html), [VTB: compound:svc](https://universaldependencies.org/treebanks/vi_vtb/vi_vtb-dep-compound-svc.html).

**Hướng áp dụng:** Với trường hợp đã xác định là chuỗi động từ theo quy ước này, phương án sơ bộ là chọn động từ đầu làm head và biểu diễn quan hệ bằng nhãn cơ bản `compound`. Việc nhận diện cần phân biệt chuỗi động từ với bổ ngữ `xcomp` và cấu trúc chỉ hướng; hai động từ đứng cạnh nhau chưa đủ để xác định cấu trúc. [UD: xcomp](https://universaldependencies.org/u/dep/xcomp.html).

**Nội dung cần làm rõ:** Phân tích riêng cho `đi mua` và `chạy ra` chưa được chốt. Cần tìm thêm ví dụ VTB tương ứng trước khi viết quy tắc. Corpus có `đi học`, `đi chơi`, nhưng không có đúng hai cụm `đi mua`, `chạy ra`; các cụm hiện có là trường hợp cần xem xét, chưa phải bằng chứng chắc chắn về serial verbs.

### 2.4. Sở hữu với của

**Kết quả hiện tại:** Ví dụ VTB “…quyết tâm của nàng dâu…” gắn `nàng` vào `quyết tâm` bằng `nmod:poss`, còn `của` phụ thuộc vào `nàng` bằng `case`. Cách gán nhãn này cho thấy cần phân biệt quan hệ của người sở hữu với danh từ được sở hữu và quan hệ của riêng từ `của`. [VTB: nmod:poss](https://universaldependencies.org/treebanks/vi_vtb/vi_vtb-dep-nmod-poss.html), [UD: case](https://universaldependencies.org/u/dep/case.html).

**Hướng áp dụng:** Với ví dụ tự đặt “sách của Lan”, cách gắn dự kiến là `nmod(sách, Lan)` và `case(Lan, của)`. Nhãn `nmod` được dùng để biểu diễn nhãn con `nmod:poss` trong phạm vi nhãn của dự án.

**Khoảng trống dữ liệu:** Corpus hiện có không chứa cấu trúc sở hữu với từ `của`. Câu “Con mèo nhà tao…” có sở hữu không dùng `của`, nhưng không thay thế được ví dụ cho quy tắc trên. Tài liệu [PROVISIONAL.md](../../tests/fixtures/treebank/PROVISIONAL.md) cũng ghi nhận khoảng trống này.

**Nội dung cần làm rõ:** Chốt phạm vi xử lý sở hữu không có `của` và cách ghi nhận việc thiếu ví dụ fixture. Khoảng trống dữ liệu sẽ được ghi nhận trong thiết kế; fixture được giữ nguyên theo hợp đồng dự án.

### 2.5. Đề ngữ và thành phần đưa lên đầu câu

**Kết quả hiện tại:** Vị trí đầu câu không đủ để xác định một thành phần là chủ ngữ. UD dùng `dislocated` cho thành phần ngoại vi không đảm nhiệm các quan hệ ngữ pháp cốt lõi thông thường. Nếu thành phần mang tính đề ngữ vẫn là chủ ngữ, UD giữ `nsubj`. [UD: dislocated](https://universaldependencies.org/u/dep/dislocated.html).

**Hướng áp dụng:** Việc lựa chọn nhãn cần dựa trên vai trò của thành phần trong câu. Corpus có câu “Bộ phim tối qua coi hay ghê, mày xem chưa?”. Đây là ví dụ cần phân biệt chủ ngữ với đối tượng được đưa lên đầu câu. `PROVISIONAL.md` ghi nhận cách gán `obj` cho `Bộ_phim` trong fixture treebank, nhưng tài liệu này đang ở trạng thái chưa được giảng viên duyệt nên chỉ được dùng làm điểm đối chiếu.

**Nội dung cần làm rõ:** Quy tắc nhận diện tự động cho toàn bộ cấu trúc đề–thuyết chưa được chốt. Cần đối chiếu thêm [ví dụ dislocated của VTB](https://universaldependencies.org/treebanks/vi_vtb/vi_vtb-dep-dislocated.html) và phân biệt rõ ba trường hợp `nsubj`, `obj`, `dislocated`.

### 2.6. Tiểu từ cuối câu: à, nhé, đấy

**Kết quả hiện tại:** UD dùng `discourse` cho một số tiểu từ có chức năng diễn ngôn và gắn chúng vào head của đơn vị liên quan, thường là mệnh đề. VTB có ví dụ gắn `rồi` vào động từ `bỏ` bằng `discourse`. Ví dụ này là căn cứ về cách gắn, nhưng chưa đủ kết luận riêng cho cả `à`, `nhé`, `đấy`. [UD: discourse](https://universaldependencies.org/u/dep/discourse.html), [VTB: discourse](https://universaldependencies.org/treebanks/vi_vtb/vi_vtb-dep-discourse.html).

**Hướng áp dụng:** Khi một từ cuối câu được xác định là tiểu từ tình thái, cách gắn dự kiến là phụ thuộc vào head của mệnh đề tương ứng bằng `discourse`. Với câu nhiều mệnh đề, head được chọn theo mệnh đề mà tiểu từ tác động đến.

Corpus có câu “Mai đi học sớm nha, đừng trễ nữa đó.” để nghiên cứu các cách dùng tương tự với `nha`, `đó`; chưa có đúng các tiểu từ có dấu `à`, `nhé`, `đấy` trong nhóm ví dụ này. Dạng không dấu `a` chưa đủ làm bằng chứng chắc chắn cho tiểu từ `à`.

**Nội dung cần làm rõ:** Tìm thêm ví dụ cho ba tiểu từ được yêu cầu và phân biệt tiểu từ tình thái với từ chỉ định hoặc từ có chức năng khác.

## 3. Giới hạn nhãn của dự án

`UD_DEPREL` trong `src/vietnlp/interfaces/_common.py` chỉ có các nhãn cơ bản. Phương án dự kiến là biểu diễn `clf:det` bằng `clf`, `compound:svc` bằng `compound` và `nmod:poss` bằng `nmod`, đồng thời giữ cách chọn head của quy ước đang theo.

Đây là lựa chọn biểu diễn cho dự án; thông tin chi tiết của nhãn con sẽ bị giản lược khi chuyển về nhãn cơ bản. Phương án này cần được kiểm tra lại trước khi chốt thiết kế trong tuần 2. Tập nhãn trong interfaces được giữ nguyên.

## 4. Kế hoạch kiểm thử khi bắt đầu triển khai parser

Ở giai đoạn hiện tại, các quy tắc và kiến trúc parser vẫn đang được nghiên cứu. Tuần tiếp theo tập trung hoàn thiện thiết kế: xác định phạm vi xử lý sáu cấu trúc, cách sử dụng đầu vào có POS là `X`, tiêu chí chọn root và thứ tự ưu tiên quy tắc. Các trường hợp chưa đủ căn cứ cần được giới hạn phạm vi với lý do cụ thể trước khi triển khai.

Luồng xử lý dự kiến gồm chọn root, khởi tạo cây, áp dụng các nhóm quy tắc, xử lý những token chưa phân tích được và kiểm tra kết quả. Sau khi thiết kế được thống nhất, TDD sẽ được áp dụng từ khi bắt đầu khung parser: viết test cho từng hành vi trước khi bổ sung phần triển khai tương ứng.

Mỗi kết quả cần được kiểm tra bằng `validate_dependency_parse()` để xác nhận schema và `is_single_rooted_tree()` để xác nhận đúng một root, head trỏ tới token tồn tại và không có chu trình.

Phương án bảo đảm cấu trúc đang xem xét là khởi tạo đúng một root có `head=0`, `deprel="root"`, rồi gắn các token còn lại vào root bằng `dep` hoặc `punct` nếu nhận diện được dấu câu. Khi chưa xác định được vị ngữ, root dự phòng là token đầu không phải dấu câu; câu chỉ có dấu câu thì chọn token đầu. Các quy tắc không tạo thêm root; mỗi thay đổi head phải được kiểm tra để tránh tham chiếu không hợp lệ, tự trỏ hoặc tạo chu trình. Nếu kết quả cuối không hợp lệ, parser sẽ dựng lại cây dự phòng một root và kiểm tra lại. Cách gắn dự phòng bảo đảm cấu trúc, nhưng vẫn có thể chưa chính xác về ngôn ngữ.

Kiểm thử sẽ được mở rộng theo tiến độ triển khai:

- Ban đầu: kiểm tra cây hợp lệ trên câu đơn giản, cùng các trường hợp câu rỗng, câu một token và câu chỉ có dấu câu. Câu rỗng dự kiến báo `ValueError`.
- Cây sai cấu trúc: kiểm tra khả năng phát hiện thiếu root, nhiều root, head không tồn tại, tự trỏ và chu trình.
- Khi bổ sung từng nhóm quy tắc: thêm kiểm thử cách chọn head và nhãn cho cấu trúc tương ứng, bao gồm trường hợp mơ hồ.
- Khi mở rộng parser: kiểm tra cấu trúc trên toàn bộ corpus qua stub.

