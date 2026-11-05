import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not USERNAME_PATTERN.fullmatch(value):
            raise ValueError(
                "Username must be 3-30 characters: letters, digits, underscores, dots, or "
                "hyphens only."
            )
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class LoginRequest(BaseModel):
    identifier: str
    password: str


class VerifyEmailRequest(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


class UserMe(BaseModel):
    id: UUID
    username: str
    email: str
    email_verified: bool
    translation_language: str
    created_at: datetime


# Kept narrow and allowlisted (rather than a free-text string) so a typo'd or unsupported
# DeepL target code can never get stored — see docs/decisions/0004-translations-and-dictionary.md.
SUPPORTED_TRANSLATION_LANGUAGES = {"EN-US", "ES"}


class UpdateSettingsRequest(BaseModel):
    translation_language: str

    @field_validator("translation_language")
    @classmethod
    def validate_translation_language(cls, value: str) -> str:
        if value not in SUPPORTED_TRANSLATION_LANGUAGES:
            raise ValueError(
                f"translation_language must be one of {sorted(SUPPORTED_TRANSLATION_LANGUAGES)}."
            )
        return value
