from pydantic import BaseModel, Field, field_validator
from typing import Dict, Optional, Any

class ExperimentСonfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Name of the experiment")
    variants: Dict[str, int] = Field(..., description="Веса вариантов. Пример: {'A': 50, 'B': 50}",
                                     json_schema_extra={"example": {"A": 33, "B": 33, "C": 33}}
                                     )
    config: Optional[Dict[str, Any]] = Field(default=None, description="Конфиг для рендеринга вариантов. Ключи — имена вариантов")
    url: Optional[str] = Field(default=None, max_length=200, description="URL-паттерн для привязки эксперимента к странице")
    is_active: bool = Field(default=True, description="Включен ли эксперимент")

    @field_validator('variants')
    @classmethod
    def check_weights_positive(cls, v):
        if any(w <= 0 for w in v.values()):
            raise ValueError("Все веса должны быть положительными")
        return v
    

class VariantResponse(BaseModel):
    experiment_name: str = Field(..., description="имя запрошенного теста")
    user_id: str = Field(..., description="ID пользователя")
    variant: str = Field(..., description="Выпавший вариант (A, B, control и т.д.)")