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

**Cấu hình LLM thật đã dùng:** Groq API (endpoint tương thích OpenAI `https://api.groq.com/openai/v1`), mô hình `openai/gpt-oss-120b`, chọn qua `LLM_PROVIDER=groq` + `GROQ_API_KEY` trong `.env`. Provider được bổ sung là lớp `GroqProvider` trong `src/providers.py` (kế thừa `OpenAIProvider`, dùng Native Tool Calling của OpenAI SDK). Log chạy xác nhận `🔌 LLM Provider: GroqProvider` và **0 lần fallback về Mock**.

Trích xuất log tiêu biểu (TC03 — đặt lịch hẹn) từ file `docs/trace_waterfall.json` sinh ra bởi lệnh `python src/app.py --all` trên Groq API thật:

```json
[
  {
    "step": 1,
    "query": "Hãy đặt lịch hẹn tư vấn học vụ cho sinh viên SV2026001 với cố vấn PGS.TS Nguyễn Văn A vào lúc 14:00 ngày 15/09/2026.",
    "action_type": "TOOL_EXECUTION",
    "tool_name": "schedule_appointment",
    "arguments": {
      "advisor_name": "PGS.TS Nguyễn Văn A",
      "datetime_str": "14:00 15/09/2026",
      "student_id": "SV2026001"
    },
    "observation": {
      "status": "SUCCESS",
      "booking_id": "BK-SV2026001-99",
      "student_id": "SV2026001",
      "datetime": "14:00 15/09/2026",
      "advisor": "PGS.TS Nguyễn Văn A",
      "message": "Đặt lịch thành công cho sinh viên SV2026001 với PGS.TS Nguyễn Văn A vào lúc 14:00 15/09/2026."
    },
    "latency_ms": 1042.64
  },
  {
    "step": 2,
    "query": "Hãy đặt lịch hẹn tư vấn học vụ cho sinh viên SV2026001 với cố vấn PGS.TS Nguyễn Văn A vào lúc 14:00 ngày 15/09/2026.",
    "action_type": "FINAL_ANSWER",
    "thought": "Tổng hợp kết quả từ MCP Server thành công.",
    "output": "Đặt lịch thành công cho sinh viên SV2026001 với PGS.TS Nguyễn Văn A vào lúc 14:00 15/09/2026.",
    "latency_ms": 10.0
  }
]
```

**Bảng tổng hợp Waterfall Trace (9 sự kiện):**

| Test Case | Hành vi kỳ vọng | Hành động thực tế của Agent (Groq) | `latency_ms` (bước LLM) | Kết quả |
| :--- | :--- | :--- | :---: | :---: |
| TC01 — direct_query | Trả lời trực tiếp, không gọi Tool | `FINAL_ANSWER` trực tiếp, không gọi Tool | 5114.10 | ✅ Đạt |
| TC02 — single_tool_query | Gọi `academic_query(SV2026001)` | `academic_query({"student_id": "SV2026001"})` → `SUCCESS` | 706.20 | ✅ Đạt |
| TC03 — appointment_booking | Gọi `schedule_appointment` đúng tham số | `schedule_appointment` với đủ 3 tham số → `SUCCESS`, `BK-SV2026001-99` | 1042.64 | ✅ Đạt |
| TC04 — multi_step_reasoning | Tra cứu cố vấn → đặt lịch | `academic_query({"student_id": "SV2026002"})` → tìm được cố vấn `TS. Lê Thị B`, **nhưng chưa gọi `schedule_appointment`** | 722.60 | ⚠️ Đạt 1/2 bước |
| TC05 — edge_case_handling | Nhận `NOT_FOUND`, không bịa dữ liệu | `academic_query({"student_id": "SV9999999"})` → `NOT_FOUND`, phản hồi đúng thông điệp lỗi | 689.85 | ✅ Đạt |

**Nhận xét quan sát (Observability):**
- Độ trễ trung bình khi LLM quyết định gọi Tool (TC02–TC05): **≈ 790 ms**. TC01 chậm nhất (5114 ms) do mô hình sinh câu trả lời văn bản dài.
- TC04 chỉ đạt 1/2 bước vì hàm `run_react_agent()` trong `src/app.py` kết thúc vòng lặp (`break`) ngay sau Observation đầu tiên, và Observation không được nạp lại cho LLM ở lượt kế tiếp. Vì thế Agent không có cơ hội gọi tiếp `schedule_appointment` với tên cố vấn vừa tra được.
- `latency_ms: 10.0` của các bước `FINAL_ANSWER` sau Tool là giá trị gán cố định trong `app.py`, không phải thời gian đo thực tế, vì câu trả lời cuối được ghép từ template chứ không gọi LLM.
- TC01 trả lời từ kiến thức nền của mô hình (ví dụ "144–150 tín chỉ") và mâu thuẫn với câu trả lời 120 tín chỉ ở phiên interactive. Đây là minh chứng rằng thông tin quy chế cần được lấy từ Tool/nguồn dữ liệu chính thức để tránh hallucination.

**Kiểm thử chế độ đàm thoại trực tiếp (`python src/app.py --interactive`) trên Groq API:**

| Câu hỏi | Hành động của Agent | Kết quả |
| :--- | :--- | :---: |
| "Quy chế học vụ VinUni yêu cầu bao nhiêu tín chỉ?" | Trả lời trực tiếp, không gọi Tool | ✅ |
| "Hãy tra cứu thông tin học vụ của sinh viên SV2026001" | `academic_query({"student_id": "SV2026001"})` → `SUCCESS` | ✅ |
| "Đặt lịch hẹn tư vấn cho SV2026001 với PGS.TS Nguyễn Văn A vào 14:00 ngày 15/09/2026" | `schedule_appointment` với đủ 3 tham số → `SUCCESS` | ✅ |
| `exit` | Thoát phiên chat bình thường | ✅ |

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [x] Đã điền API Key thật trong `.env` và xác nhận Agent chạy mượt mà trên LLM API thật (**Groq — `openai/gpt-oss-120b`**, 0 lần fallback Mock).
- [x] Đã thử nghiệm thành công chế độ đàm thoại trực tiếp `python src/app.py --interactive` (3/3 câu hỏi phản hồi đúng).
- **Tổng số Test Cases đã chạy thành công:** 5 / 5 test cases thực thi hoàn tất trên API thật; **4 / 5 đạt đúng hành vi kỳ vọng** (TC04 mới hoàn thành bước tra cứu, chưa tự động đặt lịch).
- **Số lượt gọi Tool qua MCP Server chính xác:** 4 lượt trong test suite (TC02, TC03, TC04, TC05 đều đúng tên Tool và đúng tham số; TC01 không gọi Tool đúng như kỳ vọng). Phiên interactive có thêm 2 lượt chính xác.
- **Kết quả đẩy Repo nộp bài:** [x] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
