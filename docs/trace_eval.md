# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Đoàn Duy Bách  
> **Mã Sinh Viên / Mã Học viên:** 2A202602515  
> **Chủ đề Lựa chọn:** Gợi ý 1.1 — Trợ lý Học vụ & Tra cứu Lịch thi VinUni (Tra cứu điểm GPA/hồ sơ học vụ và đặt lịch tư vấn học vụ với Cố vấn)  

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | 4 / 5 | Để đặt lịch tư vấn học vụ đúng người, Agent thường phải suy luận qua ít nhất 2 bước nối tiếp: (1) tra cứu hồ sơ sinh viên (`academic_query`) để biết cố vấn phụ trách, rồi (2) mới phát sinh hành động đặt lịch (`schedule_appointment`) với đúng tên cố vấn vừa xác định — không thể trả lời trong 1 bước suy luận đơn lẻ. |
| **2. Tool Interaction** | 5 / 5 | Bài toán bắt buộc kết nối MCP Server chuẩn JSON-RPC với 2 Tool riêng biệt (`academic_query` tra cứu CSDL học vụ mô phỏng, `schedule_appointment` tạo booking), đúng yêu cầu "1 tool tra cứu + 1 tool hành động", Agent không thể tự trả lời chính xác nếu chỉ dựa vào kiến thức nền của LLM. |
| **3. Dynamic Decision** | 4 / 5 | Hành động ở bước sau phụ thuộc trực tiếp vào Observation của bước trước: nếu tra cứu trả về `NOT_FOUND` thì Agent phải dừng lại và phản hồi lịch sự thay vì tiếp tục đặt lịch; nếu `SUCCESS` thì mới dùng tên cố vấn lấy được để gọi `schedule_appointment` — quyết định rẽ nhánh rõ ràng dựa trên kết quả quan sát thực tế. |
| **4. Long Horizon Goal** | 3 / 5 | Trong phạm vi một phiên hỏi-đáp, Agent cần giữ nguyên mục tiêu ban đầu (đặt lịch cho đúng sinh viên) xuyên suốt vòng lặp ReAct nhiều bước (tra cứu → tổng hợp → đặt lịch), tuy nhiên mục tiêu này không kéo dài qua nhiều phiên/nhiều ngày nên chưa đạt mức tối đa của một Long Horizon Goal thực sự. |
| **TỔNG ĐIỂM AGENTIC FIT** | **16 / 20** | *Tổng điểm 16/20 > 12/20 → Bài toán RẤT PHÙ HỢP để triển khai dưới dạng Agentic System (ReAct Agent + MCP Server) thay vì Chatbot Baseline đơn thuần.* |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Mở tệp `.env` điền `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`) để kết nối LLM thật trước khi thực thi `python src/app.py --all`. Bài nộp chỉ dùng Mock Offline Provider sẽ không đạt điểm nghiệm thực tế.

**Cấu hình LLM thật đã dùng:** Groq API (endpoint tương thích OpenAI `https://api.groq.com/openai/v1`), mô hình `openai/gpt-oss-120b`, chọn qua `LLM_PROVIDER=groq` + `GROQ_API_KEY` trong `.env`. Provider được bổ sung là lớp `GroqProvider` trong `src/providers.py` (kế thừa `OpenAIProvider`, dùng Native Tool Calling của OpenAI SDK). Log chạy xác nhận `🔌 LLM Provider: GroqProvider`, **0 lần fallback về Mock**, và mọi sự kiện trong trace đều ghi `"model": "openai/gpt-oss-120b"`.

**Cơ chế vòng lặp ReAct (`run_react_agent()` trong `src/app.py`):** Agent giữ một lịch sử hội thoại `messages`. Mỗi lượt, LLM nhận toàn bộ lịch sử cùng Tool Schemas:
- `type == "text"` → ghi `FINAL_ANSWER` và dừng vòng lặp.
- `type == "tool_call"` → gọi MCP Server (`call_tool` → `dispatch_tool_call`), ghi `TOOL_EXECUTION`, rồi **nạp Action (`tool_calls`) + Observation (message role `tool`) vào lịch sử** để LLM suy luận tiếp ở lượt kế tiếp.
- Hết `MAX_ITERATIONS = 5` mà chưa có câu trả lời → dừng an toàn.

Trường `thought` lấy từ chuỗi suy luận (`reasoning`) mà `gpt-oss-120b` trả về qua Groq. `latency_ms` được đo thật cho từng bước (bước Tool tách thêm `llm_latency_ms` và `tool_latency_ms`).

