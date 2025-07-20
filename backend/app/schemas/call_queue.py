from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

class CallQueueStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    FAILED_RETRY = "failed_retry"
    FAILED_PERMANENT = "failed_permanent"

class CallQueueCreate(BaseModel):
    source_url: str
    api_params: Dict[str, Any] = Field(default_factory=dict)
    source_metadata: Dict[str, Any] = Field(default_factory=dict)

class CallQueue(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_url: str
    api_params: Dict[str, Any]
    status: CallQueueStatus = CallQueueStatus.PENDING
    source_metadata: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.now)
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    last_error: Optional[str] = None

    class Config:
        use_enum_values = True

class SourceContent(BaseModel):
    content_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    source_url: str
    raw_text: str
    processed_text: Optional[str] = None
    embedding: Optional[list[float]] = None
    topic_id: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)