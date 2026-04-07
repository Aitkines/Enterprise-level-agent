from agent_engine import DoubaoAgent

class ReportService:
    def __init__(self):
        self.agent = DoubaoAgent()

    def build_html_report(self, messages, generated_at, active_target):
        # 构建给大模型的总结提示词
        context = "\n".join([f"{m['role']}: {m['content']}" for m in messages[-10:]])
        prompt = f"""
        请根据以下对话历史和分析目标 [{active_target}]，生成一份极其专业的、投行级别的 HTML 格式研究报告。
        
        要求：
        1. 必须使用 2026 年的时间主线。
        2. 包含：核心观点摘要、财务深度穿透、行业对标结论、风险提示。
        3. 使用简洁大方的 HTML/CSS 样式（深色背景，适配光之耀面主题）。
        4. 内容要详实，不要空话，要体现出逻辑深度。
        
        对话历史：
        {context}
        """
        
        # 调用大模型（非流式，为了生成完整文件）
        report_content = ""
        try:
            # 直接使用 agent 的底层 client 进行同步请求
            response = self.agent.client.chat.completions.create(
                model=self.agent.model_endpoint,
                messages=[
                    {"role": "system", "content": self.agent.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            report_content = response.choices[0].message.content
        except Exception as e:
            report_content = f"<h1>报告生成失败</h1><p>{str(e)}</p>"
            
        return report_content.encode("utf-8")