Trích xuất log tiêu biểu (TC04 — suy luận đa bước) từ file `docs/trace_waterfall.json` sinh ra bởi lệnh `python src/app.py --all` trên Groq API thật:

```json
[
  {
    "step": 1,
    "query": "Sinh viên SV2026002 muốn đặt lịch hẹn tư vấn học vụ vào 09:00 ngày 20/09/2026 với đúng cố vấn học tập đang phụ trách mình, hãy tra cứu cố vấn phù hợp rồi giúp đặt lịch.",
    "action_type": "TOOL_EXECUTION",
    "model": "openai/gpt-oss-120b",
    "thought": "We need to first query academic info for student SV2026002 to get advisor name. Then schedule appointment with that advisor at given datetime. Follow ReAct.",
    "tool_name": "academic_query",
    "arguments": { "student_id": "SV2026002" },
    "observation": {
      "status": "SUCCESS",
      "student_id": "SV2026002",
      "data": {
        "full_name": "Trần Thị Bình",
        "class": "AI-K4",
        "gpa": 3.6,
        "email": "binh.tt@vinuni.edu.vn",
        "status": "Đang học",
        "advisor": "TS. Lê Thị B"
      }
    },
    "latency_ms": 908.04,
    "llm_latency_ms": 907.99,
    "tool_latency_ms": 0.05
  },
  {
    "step": 2,
    "action_type": "TOOL_EXECUTION",
    "model": "openai/gpt-oss-120b",
    "thought": "We have student data, advisor is \"TS. Lê Thị B\". Need to schedule appointment at 09:00 20/09/2026 with that advisor.\n\nProceed to schedule_appointment tool.",
    "tool_name": "schedule_appointment",
    "arguments": {
      "advisor_name": "TS. Lê Thị B",
      "datetime_str": "09:00 20/09/2026",
      "student_id": "SV2026002"
    },
    "observation": {
      "status": "SUCCESS",
      "booking_id": "BK-SV2026002-99",
      "student_id": "SV2026002",
      "datetime": "09:00 20/09/2026",
      "advisor": "TS. Lê Thị B",
      "message": "Đặt lịch thành công cho sinh viên SV2026002 với TS. Lê Thị B vào lúc 09:00 20/09/2026."
    },
    "latency_ms": 878.96,
    "llm_latency_ms": 878.91,
    "tool_latency_ms": 0.05
  },
  {
    "step": 3,
    "action_type": "FINAL_ANSWER",
    "model": "openai/gpt-oss-120b",
    "output": "Xin chào bạn! 🎓\n\n✅ Đã tra cứu thông tin sinh viên **SV2026002** và xác nhận cố vấn học tập phụ trách là **TS. Lê Thị B**.  \n✅ Đã đặt lịch hẹn tư vấn học vụ với TS. Lê Thị B vào **09:00 ngày 20/09/2026**.\n\n**Mã đặt lịch:** `BK-SV2026002-99`\n\n...",
    "latency_ms": 900.16
  }
]
```
*(Đã lược bớt trường `query` lặp lại ở step 2–3 và phần cuối của `output`; bản đầy đủ nằm trong `docs/trace_waterfall.json`.)*

**Bảng tổng hợp Waterfall Trace (10 sự kiện):**

| Test Case | Hành vi kỳ vọng | Chuỗi hành động thực tế của Agent (Groq) | Tổng `latency_ms` | Kết quả |
| :--- | :--- | :--- | :---: | :---: |
| TC01 — direct_query | Trả lời trực tiếp, không gọi Tool | `FINAL_ANSWER` trực tiếp, không gọi Tool | 5106.67 | ✅ Đạt |
| TC02 — single_tool_query | Gọi `academic_query(SV2026001)` | `academic_query({"student_id": "SV2026001"})` → `SUCCESS` → `FINAL_ANSWER` do LLM tổng hợp | 1832.53 | ✅ Đạt |
| TC03 — appointment_booking | Gọi `schedule_appointment` đúng tham số | `schedule_appointment` đủ 3 tham số → `SUCCESS` (`BK-SV2026001-99`) → `FINAL_ANSWER` | 1573.05 | ✅ Đạt |
| TC04 — multi_step_reasoning | Tra cứu cố vấn → đặt lịch | `academic_query(SV2026002)` → cố vấn `TS. Lê Thị B` → `schedule_appointment(TS. Lê Thị B, 09:00 20/09/2026)` → `FINAL_ANSWER` | 2687.16 | ✅ Đạt (3 bước) |
| TC05 — edge_case_handling | Nhận `NOT_FOUND`, không bịa dữ liệu | `academic_query(SV9999999)` → `NOT_FOUND` → xin lỗi, đề nghị kiểm tra lại mã sinh viên | 1571.38 | ✅ Đạt |

