from typing import Literal

from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    requirement: str = Field(min_length=3, max_length=5000)
    scenario: Literal["greenfield", "brownfield", "ambiguous"]
    auto_approve: bool = False


class ApprovalRequest(BaseModel):
    approved: bool
    comment: str = Field(default="", max_length=2000)


class ReplanRequest(BaseModel):
    requirement: str = Field(min_length=3, max_length=5000)
