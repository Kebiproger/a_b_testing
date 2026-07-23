from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class TrackingEvent(BaseModel):
    user_id: str = Field(..., min_length=1, description="Идентификатор пользователя")
    event_name: str = Field(..., min_length=1, description="Название события")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    experiment_name: Optional[str] = Field(default=None, min_length=1, description="Имя A/B теста")
    variant: Optional[str] = Field(default=None, min_length=1, description="Назначенный вариант")
    event_data: Optional[Dict[str, Any]] = Field(default=None, description="Произвольный payload")
