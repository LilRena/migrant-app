from datetime import date
from pydantic import BaseModel


class ProfileRequest(BaseModel):
    country_code: str | None = None
    faculty: str | None = None
    course: int | None = None
    arrival_date: date | None = None
    visa_expiry: date | None = None
    registration_expiry: date | None = None


class ProfileResponse(BaseModel):
    country_code: str | None = None
    faculty: str | None = None
    course: int | None = None
    arrival_date: date | None = None
    visa_expiry: date | None = None
    registration_expiry: date | None = None

    model_config = {"from_attributes": True}
