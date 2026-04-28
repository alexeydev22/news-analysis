from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    service: str = Field(min_length=1)
    status: str = "ok"
