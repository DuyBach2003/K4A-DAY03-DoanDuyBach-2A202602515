"""
🔌 MULTI-PROVIDER LLM ADAPTER (Google Gemini, OpenAI, Groq & Offline Mock)
Hỗ trợ Native Tool Calling và chuyển đổi linh hoạt qua biến môi trường LLM_PROVIDER.

Lịch sử hội thoại (messages) truyền vào generate_with_tools() dùng định dạng trung lập:
  - {"role": "user", "content": str}
  - {"role": "assistant", "tool_call": {"id", "name", "arguments"}, "provider_data": ...}
  - {"role": "tool", "tool_call_id": str, "name": str, "content": str (JSON Observation)}
Mỗi Provider tự chuyển đổi sang định dạng Native Tool Calling của SDK tương ứng.
"""

import os
import re
import sys
import json
from typing import Dict, Any, List, Union
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

Messages = Union[str, List[Dict[str, Any]]]


def as_messages(messages: Messages) -> List[Dict[str, Any]]:
    """Cho phép truyền 1 câu hỏi dạng chuỗi (tương thích ngược) hoặc cả lịch sử hội thoại"""
    if isinstance(messages, str):
        return [{"role": "user", "content": messages}]
    return messages


def summarize_observation(obs: Dict[str, Any]) -> str:
    """Tổng hợp câu trả lời từ Observation (dùng cho Mock Offline Provider)"""
    if obs.get("status") == "SUCCESS" and "data" in obs:
        d = obs["data"]
        return (
            f"Kết quả tra cứu cho sinh viên {obs.get('student_id', '')} ({d.get('full_name', '')}): "
            f"Lớp {d.get('class', '')}, GPA: {d.get('gpa', '')}, Email: {d.get('email', '')}, "
            f"Trạng thái: {d.get('status', '')}, Cố vấn: {d.get('advisor', '')}."
        )
    return obs.get("message") or f"Phản hồi từ công cụ: {json.dumps(obs, ensure_ascii=False)}"


