import pandas as pd


class FinancialTableDTO:
    def __init__(self, data=None, source="未知来源", unit_hint="元", error: str | None = None, sections=None):
        self.data = data if data is not None else []
        self.source = source
        self.unit_hint = unit_hint
        self.error = error
        self.sections = sections if sections is not None else []
        if isinstance(self.data, dict):
            self.row_count = 1 if self.data else 0
        else:
            self.row_count = len(self.data)
        if not self.row_count and self.sections:
            self.row_count = sum(len(section.get("rows", [])) for section in self.sections)

    def is_empty(self) -> bool:
        return self.row_count == 0 or self.error is not None

    def to_dataframe(self) -> pd.DataFrame:
        if self.is_empty():
            return pd.DataFrame()
        if isinstance(self.data, dict):
            return pd.DataFrame([self.data])
        return pd.DataFrame(self.data)
