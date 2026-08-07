from uuid import UUID
from pydantic import BaseModel
from typing import List

class DocTocItem(BaseModel):
    commit_id: UUID
    repo_name: str
    message: str

class DocumentationTocResponse(BaseModel):
    items: List[DocTocItem]
