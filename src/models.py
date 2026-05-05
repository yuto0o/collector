from typing import List
from pydantic import BaseModel


class SummaryModel(BaseModel):
    summary: str
    highlights: List[str] = []
    importance: int = 1
    is_useful_for_python_student: bool = True
    reason_for_usefulness: str = ""
