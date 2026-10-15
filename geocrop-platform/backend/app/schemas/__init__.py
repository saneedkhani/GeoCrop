from pydantic import BaseModel, Field


class SignupIn(BaseModel):
    email: str = ""
    username: str = ""
    password: str = ""
    confirm_password: str = ""


class LoginIn(BaseModel):
    username: str = Field("", description="Username or email")
    password: str = ""


class TokenOut(BaseModel):
    token: str
    user: dict


class UploadIn(BaseModel):
    filename: str
    size_bytes: int | None = None


class CompleteIn(BaseModel):
    model_keys: list[str] = ["cropland", "croptype"]
    location: str | None = None
    capture_date: str | None = None


class RunIn(BaseModel):
    source_image_id: str
    model_keys: list[str]
