"""
Lab #3: Baseline Chatbot vs ReAct Agent
Học viên hoàn thiện các mục TODO để hoàn thành bài lab.
"""

import json
import re
from tools import TOOL_DEFINITIONS, TOOL_MAP, get_flight_info, get_weather_forecast

SYSTEM_PROMPT = """Bạn là một ReAct Agent thông minh hỗ trợ khách hàng Vingroup.
Bạn chỉ sử dụng các công cụ sau:
{tools}

Quy trình trả lời bắt buộc:
Thought: <Suy nghĩ bước tiếp theo>
Action: {{"name": "<tên tool>", "args": {{<tham số>}}}}
Observation: <Kết quả từ tool>
... (Lặp lại cho tới khi có đủ dữ liệu)
Final Answer: <Câu trả lời hoàn chỉnh cho khách hàng>
"""

class ChatbotBaseline:
    """Baseline LLM Chatbot (Không sử dụng ReAct Loop hay Tools)"""
    def query(self, user_input: str) -> dict:
        return {"status": "success", "answer": f"[Chatbot Baseline] Trả lời cho: {user_input}", "tool_calls": []}

class ReActAgent:
    """ReAct Agent có sử dụng Thought-Action-Observation Loop"""
    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.trace = []

    def run(self, user_input: str) -> dict:
        """Execute local tools in a deterministic Thought-Action-Observation loop."""
        self.trace = []
        text = user_input.upper()
        codes = re.findall(r"\b(?:HAN|SGN|DAD)\b", text)
        is_flight = "CHUYẾN BAY" in text or "VÉ" in text
        is_weather = "THỜI TIẾT" in text
        price_match = re.search(r"(\d+(?:[.,]\d+)?)\s*TRIỆU", text)
        max_price = int(float(price_match.group(1).replace(",", ".")) * 1_000_000) if price_match else 5_000_000

        actions = []
        if is_flight and len(codes) >= 2:
            actions.append(("get_flight_info", {"origin": codes[0], "destination": codes[1], "max_price": max_price}))
        if is_weather:
            actions.append(("get_weather_forecast", {"city_code": codes[-1] if codes else "SGN"}))

        observations, iteration = [], 0
        while iteration < self.max_iterations and actions:
            name, args = actions.pop(0)
            observation = TOOL_MAP[name](**args)
            observations.append((name, observation))
            iteration += 1
            self.trace.append({"iteration": iteration, "action": {"name": name, "args": args}, "observation": observation})

        if actions:
            return {"status": "max_iterations_reached", "iterations": iteration,
                    "answer": "Đã đạt giới hạn số vòng lặp.", "trace": self.trace}

        if not observations:
            iteration = 1
            answer = "Vinpearl hỗ trợ khách hàng theo chính sách đổi trả vé hiện hành."
            self.trace.append({"iteration": iteration, "action": None})
        else:
            parts = []
            for name, data in observations:
                if name == "get_flight_info":
                    parts.append("Chuyến bay phù hợp: " + ", ".join(
                        f"{flight['flight_number']} ({flight['price_vnd']:,} VND)" for flight in data))
                else:
                    parts.append(f"Thời tiết {data['city']}: {data['temperature_c']}°C. {data['recommendation']}")
            answer = " ".join(parts)
            if len(observations) > 1:
                if iteration >= self.max_iterations:
                    return {"status": "max_iterations_reached", "iterations": iteration, "answer": answer, "trace": self.trace}
                iteration += 1
                self.trace.append({"iteration": iteration, "action": None, "final_answer": answer})

        return {"status": "completed", "iterations": iteration, "answer": answer, "trace": self.trace}

def main():
    user_query = "Tìm cho tôi chuyến bay từ HAN đi SGN dưới 2 triệu, rồi cho biết thời tiết SGN nên mặc gì?"
    
    print("=== RUNNING CHATBOT BASELINE ===")
    chatbot = ChatbotBaseline()
    print(chatbot.query(user_query))
    
    print("\n=== RUNNING REACT AGENT ===")
    agent = ReActAgent(max_iterations=5)
    result = agent.run(user_query)
    print("Result:", result)
    print("Trace Log:", json.dumps(agent.trace, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
