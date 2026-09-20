# BTVN#1: Issue Triage Mini-App (LLM-Powered App)

> **Môn học:** SE111 — Agentic AI  
> **Khoa:** Kỹ thuật Phần mềm — Trường Đại học Công nghệ Thông tin (UIT), ĐHQG-HCM.

---

## 📌 Giới thiệu tổng quan

**Issue Triage Mini-App** là một ứng dụng minh họa đầy đủ các nguyên lý cốt lõi của một **LLM-Powered App** trong bài toán tự động hóa sàng lọc, phân loại sự cố phần mềm (Issue Triage):
* **Đọc hiểu & phân loại**: Tiếp nhận mô tả lỗi phần mềm từ người dùng hoặc hệ thống giám sát.
* **Prompt Engineering**: Áp dụng **Prompt Template** với các thẻ XML để phân tách ranh giới rõ ràng giữa chỉ thị (`<task>`) và dữ liệu đầu vào (`<input>`).
* **Function Calling (Tool Use)**: Khai báo công cụ `get_component_owner` cho phép model đề xuất hành động tra cứu team chịu trách nhiệm; ứng dụng kiểm soát và thực thi cục bộ.
* **Ghi vết chu trình 4 bước (Trace)**:
  $$\text{tool\_call} \longrightarrow \text{application executes} \longrightarrow \text{tool\_result} \longrightarrow \text{final response}$$
* **Structured Output & Schema Contract**: Ép kiểu dữ liệu trả về theo mô hình **Pydantic `IssueTriage`** (bao gồm các ràng buộc `status`, `severity`, `component`, `needs_urgent_response`, `reason`).
* **Application Validation**: Tầng ứng dụng trực tiếp kiểm tra tính hợp lệ về mặt nghiệp vụ trước khi bàn giao dữ liệu.
* **Dự toán chi phí**: Báo cáo đo token và ước tính ngân sách vận hành cho quy mô 10.000 sự cố/tháng.

---

## 🏗️ Cấu trúc thư mục

```text
Demo Issue Triage-20260920/
├── .env.example              # Mẫu cấu hình môi trường (API Key, Base URL, Model)
├── requirements.txt          # Danh sách thư viện phụ thuộc
├── demo_common.py            # Module tiện ích nạp môi trường và khởi tạo OpenAI client
├── triage_workflow.py        # [CORE] Khai báo schema Pydantic, template, tool và workflow chính
├── 00_minimal_triage.py      # Demo 0: Kiểm tra kết nối API với output dạng tự do (prose)
├── 01_measure_tokens.py      # Demo 1: Đo lượng token EN vs VI (chạy offline với tiktoken)
├── 02_structured_output.py   # Demo 2: So sánh Prompt-only JSON và Pydantic Constrained Output
├── 03_function_calling.py    # Demo 3: Giao diện CLI thực thi luồng Function Calling và in 4 bước Trace
├── 04_streamlit_triage.py    # Demo 4: Giao diện Web tương tác trực quan bằng Streamlit
├── demo-guide.html           # Tài liệu hướng dẫn thực hành của giảng viên
├── docs/
│   └── uoc_tinh_chi_phi.html # Báo cáo ước tính chi phí cho 10.000 issue/tháng (Slide 69)
└── README.md                 # Tài liệu hướng dẫn chi tiết dự án
```

---

## ⚙️ Cài đặt và Chuẩn bị môi trường

### 1. Yêu cầu hệ thống
* **Python**: Phiên bản 3.10 trở lên.
* **Hệ điều hành**: Windows / macOS / Linux.

### 2. Thiết lập môi trường ảo và cài đặt thư viện

Mở Terminal tại thư mục dự án và thực hiện các lệnh sau:

```powershell
# 1. Tạo môi trường ảo (virtual environment)
python -m venv .venv

# 2. Kích hoạt môi trường ảo
# Trên Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Trên macOS / Linux:
# source .venv/bin/activate

# 3. Cài đặt các gói thư viện phụ thuộc
pip install -r requirements.txt
```