**Nhận xét quan sát (Observability):**
- **TC04 chứng minh vòng lặp ReAct nhiều bước hoạt động:** Observation của `academic_query` được nạp lại cho LLM, và LLM dùng đúng tên cố vấn vừa tra được làm tham số `advisor_name` cho `schedule_appointment` (xem `thought` ở step 2). Đây là quyết định động mà Chatbot Baseline không làm được.
- Độ trễ trung bình của bước LLM quyết định gọi Tool: **≈ 826 ms** (5 lượt). Bước LLM tổng hợp Final Answer sau Observation: **≈ 883 ms** (4 lượt). Thời gian thực thi Tool qua MCP Server không đáng kể (**≈ 0.05 ms**) vì dữ liệu là CSDL mô phỏng trong bộ nhớ. Nút thắt độ trễ nằm hoàn toàn ở LLM.
- TC01 chậm nhất (5106.67 ms) do mô hình sinh câu trả lời văn bản dài. Nội dung được trả lời từ kiến thức nền của mô hình (ví dụ số tín chỉ tốt nghiệp, tỉ lệ điểm danh), không có Tool quy chế để đối chiếu nên có nguy cơ hallucination. Hướng cải tiến: bổ sung Tool tra cứu quy chế từ nguồn chính thức.
- Ở câu trả lời cuối của TC04, mô hình thêm câu "Bạn sẽ nhận được email xác nhận và nhắc nhở trước ngày hẹn". Thông tin này **không có trong Observation**, là một ví dụ nhỏ về việc LLM thêm nội dung ngoài dữ liệu Tool dù System Prompt đã cấm. Hướng cải tiến: siết System Prompt hoặc để Tool trả về đầy đủ thông tin thông báo.
- Bước Final Answer của TC04 không có chuỗi `reasoning` từ API nên `thought` dùng mô tả mặc định của Provider.

**Kiểm thử chế độ đàm thoại trực tiếp (`python src/app.py --interactive`) trên Groq API:**

| Câu hỏi | Hành động của Agent | Kết quả |
| :--- | :--- | :---: |
| "Quy chế học vụ VinUni yêu cầu bao nhiêu tín chỉ?" | Trả lời trực tiếp, không gọi Tool | ✅ |
| "Hãy tra cứu thông tin học vụ của sinh viên SV2026001" | `academic_query({"student_id": "SV2026001"})` → `SUCCESS` | ✅ |
| "Đặt lịch hẹn tư vấn cho SV2026001 với PGS.TS Nguyễn Văn A vào 14:00 ngày 15/09/2026" | `schedule_appointment` với đủ 3 tham số → `SUCCESS` | ✅ |
| `exit` | Thoát phiên chat bình thường | ✅ |

*(Phiên interactive được chạy trước khi nâng cấp vòng lặp ReAct nhiều bước. Chế độ `--interactive` ghi đè `docs/trace_waterfall.json` sau mỗi câu hỏi, nên trace nộp bài là trace của lần chạy `--all` cuối cùng.)*

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [x] Đã điền API Key thật trong `.env` và xác nhận Agent chạy mượt mà trên LLM API thật (**Groq — `openai/gpt-oss-120b`**, 0 lần fallback Mock).
- [x] Đã thử nghiệm thành công chế độ đàm thoại trực tiếp `python src/app.py --interactive` (3/3 câu hỏi phản hồi đúng).
- **Tổng số Test Cases đã chạy thành công:** 5 / 5 test cases thực thi hoàn tất trên API thật; **5 / 5 đạt đúng hành vi kỳ vọng**, bao gồm TC04 suy luận đa bước (tra cứu → đặt lịch).
- **Số lượt gọi Tool qua MCP Server chính xác:** 5 lượt trong test suite (TC02: 1, TC03: 1, TC04: 2, TC05: 1), tất cả đúng tên Tool và đúng tham số; TC01 không gọi Tool đúng như kỳ vọng.
- **Kết quả đẩy Repo nộp bài:** [x] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
