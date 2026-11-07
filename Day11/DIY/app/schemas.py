from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """用戶提問"""

    question: str = Field(..., min_length=1)
    failure_mode: str = Field(default="normal", description="failure_mode: normal, slow, unavailable")


class AskResponse(BaseModel):
    """API 回應"""

    answer: str | None = Field(default=None, description="答案內容（正常情況）")
    answer_status: str = Field(description="answered 或 unavailable")
    technical_success: bool = Field(description="是否完成技術工作")
    degraded: bool = Field(description="是否是降級狀態")
    request_id: str = Field(description="請求ID，用於 trace 關聯")
    reason: str | None = Field(default=None, description="失敗原因（unavailable 情況）")
