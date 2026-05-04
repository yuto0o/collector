from typing import List
from pydantic import BaseModel


class SummaryModel(BaseModel):
    summary: str
    highlights: List[str] = []
    importance: int = 1
