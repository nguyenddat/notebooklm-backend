prompt = """MÔ TẢ hình ảnh sao cho người đọc tài liệu, ngay cả khi không nhìn thấy hình, vẫn có thể hiểu hình ảnh đó đang minh họa cho nội dung gì trong tài liệu hướng dẫn.

ĐẦU VÀO:
- Hình ảnh đầu tiên: hình ảnh CẦN ĐƯỢC MÔ TẢ (ảnh chụp màn hình, ảnh minh họa thao tác, sơ đồ, biểu đồ…).
- Hình ảnh thứ hai (nếu có): hình ảnh TOÀN TRANG của tài liệu hoặc giao diện, dùng CHỈ để hiểu bối cảnh chung của hình ảnh đầu tiên.

NGUYÊN TẮC MÔ TẢ:
1. Mô tả trung thực những gì NHÌN THẤY trong hình ảnh.
2. Ngôn ngữ:
   - Trung lập, mang tính tài liệu
   - Không dùng ngôi thứ nhất
3. Dựa vào nội dung của hình ảnh thứ 2 để hiểu bối cảnh, mô tả hình ảnh đầu tiên dưới vai người dùng sử dụng phần mềm. Ví dụ: Bước 1: Vào giao diện chính, bạn sẽ thấy...; Bước 2: Sau khi điền thông tin, vui lòng ấn Next để đăng nhập,...

Chỉ trả về JSON hợp lệ. Không thêm bất kỳ nội dung nào khác: 
"""