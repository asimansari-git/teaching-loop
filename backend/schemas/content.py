from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List

class ContentChunkOut(BaseModel):
    id: int
    text: str
    topics: list
    status: str

class ContentItemOut(BaseModel):
    id: int
    filename: str
    status: str
    created_at: datetime
    chunks: List[ContentChunkOut] = []
    model_config = ConfigDict(from_attributes=True)
