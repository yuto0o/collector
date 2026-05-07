from typing import List
from pydantic import BaseModel


class SummaryModel(BaseModel):
    summary: str
    highlights: List[str] = []
    importance: int = 1
    is_useful_for_python_student: bool = True
    is_ai_news: bool = False
    reason_for_usefulness: str = ""
