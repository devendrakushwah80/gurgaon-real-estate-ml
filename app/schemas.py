"""Pydantic contracts for the EstateIQ API."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.ingestion.normalizer import normalize_city


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=120)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Enter a valid email address")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class PreferenceUpdate(BaseModel):
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)
    preferred_bhk: list[int] = Field(default_factory=list)
    preferred_localities: list[str] = Field(default_factory=list)
    property_type: str | None = None
    min_area_sqft: float | None = Field(default=None, gt=0)
    furnishing: str | None = None
    usage: str | None = None
    min_trust_score: float = Field(default=0, ge=0, le=100)

    @field_validator("preferred_bhk")
    @classmethod
    def validate_bhk(cls, values: list[int]) -> list[int]:
        if any(value < 1 or value > 20 for value in values):
            raise ValueError("preferred_bhk values must be between 1 and 20")
        return values


class PropertyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=5000)
    property_type: str = Field(min_length=2, max_length=50)
    bhk: int | None = Field(default=None, ge=1, le=20)
    locality: str = Field(min_length=2, max_length=120)
    sector: str | None = Field(default=None, max_length=120)
    city: str = Field(default="gurgaon", max_length=80)
    area_sqft: float = Field(gt=0, le=1_000_000)
    listing_price: float = Field(gt=0, le=10_000_000)
    furnishing: str | None = None
    floor: str | None = None
    total_floors: int | None = Field(default=None, ge=1, le=200)
    property_age: str | None = None
    amenities: list[str] = Field(default_factory=list)
    seller_type: str | None = None
    rera_id: str | None = None
    source_url: str | None = None
    image_urls: list[str] = Field(default_factory=list)

    @field_validator("city")
    @classmethod
    def canonical_city(cls, value: str) -> str:
        return normalize_city(value)


class RecommendationQuery(BaseModel):
    city: str = Field(default="gurgaon", max_length=80)
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)
    bhk: int | None = Field(default=None, ge=1, le=20)
    locality: str | None = None
    property_type: str | None = None
    min_area_sqft: float | None = Field(default=None, gt=0)
    max_area_sqft: float | None = Field(default=None, gt=0)
    min_trust_score: float = Field(default=0, ge=0, le=100)
    top_n: int = Field(default=10, ge=1, le=50)

    @field_validator("city")
    @classmethod
    def canonical_city(cls, value: str) -> str:
        return normalize_city(value)


class CompareRequest(BaseModel):
    property_ids: list[str] = Field(min_length=2, max_length=4)
