# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""Pydantic models for auto repair estimate data extraction.

Defines the schema used by the content processing pipeline to extract
structured fields from body shop repair estimate documents.
"""

from __future__ import annotations

import json
from typing import List, Optional

from pydantic import BaseModel, Field


class RepairShopAddress(BaseModel):
    """A class representing an auto body shop address."""

    street: Optional[str] = Field(description="Street address, e.g. 456 Repair Lane")
    city: Optional[str] = Field(description="City, e.g. Macon")
    state: Optional[str] = Field(description="State, e.g. GA")
    postal_code: Optional[str] = Field(description="Postal code, e.g. 31201")
    country: Optional[str] = Field(description="Country, e.g. USA")

    @staticmethod
    def example() -> "RepairShopAddress":
        """Return an empty instance with default placeholder values."""
        return RepairShopAddress(
            street="", city="", state="", postal_code="", country=""
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "street": self.street,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
        }


class RepairEstimateVehicle(BaseModel):
    """A class representing the customer vehicle on a repair estimate."""

    year: Optional[int] = Field(description="Vehicle year, e.g. 2022")
    make: Optional[str] = Field(description="Vehicle make, e.g. Toyota")
    model: Optional[str] = Field(description="Vehicle model, e.g. Camry")
    trim: Optional[str] = Field(description="Vehicle trim, e.g. SE")
    vin: Optional[str] = Field(description="Vehicle VIN, e.g. 4T1G11AK2NU123456")
    license_plate: Optional[str] = Field(description="License plate, e.g. GA-ABC123")

    @staticmethod
    def example() -> "RepairEstimateVehicle":
        """Return an empty instance with default placeholder values."""
        return RepairEstimateVehicle(
            year=0,
            make="",
            model="",
            trim="",
            vin="",
            license_plate="",
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "year": self.year,
            "make": self.make,
            "model": self.model,
            "trim": self.trim,
            "vin": self.vin,
            "license_plate": self.license_plate,
        }


class RepairEstimateLineItem(BaseModel):
    """A class representing a repair estimate line item."""

    service_description: Optional[str] = Field(
        description="Service description, e.g. Dent repair (quarter panel)"
    )
    labor_hours: Optional[float] = Field(description="Labor hours, e.g. 2.0")
    rate_per_hour: Optional[float] = Field(description="Labor rate per hour, e.g. 75.0")
    rate_per_hour_currency: Optional[str] = Field(
        description="Currency for rate_per_hour, e.g. USD"
    )
    parts_cost: Optional[float] = Field(description="Parts cost, e.g. 150.0")
    parts_cost_currency: Optional[str] = Field(
        description="Currency for parts_cost, e.g. USD"
    )
    materials_cost: Optional[float] = Field(
        description="Materials/supplies cost, e.g. 50.0"
    )
    materials_cost_currency: Optional[str] = Field(
        description="Currency for materials_cost, e.g. USD"
    )
    total: Optional[float] = Field(description="Line total amount")
    total_currency: Optional[str] = Field(description="Currency for total, e.g. USD")

    @staticmethod
    def example() -> "RepairEstimateLineItem":
        """Return an empty instance with default placeholder values."""
        return RepairEstimateLineItem(
            service_description="",
            labor_hours=0.0,
            rate_per_hour=0.0,
            rate_per_hour_currency="",
            parts_cost=0.0,
            parts_cost_currency="",
            materials_cost=0.0,
            materials_cost_currency="",
            total=0.0,
            total_currency="",
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "service_description": self.service_description,
            "labor_hours": self.labor_hours,
            "rate_per_hour": self.rate_per_hour,
            "rate_per_hour_currency": self.rate_per_hour_currency,
            "parts_cost": self.parts_cost,
            "parts_cost_currency": self.parts_cost_currency,
            "materials_cost": self.materials_cost,
            "materials_cost_currency": self.materials_cost_currency,
            "total": self.total,
            "total_currency": self.total_currency,
        }


class Signature(BaseModel):
    """A class representing an authorized signature field."""

    signatory: Optional[str] = Field(description="Name of the signatory")
    is_signed: Optional[bool] = Field(
        description="Indicates if the document is signed. GPT should check whether it has signature in image files. if there is Sign, fill it up as True"
    )

    @staticmethod
    def example() -> "Signature":
        """Return an empty instance with default placeholder values."""
        return Signature(signatory="", is_signed=False)

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {"signatory": self.signatory, "is_signed": self.is_signed}


class RepairEstimateDocument(BaseModel):
    """A class representing an auto body shop repair estimate document."""

    estimate_number: Optional[str] = Field(
        description="Estimate number, e.g. EST-20251130"
    )
    date: Optional[str] = Field(description="Estimate date, e.g. 2025-11-30")

    prepared_by: Optional[str] = Field(
        description="Prepared by / shop name, e.g. Macon Auto Body & Paint"
    )
    shop_address: Optional[RepairShopAddress] = Field(description="Shop address")
    shop_phone: Optional[str] = Field(description="Shop phone number")

    customer_name: Optional[str] = Field(description="Customer name, e.g. Chad Brooks")
    vehicle: Optional[RepairEstimateVehicle] = Field(description="Vehicle information")

    damage_description: Optional[str] = Field(
        description="Damage description / narrative"
    )

    repair_details: Optional[List[RepairEstimateLineItem]] = Field(
        description="Repair detail line items"
    )

    subtotal: Optional[float] = Field(description="Subtotal amount")
    subtotal_currency: Optional[str] = Field(
        description="Currency for subtotal, e.g. USD"
    )

    tax_rate: Optional[str] = Field(description="Tax rate, e.g. 7%")
    tax_amount: Optional[float] = Field(description="Tax amount, e.g. 24.50")
    tax_currency: Optional[str] = Field(description="Currency for tax_amount, e.g. USD")

    total_estimate: Optional[float] = Field(
        description="Total estimate amount, e.g. 374.50"
    )
    total_estimate_currency: Optional[str] = Field(
        description="Currency for total_estimate, e.g. USD"
    )

    notes: Optional[List[str]] = Field(description="Notes on the estimate")

    authorized_signature: Optional[Signature] = Field(
        description="Authorized signature"
    )
    authorized_signature_date: Optional[str] = Field(
        description="Signature date, e.g. 2025-11-30"
    )

    @staticmethod
    def example() -> "RepairEstimateDocument":
        """Return an empty instance with default placeholder values."""
        return RepairEstimateDocument(
            estimate_number="",
            date="",
            prepared_by="",
            shop_address=RepairShopAddress.example(),
            shop_phone="",
            customer_name="",
            vehicle=RepairEstimateVehicle.example(),
            damage_description="",
            repair_details=[RepairEstimateLineItem.example()],
            subtotal=0.0,
            subtotal_currency="",
            tax_rate="",
            tax_amount=0.0,
            tax_currency="",
            total_estimate=0.0,
            total_estimate_currency="",
            notes=[],
            authorized_signature=Signature.example(),
            authorized_signature_date="",
        )

    @staticmethod
    def from_json(json_str: str) -> "RepairEstimateDocument":
        """Deserialize a JSON string into a RepairEstimateDocument instance."""
        json_content = json.loads(json_str)

        def create_address(details: Optional[dict]) -> Optional[RepairShopAddress]:
            if not details:
                return None
            return RepairShopAddress(
                street=details.get("street"),
                city=details.get("city"),
                state=details.get("state"),
                postal_code=details.get("postal_code"),
                country=details.get("country"),
            )

        def create_vehicle(details: Optional[dict]) -> Optional[RepairEstimateVehicle]:
            if not details:
                return None
            return RepairEstimateVehicle(
                year=details.get("year"),
                make=details.get("make"),
                model=details.get("model"),
                trim=details.get("trim"),
                vin=details.get("vin"),
                license_plate=details.get("license_plate"),
            )

        def create_line_item(
            details: Optional[dict],
        ) -> Optional[RepairEstimateLineItem]:
            if not details:
                return None
            return RepairEstimateLineItem(
                service_description=details.get("service_description"),
                labor_hours=details.get("labor_hours"),
                rate_per_hour=details.get("rate_per_hour"),
                rate_per_hour_currency=details.get("rate_per_hour_currency"),
                parts_cost=details.get("parts_cost"),
                parts_cost_currency=details.get("parts_cost_currency"),
                materials_cost=details.get("materials_cost"),
                materials_cost_currency=details.get("materials_cost_currency"),
                total=details.get("total"),
                total_currency=details.get("total_currency"),
            )

        def create_signature(details: Optional[dict]) -> Optional[Signature]:
            if not details:
                return None
            return Signature(
                signatory=details.get("signatory"),
                is_signed=details.get("is_signed"),
            )

        line_items_raw = json_content.get("repair_details") or []
        line_items = [create_line_item(item) for item in line_items_raw]
        line_items = [item for item in line_items if item is not None]

        return RepairEstimateDocument(
            estimate_number=json_content.get("estimate_number"),
            date=json_content.get("date"),
            prepared_by=json_content.get("prepared_by"),
            shop_address=create_address(json_content.get("shop_address")),
            shop_phone=json_content.get("shop_phone"),
            customer_name=json_content.get("customer_name"),
            vehicle=create_vehicle(json_content.get("vehicle")),
            damage_description=json_content.get("damage_description"),
            repair_details=line_items,
            subtotal=json_content.get("subtotal"),
            subtotal_currency=json_content.get("subtotal_currency"),
            tax_rate=json_content.get("tax_rate"),
            tax_amount=json_content.get("tax_amount"),
            tax_currency=json_content.get("tax_currency"),
            total_estimate=json_content.get("total_estimate"),
            total_estimate_currency=json_content.get("total_estimate_currency"),
            notes=json_content.get("notes") or [],
            authorized_signature=create_signature(
                json_content.get("authorized_signature")
            ),
            authorized_signature_date=json_content.get("authorized_signature_date"),
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "estimate_number": self.estimate_number,
            "date": self.date,
            "prepared_by": self.prepared_by,
            "shop_address": self.shop_address.to_dict() if self.shop_address else None,
            "shop_phone": self.shop_phone,
            "customer_name": self.customer_name,
            "vehicle": self.vehicle.to_dict() if self.vehicle else None,
            "damage_description": self.damage_description,
            "repair_details": [item.to_dict() for item in (self.repair_details or [])],
            "subtotal": self.subtotal,
            "subtotal_currency": self.subtotal_currency,
            "tax_rate": self.tax_rate,
            "tax_amount": self.tax_amount,
            "tax_currency": self.tax_currency,
            "total_estimate": self.total_estimate,
            "total_estimate_currency": self.total_estimate_currency,
            "notes": self.notes or [],
            "authorized_signature": self.authorized_signature.to_dict()
            if self.authorized_signature
            else None,
            "authorized_signature_date": self.authorized_signature_date,
        }