class BaseLLMProvider:
    """Interface cơ sở cho các LLM Provider hỗ trợ Native Tool Calling"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(self, messages: Messages, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        raise NotImplementedError


class MockOfflineProvider(BaseLLMProvider):
    """Offline Mock Provider dùng để chạy thử mà không tốn API Key"""
    def __init__(self):
        self.model_name = "Offline-Mock-Model-2026"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return f"[Mock Chatbot Response]: Xin chào! Tôi đã nhận được câu hỏi '{prompt}'. (Chế độ Chatbot không có Tool tra cứu dữ liệu thời gian thực)."

    def _tool_call(self, tool_name: str, arguments: Dict[str, Any], thought: str, call_no: int) -> Dict[str, Any]:
        return {
            "type": "tool_call",
            "tool_name": tool_name,
            "arguments": arguments,
            "call_id": f"mock_call_{call_no}",
            "thought": thought,
            "model": self.model_name
        }

    def generate_with_tools(self, messages: Messages, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        messages = as_messages(messages)
        query = next(m["content"] for m in messages if m["role"] == "user")
        q = query.lower()
        sid_match = re.search(r"sv\d+", q)
        student_id = sid_match.group(0).upper() if sid_match else "SV2026001"
        dt_match = re.search(r"(\d{1,2}:\d{2}).*?(\d{1,2}/\d{1,2}/\d{4})", query)
        datetime_str = f"{dt_match.group(1)} {dt_match.group(2)}" if dt_match else "14:00 15/09/2026"
        observations = [m for m in messages if m["role"] == "tool"]
        call_no = len(observations) + 1

        # Lượt đầu tiên: mô phỏng nhận diện intent để chọn Tool
        if not observations:
            if "đặt lịch" in q and "tra cứu" not in q:
                return self._tool_call(
                    "schedule_appointment",
                    {"student_id": student_id, "datetime_str": datetime_str, "advisor_name": "PGS.TS Nguyễn Văn A"},
                    f"Người dùng yêu cầu đặt lịch hẹn tư vấn cho sinh viên {student_id}. Tôi sẽ gọi tool schedule_appointment.",
                    call_no
                )
            if sid_match or "tra cứu" in q:
                return self._tool_call(
                    "academic_query",
                    {"student_id": student_id},
                    f"Người dùng muốn tra cứu thông tin học vụ của sinh viên {student_id}. Tôi sẽ gọi tool academic_query.",
                    call_no
                )
            return {
                "type": "text",
                "content": "[Mock Agent Response]: Xin chào! Quy chế học vụ VinUni yêu cầu sinh viên tích lũy tối thiểu 120 tín chỉ và duy trì GPA trên 2.0 để tốt nghiệp.",
                "thought": "Câu hỏi chung về quy chế học vụ, trả lời trực tiếp không cần gọi Tool.",
                "model": self.model_name
            }

        # Các lượt sau: suy luận tiếp dựa trên Observation gần nhất
        last = observations[-1]
        obs = json.loads(last["content"])
        if last["name"] == "academic_query" and obs.get("status") == "SUCCESS" and "đặt lịch" in q:
            advisor = obs["data"].get("advisor", "")
            return self._tool_call(
                "schedule_appointment",
                {"student_id": student_id, "datetime_str": datetime_str, "advisor_name": advisor},
                f"Observation cho biết cố vấn phụ trách là {advisor}. Tiếp tục gọi schedule_appointment để đặt lịch.",
                call_no
            )
        return {
            "type": "text",
            "content": summarize_observation(obs),
            "thought": "Đã có đủ dữ liệu từ Observation, tổng hợp câu trả lời cuối cùng.",
            "model": self.model_name
        }


def _to_gemini_contents(messages: List[Dict[str, Any]], types) -> list:
    """Chuyển lịch sử hội thoại trung lập sang Content của Google GenAI SDK"""
    contents = []
    for m in messages:
        if m["role"] == "user":
            contents.append(types.Content(role="user", parts=[types.Part(text=m["content"])]))
        elif m["role"] == "assistant":
            tc = m["tool_call"]
            # Ưu tiên Part gốc do Gemini trả về (giữ nguyên thought_signature)
            part = m.get("provider_data") or types.Part.from_function_call(name=tc["name"], args=tc["arguments"])
            contents.append(types.Content(role="model", parts=[part]))
        elif m["role"] == "tool":
            response = json.loads(m["content"])
            contents.append(types.Content(role="user", parts=[types.Part.from_function_response(name=m["name"], response=response)]))
    return contents


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider (Native Tool Calling với Google GenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-2.5-flash"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(model=self.model_name, contents=contents)
            return response.text
        except Exception as e:
            return f"[Gemini Exception]: {str(e)}"

    def generate_with_tools(self, messages: Messages, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        messages = as_messages(messages)
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print("ℹ️ [Gemini Provider]: Chưa tìm thấy GEMINI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(messages, tools_schema, system_prompt)

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)

            # Chuẩn hóa function declarations cho Gemini SDK
            function_declarations = []
            for tool in tools_schema:
                # Bỏ qua các tool schema chưa được định nghĩa hoàn chỉnh
                if not tool.get("name") or not tool.get("parameters"):
                    continue
                function_declarations.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {})
                })

            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                tools=[{"function_declarations": function_declarations}] if function_declarations else None,
                temperature=0.2
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=_to_gemini_contents(messages, types),
                config=config
            )

            # Kiểm tra xem Gemini có trả về Tool Call không
            if response.function_calls:
                call = response.function_calls[0]
                args = dict(call.args) if hasattr(call, 'args') and call.args else {}
                raw_part = next((p for p in response.candidates[0].content.parts if p.function_call), None)
                return {
                    "type": "tool_call",
                    "tool_name": call.name,
                    "arguments": args,
                    "call_id": call.id,
                    "provider_data": raw_part,
                    "thought": f"Gemini quyết định gọi công cụ '{call.name}' với tham số: {json.dumps(args, ensure_ascii=False)}",
                    "model": self.model_name
                }
            else:
                return {
                    "type": "text",
                    "content": response.text or "",
                    "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ).",
                    "model": self.model_name
                }

        except Exception as e:
            print(f"⚠️ [Gemini API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(messages, tools_schema, system_prompt)


def _to_openai_messages(messages: List[Dict[str, Any]], system_prompt: str) -> List[Dict[str, Any]]:
    """Chuyển lịch sử hội thoại trung lập sang messages của OpenAI Chat Completions"""
    out = [{"role": "system", "content": system_prompt}] if system_prompt else []
    for m in messages:
        if m["role"] == "user":
            out.append({"role": "user", "content": m["content"]})
        elif m["role"] == "assistant":
            tc = m["tool_call"]
            out.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"], ensure_ascii=False)}
                }]
            })
        elif m["role"] == "tool":
            out.append({"role": "tool", "tool_call_id": m["tool_call_id"], "content": m["content"]})
    return out


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (Native Tool Calling với OpenAI SDK)"""
    label = "OpenAI"
    key_env = "OPENAI_API_KEY"
    key_placeholder = "your_openai_api_key_here"
    default_model = "gpt-4o-mini"
    default_base_url = None  # None: OpenAI SDK tự đọc OPENAI_BASE_URL hoặc dùng endpoint mặc định

    def __init__(self, api_key: str = None, model: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv(self.key_env)
        self.model_name = model or os.getenv("LLM_MODEL") or self.default_model
        self.base_url = base_url or self.default_base_url

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == self.key_placeholder:
            return f"[{self.label} Error]: Chưa cấu hình {self.key_env} trong file .env! Đang sử dụng chế độ Mock."
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(model=self.model_name, messages=messages)
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[OpenAI Exception]: {str(e)}"

    def generate_with_tools(self, messages: Messages, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        messages = as_messages(messages)
        if not self.api_key or self.api_key == self.key_placeholder:
            print(f"ℹ️ [{self.label} Provider]: Chưa tìm thấy {self.key_env} hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(messages, tools_schema, system_prompt)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)

            tools = []
            for tool in tools_schema:
                if not tool.get("name"):
                    continue
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                })

            response = client.chat.completions.create(
                model=self.model_name,
                messages=_to_openai_messages(messages, system_prompt),
                tools=tools if tools else None,
                tool_choice="auto" if tools else None
            )

            msg = response.choices[0].message
            # Các model suy luận (vd. gpt-oss trên Groq) trả về chuỗi suy luận trong trường 'reasoning'
            reasoning = (getattr(msg, "reasoning", None) or "").strip()
            if msg.tool_calls:
                call = msg.tool_calls[0]
                args = json.loads(call.function.arguments) if call.function.arguments else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.function.name,
                    "arguments": args,
                    "call_id": call.id,
                    "thought": reasoning or (msg.content or "").strip() or f"{self.label} ({self.model_name}) quyết định gọi công cụ '{call.function.name}' với tham số: {json.dumps(args, ensure_ascii=False)}",
                    "model": self.model_name
                }
            else:
                return {
                    "type": "text",
                    "content": msg.content or "",
                    "thought": reasoning or f"{self.label} ({self.model_name}) phản hồi trực tiếp bằng văn bản (không cần gọi công cụ).",
                    "model": self.model_name
                }
        except Exception as e:
            print(f"⚠️ [{self.label} API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(messages, tools_schema, system_prompt)


class GroqProvider(OpenAIProvider):
    """Groq Provider (endpoint tương thích OpenAI, Native Tool Calling qua OpenAI SDK)"""
    label = "Groq"
    key_env = "GROQ_API_KEY"
    key_placeholder = "your_groq_api_key_here"
    default_model = "openai/gpt-oss-120b"
    default_base_url = "https://api.groq.com/openai/v1"


def get_llm_provider() -> BaseLLMProvider:
    """Factory function khởi tạo Provider theo LLM_PROVIDER env variable"""
    provider_type = os.getenv("LLM_PROVIDER", "gemini").lower()

    if provider_type == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        if key and key != "your_gemini_api_key_here":
            return GeminiProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if key and key != "your_openai_api_key_here":
            return OpenAIProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "groq":
        key = os.getenv("GROQ_API_KEY")
        if key and key != "your_groq_api_key_here":
            return GroqProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "mock":
        return MockOfflineProvider()
    else:
        return MockOfflineProvider()
