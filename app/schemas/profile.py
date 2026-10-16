import re
from datetime import date
from pydantic import BaseModel, field_validator


class ProfileRequest(BaseModel):
    country_code: str | None = None
    faculty: str | None = None
    course: int | None = None
    arrival_date: date | None = None
    visa_expiry: date | None = None
    registration_expiry: date | None = None

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().upper()
        if not re.fullmatch(r"[A-Z]{2}", v):
            raise ValueError("country_code должен содержать ровно две латинские буквы")
        return v

    @field_validator("course")
    @classmethod
    def validate_course(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 6):
            raise ValueError("course должен быть от 1 до 6")
        return v


class ProfileResponse(BaseModel):
    country_code: str | None = None
    faculty: str | None = None
    course: int | None = None
    arrival_date: date | None = None
    visa_expiry: date | None = None
    registration_expiry: date | None = None

    model_config = {"from_attributes": True}
