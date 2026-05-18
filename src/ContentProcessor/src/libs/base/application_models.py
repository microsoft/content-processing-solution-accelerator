# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Shared Pydantic base models and settings used across the application.

Provides ``AppModelBase`` (for domain models) and ``ModelBaseSettings``
(for settings classes) with common Pydantic configuration.
"""

from typing import TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppModelBase(BaseModel):
    """Base model for all application domain objects.

    Enables population by field name, arbitrary types, and
    validates on assignment.
    """

    model_config = ConfigDict(
        populate_by_name=True, arbitrary_types_allowed=True, validate_assignment=True
    )


T = TypeVar("T", bound="ModelBaseSettings")


class ModelBaseSettings(BaseSettings):
    """Base settings model that ignores extra env vars and is case-insensitive."""

    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)
