# prompt = """
# Bạn là một chuyên gia xếp hạng tài liệu (Reranking System). Nhiệm vụ của bạn là phân tích mức độ liên quan giữa Câu hỏi của người dùng và Danh sách tài liệu được cung cấp và trả về danh sách vị trí các tài liệu theo thứ tự ưu tiên giảm dần về độ liên quan.

# Lưu ý:
# 1. Chỉ sử dụng chỉ số (index) bắt đầu từ 0 để đại diện cho tài liệu.
# 2. Tuyệt đối KHÔNG trả về chỉ số lớn hơn hoặc bằng {num_docs}.
# 3. Trả về tối đa {top_k} chỉ số liên quan nhất. Nếu có ít hơn {top_k} tài liệu liên quan, chỉ trả về bấy nhiêu.

# Câu hỏi: {question}
# Danh sách tài liệu (Số lượng: {num_docs}):
# {documents}

# Bạn PHẢI trả về một danh sách chỉ số duy nhất theo đúng cấu trúc dưới đây. Không giải thích, không thêm văn bản thừa.
# """

prompt = """
Bạn là một chuyên gia xếp hạng tài liệu (Reranking System). Nhiệm vụ của bạn là phân tích mức độ liên quan giữa Câu hỏi của người dùng và Danh sách tài liệu được cung cấp và trả về danh sách vị trí các tài liệu theo thứ tự ưu tiên giảm dần về độ liên quan.

Lưu ý:
1. Chỉ sử dụng chỉ số (index) bắt đầu từ 0 để đại diện cho tài liệu.
2. Tuyệt đối KHÔNG trả về chỉ số lớn hơn hoặc bằng {num_docs}.
3. Loại bỏ các tài liệu không phù hợp với câu hỏi, ngoài ra bạn có thể giữ nếu thấy vẫn phù hợp.

Câu hỏi: {question}
Danh sách tài liệu (Số lượng: {num_docs}):
{documents}

Bạn PHẢI trả về một danh sách chỉ số duy nhất theo đúng cấu trúc dưới đây. Không giải thích, không thêm văn bản thừa.
"""