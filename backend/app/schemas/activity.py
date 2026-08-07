from datetime import datetime
from pydantic import BaseModel
from typing import List

class ActivityItemResponse(BaseModel):
    event: str
    repo: str
    details: str
    time: datetime
    status: str

class ActivityFeedResponse(BaseModel):
    activities: List[ActivityItemResponse]
