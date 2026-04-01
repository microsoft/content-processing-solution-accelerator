# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""Pydantic models for police report data extraction.

Defines the schema used by the content processing pipeline to extract
structured fields from police report documents attached to insurance claims.
"""

from __future__ import annotations

import json
from typing import List, Optional

from pydantic import BaseModel, Field


class PoliceReportAddress(BaseModel):
    """A class representing an address referenced in a police report."""

    street: Optional[str] = Field(description="Street address, e.g. 123 Main St.")
    city: Optional[str] = Field(description="City, e.g. Macon")
    state: Optional[str] = Field(description="State, e.g. GA")
    postal_code: Optional[str] = Field(description="Postal code, e.g. 31201")
    country: Optional[str] = Field(description="Country, e.g. USA")

    @staticmethod
    def example() -> "PoliceReportAddress":
        """Return an empty instance with default placeholder values."""
        return PoliceReportAddress(
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


class ReportingParty(BaseModel):
    """A class representing the reporting party / claimant in the police report context."""

    name: Optional[str] = Field(description="Full name of reporting party")
    address: Optional[PoliceReportAddress] = Field(
        description="Address of reporting party"
    )
    phone: Optional[str] = Field(description="Phone number")
    email: Optional[str] = Field(description="Email address")

    @staticmethod
    def example() -> "ReportingParty":
        """Return an empty instance with default placeholder values."""
        return ReportingParty(
            name="",
            address=PoliceReportAddress.example(),
            phone="",
            email="",
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "name": self.name,
            "address": self.address.to_dict() if self.address else None,
            "phone": self.phone,
            "email": self.email,
        }


class PoliceReportVehicle(BaseModel):
    """A class representing a vehicle referenced in a police report."""

    year: Optional[int] = Field(description="Vehicle year, e.g. 2022")
    make: Optional[str] = Field(description="Vehicle make, e.g. Toyota")
    model: Optional[str] = Field(description="Vehicle model, e.g. Camry")
    trim: Optional[str] = Field(description="Vehicle trim, e.g. SE")
    vin: Optional[str] = Field(description="Vehicle VIN")
    license_plate: Optional[str] = Field(description="License plate")
    mileage: Optional[int] = Field(description="Mileage")

    @staticmethod
    def example() -> "PoliceReportVehicle":
        """Return an empty instance with default placeholder values."""
        return PoliceReportVehicle(
            year=0,
            make="",
            model="",
            trim="",
            vin="",
            license_plate="",
            mileage=0,
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
            "mileage": self.mileage,
        }


class PoliceReportIncident(BaseModel):
    """A class representing incident details in a police report."""

    date: Optional[str] = Field(description="Incident date, e.g. 2025-11-28")
    time: Optional[str] = Field(description="Incident time, e.g. 14:15")
    location: Optional[str] = Field(description="Incident location")
    cause: Optional[str] = Field(description="Cause of incident")
    narrative: Optional[str] = Field(
        description="Narrative/description of what happened"
    )

    @staticmethod
    def example() -> "PoliceReportIncident":
        """Return an empty instance with default placeholder values."""
        return PoliceReportIncident(
            date="", time="", location="", cause="", narrative=""
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "date": self.date,
            "time": self.time,
            "location": self.location,
            "cause": self.cause,
            "narrative": self.narrative,
        }


class PoliceReportDamageItem(BaseModel):
    """A class representing a damage line item recorded alongside a police report."""

    item_description: Optional[str] = Field(description="Damaged item/area description")
    repair_estimate: Optional[float] = Field(description="Repair estimate amount")
    repair_estimate_currency: Optional[str] = Field(
        description="Currency of repair_estimate, e.g. USD"
    )

    @staticmethod
    def example() -> "PoliceReportDamageItem":
        """Return an empty instance with default placeholder values."""
        return PoliceReportDamageItem(
            item_description="",
            repair_estimate=0.0,
            repair_estimate_currency="",
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "item_description": self.item_description,
            "repair_estimate": self.repair_estimate,
            "repair_estimate_currency": self.repair_estimate_currency,
        }


class PoliceReportDamageSummary(BaseModel):
    """A class representing a damage summary section."""

    items: Optional[List[PoliceReportDamageItem]] = Field(
        description="List of damage items"
    )
    total_estimated_repair: Optional[float] = Field(
        description="Total estimated repair amount"
    )
    total_estimated_repair_currency: Optional[str] = Field(
        description="Currency of total_estimated_repair, e.g. USD"
    )

    @staticmethod
    def example() -> "PoliceReportDamageSummary":
        """Return an empty instance with default placeholder values."""
        return PoliceReportDamageSummary(
            items=[PoliceReportDamageItem.example()],
            total_estimated_repair=0.0,
            total_estimated_repair_currency="",
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "items": [item.to_dict() for item in (self.items or [])],
            "total_estimated_repair": self.total_estimated_repair,
            "total_estimated_repair_currency": self.total_estimated_repair_currency,
        }


class PoliceReportDocument(BaseModel):
    """A class representing a police report document attached to an auto claim.

    Note: The sample content includes the statement "Police Report: Filed (Report # GA-20251128-CR)".
    This schema focuses on extracting the report identifier and the related incident context.
    """

    report_number: Optional[str] = Field(
        description="Police report number, e.g. GA-20251128-CR"
    )
    is_filed: Optional[bool] = Field(description="Whether a police report was filed")
    reporting_agency: Optional[str] = Field(description="Reporting agency / department")

    insurance_company: Optional[str] = Field(description="Insurance company name")
    claim_number: Optional[str] = Field(description="Claim number")
    policy_number: Optional[str] = Field(description="Policy number")

    reporting_party: Optional[ReportingParty] = Field(
        description="Reporting party information"
    )
    incident: Optional[PoliceReportIncident] = Field(description="Incident details")
    vehicles: Optional[List[PoliceReportVehicle]] = Field(
        description="Vehicles involved"
    )
    damage_summary: Optional[PoliceReportDamageSummary] = Field(
        description="Damage summary"
    )

    @staticmethod
    def example() -> "PoliceReportDocument":
        """Return an empty instance with default placeholder values."""
        return PoliceReportDocument(
            report_number="",
            is_filed=False,
            reporting_agency="",
            insurance_company="",
            claim_number="",
            policy_number="",
            reporting_party=ReportingParty.example(),
            incident=PoliceReportIncident.example(),
            vehicles=[PoliceReportVehicle.example()],
            damage_summary=PoliceReportDamageSummary.example(),
        )

    @staticmethod
    def from_json(json_str: str) -> "PoliceReportDocument":
        """Deserialize a JSON string into a PoliceReportDocument instance."""
        json_content = json.loads(json_str)

        def create_address(address: Optional[dict]) -> Optional[PoliceReportAddress]:
            if not address:
                return None
            return PoliceReportAddress(
                street=address.get("street"),
                city=address.get("city"),
                state=address.get("state"),
                postal_code=address.get("postal_code"),
                country=address.get("country"),
            )

        def create_reporting_party(details: Optional[dict]) -> Optional[ReportingParty]:
            if not details:
                return None
            return ReportingParty(
                name=details.get("name"),
                address=create_address(details.get("address")),
                phone=details.get("phone"),
                email=details.get("email"),
            )

        def create_incident(details: Optional[dict]) -> Optional[PoliceReportIncident]:
            if not details:
                return None
            return PoliceReportIncident(
                date=details.get("date"),
                time=details.get("time"),
                location=details.get("location"),
                cause=details.get("cause"),
                narrative=details.get("narrative"),
            )

        def create_vehicle(details: Optional[dict]) -> Optional[PoliceReportVehicle]:
            if not details:
                return None
            return PoliceReportVehicle(
                year=details.get("year"),
                make=details.get("make"),
                model=details.get("model"),
                trim=details.get("trim"),
                vin=details.get("vin"),
                license_plate=details.get("license_plate"),
                mileage=details.get("mileage"),
            )

        def create_damage_item(
            details: Optional[dict],
        ) -> Optional[PoliceReportDamageItem]:
            if not details:
                return None
            return PoliceReportDamageItem(
                item_description=details.get("item_description"),
                repair_estimate=details.get("repair_estimate"),
                repair_estimate_currency=details.get("repair_estimate_currency"),
            )

        def create_damage_summary(
            details: Optional[dict],
        ) -> Optional[PoliceReportDamageSummary]:
            if not details:
                return None
            items_raw = details.get("items") or []
            items = [create_damage_item(i) for i in items_raw]
            items = [i for i in items if i is not None]
            return PoliceReportDamageSummary(
                items=items,
                total_estimated_repair=details.get("total_estimated_repair"),
                total_estimated_repair_currency=details.get(
                    "total_estimated_repair_currency"
                ),
            )

        vehicles_raw = json_content.get("vehicles") or []
        vehicles = [create_vehicle(v) for v in vehicles_raw]
        vehicles = [v for v in vehicles if v is not None]

        return PoliceReportDocument(
            report_number=json_content.get("report_number"),
            is_filed=json_content.get("is_filed"),
            reporting_agency=json_content.get("reporting_agency"),
            insurance_company=json_content.get("insurance_company"),
            claim_number=json_content.get("claim_number"),
            policy_number=json_content.get("policy_number"),
            reporting_party=create_reporting_party(json_content.get("reporting_party")),
            incident=create_incident(json_content.get("incident")),
            vehicles=vehicles,
            damage_summary=create_damage_summary(json_content.get("damage_summary")),
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "report_number": self.report_number,
            "is_filed": self.is_filed,
            "reporting_agency": self.reporting_agency,
            "insurance_company": self.insurance_company,
            "claim_number": self.claim_number,
            "policy_number": self.policy_number,
            "reporting_party": self.reporting_party.to_dict()
            if self.reporting_party
            else None,
            "incident": self.incident.to_dict() if self.incident else None,
            "vehicles": [v.to_dict() for v in (self.vehicles or [])],
            "damage_summary": self.damage_summary.to_dict()
            if self.damage_summary
            else None,
        }
