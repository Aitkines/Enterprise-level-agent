import sys
import os
# Ensure root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from agent_engine import DoubaoAgent

class ChatService:
    def __init__(self):
        self.agent = DoubaoAgent()

    def run_query_stream(self, prompt, chat_history, active_target=None, active_targets=None):
        try:
            # 直接调用 agent 的流式接口
            for chunk in self.agent.run_query_stream(
                query=prompt,
                chat_history=chat_history or []
            ):
                yield chunk
        except Exception as e:
            yield f"ChatService 运行出错: {str(e)}"

    def extract_tool_name(self, status_text):
        if "：" in status_text:
            return status_text.split("：")[-1]
        return "专家工具集"
