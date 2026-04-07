class DataQualityService:
    def build_track_data_quality(self, snapshots, metric_keys, metric_display_map):
        return {"sample_count": 0, "overall_coverage": 0.0}

class DashboardService:
    def get_data_overview(self):
        return {
            "company_count": 0,
            "industry_count": 0,
            "avg_gross_margin": 0.0
        }
    def get_system_status(self, msg_count=0):
        return {
            "api_status": "在线",
            "kb_ready": True,
            "msg_count": msg_count
        }

class ReportService:
    def build_html_report(self, messages, generated_at, active_target):
        return b""

class TrackScoringService:
    def score_snapshots(self, snapshots, track_template):
        return {"ok": False, "reason": "暂未初始化评分模型"}
