from pydantic import BaseModel, Field

class ApplyRequest(BaseModel): # This describes the request sent when applying move suggestions
  suggestion_ids: list[int] = Field(min_length=1)