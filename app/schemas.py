from datetime import time
from pydantic import BaseModel, Field
from typing import List, Optional


class CreateReport(BaseModel):
    id: Optional[str]
    description: str
    issue_id: Optional[str]
    title: str
    ref: str
