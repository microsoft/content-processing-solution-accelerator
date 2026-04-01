# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""Pydantic models for auto insurance claim form data extraction.

Defines the hierarchical schema used by the content processing pipeline to
extract structured fields from auto insurance claim documents.
"""

from __future__ import annotations

import json
from typing import List, Optional

from pydantic import BaseModel, Field


class AutoClaimAddress(BaseModel):
    """A class representing an address used on an auto claim form."""

    street: Optional[str] = Field(description="Street address, e.g. 123 Main St.")
    city: Optional[str] = Field(description="City, e.g. Macon")
    state: Optional[str] = Field(description="State, e.g. GA")
    postal_code: Optional[str] = Field(description="Postal code, e.g. 31201")
    country: Optional[str] = Field(description="Country, e.g. USA")

    @staticmethod
    def example() -> "AutoClaimAddress":
        """Return an empty instance with default placeholder values."""
        return AutoClaimAddress(
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


class PolicyholderInformation(BaseModel):
    """A class representing policyholder information."""

    name: Optional[str] = Field(description="Policyholder full name, e.g. Chad Brooks")
    address: Optional[AutoClaimAddress] = Field(
        description="Policyholder address, e.g. 123 Main Street, Macon, GA 31201"
    )
    phone: Optional[str] = Field(
        description="Policyholder phone number, e.g. (555) 555-1212"
    )
    email: Optional[str] = Field(
        description="Policyholder email address, e.g. chad.brooks@example.com"
    )

    @staticmethod
    def example() -> "PolicyholderInformation":
        """Return an empty instance with default placeholder values."""
        return PolicyholderInformation(
            name="",
            address=AutoClaimAddress.example(),
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


class PolicyDetails(BaseModel):
    """A class representing policy details."""

    coverage_type: Optional[str] = Field(
        description="Coverage type, e.g. Auto – Comprehensive"
    )
    effective_date: Optional[str] = Field(
        description="Policy effective date, e.g. 2025-01-01"
    )
    expiration_date: Optional[str] = Field(
        description="Policy expiration date, e.g. 2025-12-31"
    )
    deductible: Optional[float] = Field(description="Deductible amount, e.g. 500.0")
    deductible_currency: Optional[str] = Field(
        description="Currency of the deductible, e.g. USD"
    )

    @staticmethod
    def example() -> "PolicyDetails":
        """Return an empty instance with default placeholder values."""
        return PolicyDetails(
            coverage_type="",
            effective_date="",
            expiration_date="",
            deductible=0.0,
            deductible_currency="",
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "coverage_type": self.coverage_type,
            "effective_date": self.effective_date,
            "expiration_date": self.expiration_date,
            "deductible": self.deductible,
            "deductible_currency": self.deductible_currency,
        }


class IncidentDetails(BaseModel):
    """A class representing incident details."""

    date_of_loss: Optional[str] = Field(description="Date of loss, e.g. 2025-11-28")
    time_of_loss: Optional[str] = Field(description="Time of loss, e.g. 14:15")
    location: Optional[str] = Field(
        description="Incident location, e.g. Parking lot near 123 Main Street, Macon, GA"
    )
    cause_of_loss: Optional[str] = Field(
        description="Cause of loss, e.g. Low-speed collision with another vehicle"
    )
    description: Optional[str] = Field(
        description="Incident description, e.g. Minor dent and paint scratches; no structural damage"
    )
    police_report_filed: Optional[bool] = Field(
        description="Whether a police report was filed"
    )
    police_report_number: Optional[str] = Field(
        description="Police report number, e.g. GA-20251128-CR"
    )

    @staticmethod
    def example() -> "IncidentDetails":
        """Return an empty instance with default placeholder values."""
        return IncidentDetails(
            date_of_loss="",
            time_of_loss="",
            location="",
            cause_of_loss="",
            description="",
            police_report_filed=False,
            police_report_number="",
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "date_of_loss": self.date_of_loss,
            "time_of_loss": self.time_of_loss,
            "location": self.location,
            "cause_of_loss": self.cause_of_loss,
            "description": self.description,
            "police_report_filed": self.police_report_filed,
            "police_report_number": self.police_report_number,
        }


class VehicleInformation(BaseModel):
    """A class representing vehicle information."""

    year: Optional[int] = Field(description="Vehicle year, e.g. 2022")
    make: Optional[str] = Field(description="Vehicle make, e.g. Toyota")
    model: Optional[str] = Field(description="Vehicle model, e.g. Camry")
    trim: Optional[str] = Field(description="Vehicle trim, e.g. SE")
    vin: Optional[str] = Field(description="Vehicle VIN, e.g. 4T1G11AK2NU123456")
    license_plate: Optional[str] = Field(description="License plate, e.g. GA-ABC123")
    mileage: Optional[int] = Field(description="Mileage, e.g. 28450")

    @staticmethod
    def example() -> "VehicleInformation":
        """Return an empty instance with default placeholder values."""
        return VehicleInformation(
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


class DamageAssessmentItem(BaseModel):
    """A class representing a damage assessment line item."""

    item_description: Optional[str] = Field(
        description="Damaged item/area description, e.g. Right-front quarter panel"
    )
    date_acquired: Optional[str] = Field(
        description="Date acquired (if present), e.g. 2022-03-15"
    )
    cost_new: Optional[float] = Field(description="Cost when new, e.g. 1200.0")
    cost_new_currency: Optional[str] = Field(
        description="Currency of cost_new, e.g. USD"
    )
    repair_estimate: Optional[float] = Field(description="Repair estimate, e.g. 350.0")
    repair_estimate_currency: Optional[str] = Field(
        description="Currency of repair_estimate, e.g. USD"
    )

    @staticmethod
    def example() -> "DamageAssessmentItem":
        """Return an empty instance with default placeholder values."""
        return DamageAssessmentItem(
            item_description="",
            date_acquired="",
            cost_new=0.0,
            cost_new_currency="",
            repair_estimate=0.0,
            repair_estimate_currency="",
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "item_description": self.item_description,
            "date_acquired": self.date_acquired,
            "cost_new": self.cost_new,
            "cost_new_currency": self.cost_new_currency,
            "repair_estimate": self.repair_estimate,
            "repair_estimate_currency": self.repair_estimate_currency,
        }


class DamageAssessment(BaseModel):
    """A class representing overall damage assessment."""

    items: Optional[List[DamageAssessmentItem]] = Field(
        description="List of damage assessment line items"
    )
    total_estimated_repair: Optional[float] = Field(
        description="Total estimated repair, e.g. 500.0"
    )
    total_estimated_repair_currency: Optional[str] = Field(
        description="Currency of total_estimated_repair, e.g. USD"
    )

    @staticmethod
    def example() -> "DamageAssessment":
        """Return an empty instance with default placeholder values."""
        return DamageAssessment(
            items=[DamageAssessmentItem.example()],
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


class SupportingDocuments(BaseModel):
    """A class representing supporting documents included with the claim."""

    photos_of_damage: Optional[bool] = Field(
        description="Whether photos of damage are included"
    )
    police_report_copy: Optional[bool] = Field(
        description="Whether a police report copy is included"
    )
    repair_shop_estimate: Optional[bool] = Field(
        description="Whether a repair shop estimate is included"
    )
    other: Optional[List[str]] = Field(description="Other supporting documents")

    @staticmethod
    def example() -> "SupportingDocuments":
        """Return an empty instance with default placeholder values."""
        return SupportingDocuments(
            photos_of_damage=False,
            police_report_copy=False,
            repair_shop_estimate=False,
            other=[],
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "photos_of_damage": self.photos_of_damage,
            "police_report_copy": self.police_report_copy,
            "repair_shop_estimate": self.repair_shop_estimate,
            "other": self.other or [],
        }


class Signature(BaseModel):
    """A class representing a signature field."""

    signatory: Optional[str] = Field(description="Name of the signatory")
    is_signed: Optional[bool] = Field(
        description="Indicates if the form is signed. GPT should check whether it has signature in image files. if there is Sign, fill it up as True"
    )

    @staticmethod
    def example() -> "Signature":
        """Return an empty instance with default placeholder values."""
        return Signature(signatory="", is_signed=False)

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {"signatory": self.signatory, "is_signed": self.is_signed}


class Declaration(BaseModel):
    """A class representing the claim declaration."""

    statement: Optional[str] = Field(description="Declaration statement text")
    signature: Optional[Signature] = Field(description="Signature")
    date: Optional[str] = Field(description="Signature date, e.g. 2025-12-01")

    @staticmethod
    def example() -> "Declaration":
        """Return an empty instance with default placeholder values."""
        return Declaration(statement="", signature=Signature.example(), date="")

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "statement": self.statement,
            "signature": self.signature.to_dict() if self.signature else None,
            "date": self.date,
        }


class SubmissionInstructions(BaseModel):
    """A class representing submission instructions."""

    submission_email: Optional[str] = Field(
        description="Submission email address, e.g. claims@contosoinsurance.com"
    )
    portal_url: Optional[str] = Field(description="Claims portal URL, if present")
    notes: Optional[str] = Field(description="Additional submission notes")

    @staticmethod
    def example() -> "SubmissionInstructions":
        """Return an empty instance with default placeholder values."""
        return SubmissionInstructions(submission_email="", portal_url="", notes="")

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "submission_email": self.submission_email,
            "portal_url": self.portal_url,
            "notes": self.notes,
        }


class AutoInsuranceClaimForm(BaseModel):
    """A class representing an auto insurance claim form."""

    insurance_company: Optional[str] = Field(
        description="Insurance company name, e.g. Contoso Insurance"
    )
    claim_number: Optional[str] = Field(description="Claim number, e.g. CLM987654")
    policy_number: Optional[str] = Field(description="Policy number, e.g. AUTO123456")

    policyholder_information: Optional[PolicyholderInformation] = Field(
        description="Policyholder information"
    )
    policy_details: Optional[PolicyDetails] = Field(description="Policy details")
    incident_details: Optional[IncidentDetails] = Field(description="Incident details")
    vehicle_information: Optional[VehicleInformation] = Field(
        description="Vehicle information"
    )
    damage_assessment: Optional[DamageAssessment] = Field(
        description="Damage assessment"
    )
    supporting_documents: Optional[SupportingDocuments] = Field(
        description="Supporting documents"
    )
    declaration: Optional[Declaration] = Field(description="Declaration")
    submission_instructions: Optional[SubmissionInstructions] = Field(
        description="Submission instructions"
    )

    @staticmethod
    def example() -> "AutoInsuranceClaimForm":
        """Return an empty instance with default placeholder values."""
        return AutoInsuranceClaimForm(
            insurance_company="",
            claim_number="",
            policy_number="",
            policyholder_information=PolicyholderInformation.example(),
            policy_details=PolicyDetails.example(),
            incident_details=IncidentDetails.example(),
            vehicle_information=VehicleInformation.example(),
            damage_assessment=DamageAssessment.example(),
            supporting_documents=SupportingDocuments.example(),
            declaration=Declaration.example(),
            submission_instructions=SubmissionInstructions.example(),
        )

    @staticmethod
    def from_json(json_str: str) -> "AutoInsuranceClaimForm":
        """Deserialize a JSON string into an AutoInsuranceClaimForm instance."""
        json_content = json.loads(json_str)

        def create_address(address: Optional[dict]) -> Optional[AutoClaimAddress]:
            if not address:
                return None
            return AutoClaimAddress(
                street=address.get("street"),
                city=address.get("city"),
                state=address.get("state"),
                postal_code=address.get("postal_code"),
                country=address.get("country"),
            )

        def create_policyholder(
            info: Optional[dict],
        ) -> Optional[PolicyholderInformation]:
            if not info:
                return None
            return PolicyholderInformation(
                name=info.get("name"),
                address=create_address(info.get("address")),
                phone=info.get("phone"),
                email=info.get("email"),
            )

        def create_policy_details(details: Optional[dict]) -> Optional[PolicyDetails]:
            if not details:
                return None
            return PolicyDetails(
                coverage_type=details.get("coverage_type"),
                effective_date=details.get("effective_date"),
                expiration_date=details.get("expiration_date"),
                deductible=details.get("deductible"),
                deductible_currency=details.get("deductible_currency"),
            )

        def create_incident(details: Optional[dict]) -> Optional[IncidentDetails]:
            if not details:
                return None
            return IncidentDetails(
                date_of_loss=details.get("date_of_loss"),
                time_of_loss=details.get("time_of_loss"),
                location=details.get("location"),
                cause_of_loss=details.get("cause_of_loss"),
                description=details.get("description"),
                police_report_filed=details.get("police_report_filed"),
                police_report_number=details.get("police_report_number"),
            )

        def create_vehicle(details: Optional[dict]) -> Optional[VehicleInformation]:
            if not details:
                return None
            return VehicleInformation(
                year=details.get("year"),
                make=details.get("make"),
                model=details.get("model"),
                trim=details.get("trim"),
                vin=details.get("vin"),
                license_plate=details.get("license_plate"),
                mileage=details.get("mileage"),
            )

        def create_damage_item(item: Optional[dict]) -> Optional[DamageAssessmentItem]:
            if not item:
                return None
            return DamageAssessmentItem(
                item_description=item.get("item_description"),
                date_acquired=item.get("date_acquired"),
                cost_new=item.get("cost_new"),
                cost_new_currency=item.get("cost_new_currency"),
                repair_estimate=item.get("repair_estimate"),
                repair_estimate_currency=item.get("repair_estimate_currency"),
            )

        def create_damage(details: Optional[dict]) -> Optional[DamageAssessment]:
            if not details:
                return None
            items_raw = details.get("items") or []
            items = [create_damage_item(i) for i in items_raw]
            items = [i for i in items if i is not None]
            return DamageAssessment(
                items=items,
                total_estimated_repair=details.get("total_estimated_repair"),
                total_estimated_repair_currency=details.get(
                    "total_estimated_repair_currency"
                ),
            )

        def create_supporting(details: Optional[dict]) -> Optional[SupportingDocuments]:
            if not details:
                return None
            return SupportingDocuments(
                photos_of_damage=details.get("photos_of_damage"),
                police_report_copy=details.get("police_report_copy"),
                repair_shop_estimate=details.get("repair_shop_estimate"),
                other=details.get("other") or [],
            )

        def create_signature(details: Optional[dict]) -> Optional[Signature]:
            if not details:
                return None
            return Signature(
                signatory=details.get("signatory"),
                is_signed=details.get("is_signed"),
            )

        def create_declaration(details: Optional[dict]) -> Optional[Declaration]:
            if not details:
                return None
            return Declaration(
                statement=details.get("statement"),
                signature=create_signature(details.get("signature")),
                date=details.get("date"),
            )

        def create_submission(
            details: Optional[dict],
        ) -> Optional[SubmissionInstructions]:
            if not details:
                return None
            return SubmissionInstructions(
                submission_email=details.get("submission_email"),
                portal_url=details.get("portal_url"),
                notes=details.get("notes"),
            )

        return AutoInsuranceClaimForm(
            insurance_company=json_content.get("insurance_company"),
            claim_number=json_content.get("claim_number"),
            policy_number=json_content.get("policy_number"),
            policyholder_information=create_policyholder(
                json_content.get("policyholder_information")
            ),
            policy_details=create_policy_details(json_content.get("policy_details")),
            incident_details=create_incident(json_content.get("incident_details")),
            vehicle_information=create_vehicle(json_content.get("vehicle_information")),
            damage_assessment=create_damage(json_content.get("damage_assessment")),
            supporting_documents=create_supporting(
                json_content.get("supporting_documents")
            ),
            declaration=create_declaration(json_content.get("declaration")),
            submission_instructions=create_submission(
                json_content.get("submission_instructions")
            ),
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "insurance_company": self.insurance_company,
            "claim_number": self.claim_number,
            "policy_number": self.policy_number,
            "policyholder_information": self.policyholder_information.to_dict()
            if self.policyholder_information
            else None,
            "policy_details": self.policy_details.to_dict()
            if self.policy_details
            else None,
            "incident_details": self.incident_details.to_dict()
            if self.incident_details
            else None,
            "vehicle_information": self.vehicle_information.to_dict()
            if self.vehicle_information
            else None,
            "damage_assessment": self.damage_assessment.to_dict()
            if self.damage_assessment
            else None,
            "supporting_documents": self.supporting_documents.to_dict()
            if self.supporting_documents
            else None,
            "declaration": self.declaration.to_dict() if self.declaration else None,
            "submission_instructions": self.submission_instructions.to_dict()
            if self.submission_instructions
            else None,
        }
