from typing import Any
from pydantic import BaseModel, field_validator, Field


class User(BaseModel):

    id: int
    city: dict
    sex: int
    deactivated: bool = Field(default=False)

    @field_validator('city')
    @classmethod
    def validate_city(cls, value):
        if isinstance(value, dict):
            if value.get('id') == 66:
                return value.get('id')
        raise ValueError('Invalid city')