*(Mẹo trên Windows: Nếu gặp lỗi chặn script khi kích hoạt venv, chạy lệnh: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` rồi kích hoạt lại).*

### 3. Cấu hình biến môi trường (`.env`)

Sao chép file mẫu `.env.example` thành `.env`:

```powershell
copy .env.example .env
```

Mở file `.env` và điền cấu hình API của bạn:

* **Sử dụng Google Gemini API (Khuyên dùng - Miễn phí):**
  ```env
  OPENAI_API_KEY=AIzaSy...
  OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
  OPENAI_MODEL=gemini-2.5-flash
  ```

* **Sử dụng OpenAI API:**
  ```env
  OPENAI_API_KEY=sk-proj-...
  OPENAI_BASE_URL=https://api.openai.com/v1
  OPENAI_MODEL=gpt-4o-mini
  ```

> ⚠️ **Lưu ý bảo mật:** Tuyệt đối không commit file `.env` chứa API key thật lên Git hoặc nộp trong file nén Google Drive.

---

## 🚀 Hướng dẫn Chạy ứng dụng

### 1. Chạy Demo dòng lệnh CLI (In đầy đủ 4 bước Trace)

```powershell
python 03_function_calling.py
```

Bạn cũng có thể truyền mô tả lỗi tùy chỉnh thông qua tham số `--issue`:
```powershell
python 03_function_calling.py --issue "API giỏ hàng trả lỗi HTTP 502 Bad Gateway từ 10:00."
```

**Kết quả màn hình sẽ in ra:**
1. `=== 1. Model đề xuất tool call ===`: Model gửi yêu cầu gọi `get_component_owner({"component": "payment"})`.
2. `=== 2. Application thực thi ===`: Ứng dụng tra cứu nội bộ ra owner `'checkout-platform'`.
3. `=== 3. Tool result quay lại model ===`: Kết quả trả về cho LLM.
4. `=== 4. Final response (Structured IssueTriage) ===`: Đối tượng Pydantic `IssueTriage` chuẩn cấu trúc JSON.

---

### 2. Chạy Giao diện Web tương tác bằng Streamlit

```powershell
streamlit run 04_streamlit_triage.py
```

* Trình duyệt sẽ mở tại địa chỉ: `http://localhost:8501`.
* Giao diện cho phép nhập mô tả sự cố, bấm **Phân loại issue** và hiển thị:
  - Các thẻ chỉ số: Mức độ nghiêm trọng (`P0`-`P3`), Trạng thái, Cờ On-call khẩn cấp.
  - Hộp mở rộng (Expander) hiển thị chi tiết Trace Function Calling.
  - JSON phân loại `IssueTriage` và lý do trích xuất.

*(Nhấn `Ctrl + C` tại Terminal để dừng server Streamlit).*

---

### 3. Đo Token thực tế

```powershell
python 01_measure_tokens.py
```
So sánh số lượng token giữa tiếng Anh và tiếng Việt qua 2 bộ mã hóa `cl100k_base` và `o200k_base`.

---

### 4. Xem Báo cáo Ước tính Chi phí vận hành

Mở file sau trực tiếp bằng bất kỳ trình duyệt nào (Chrome, Edge):
```text
docs/uoc_tinh_chi_phi.html
```

**Tóm tắt dự toán:**
* **Quy mô:** 10.000 issue/tháng.
* **Tiêu thụ trung bình:** ~705 tokens / issue (Input: 615 tokens, Output: 90 tokens).
* **Chi phí ước tính:**
  - **Gemini 2.5 Flash:** ~$0.73 / tháng (~18.600 VNĐ / tháng).
  - **GPT-4o-mini:** ~$1.46 / tháng (~37.200 VNĐ / tháng).

---

## 📋 Checklist Yêu cầu BTVN#1

- [x] Nhận mô tả issue phần mềm (CLI `--issue` hoặc form Streamlit).
- [x] Dùng Prompt Template phân tách rõ ràng `<task>` (instruction) và `<input>` (data).
- [x] Trả về cấu trúc `IssueTriage` bằng Pydantic model (`status`, `severity`, `component`, `needs_urgent_response`, `reason`).
- [x] Validate output ở phía Application (`validate_application_rules`).
- [x] Khai báo tool đơn giản (`get_component_owner`).
- [x] In trace đầy đủ: `tool_call -> application executes -> tool_result -> final response`.
- [x] Tạo tài liệu ước tính chi phí `docs/uoc_tinh_chi_phi.html` cho 10.000 issue/tháng.
