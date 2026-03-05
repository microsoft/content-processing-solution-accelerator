# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""Pydantic models for property loss and damage claim form data extraction.

Defines the schema used by the content processing pipeline to extract
structured fields from property insurance claim documents.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Address(BaseModel):
    """
    A class representing an address.

    Attributes:
        street: Street address
        city: City, e.g. New York
        state: State, e.g. NY
        postal_code: Postal code, e.g. 10001
        country: Country, e.g. USA
    """

    street: Optional[str] = Field(description="Street address, e.g. 123 Main St.")
    city: Optional[str] = Field(description="City, e.g. New York")
    state: Optional[str] = Field(description="State, e.g. NY")
    postal_code: Optional[str] = Field(description="Postal code, e.g. 10001")
    country: Optional[str] = Field(description="Country, e.g. USA")

    @staticmethod
    def example():
        """Return an empty instance with default placeholder values."""
        return Address(street="", city="", state="", postal_code="", country="")

    def to_dict(self):
        """Serialize to a plain dictionary."""
        return {
            "street": self.street,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
        }


class PolicyClaimInfo(BaseModel):
    """
    A class representing policy and claim information.

    Attributes:
        first_name: First name of the policy holder.
        last_name: Last name of the policy holder.
        telephone_number: Telephone number of the policy holder.
        policy_number: Policy number.
        coverage_type: Type of coverage.
        claim_number: Claim number.
        policy_effective_date: Policy effective date.
        policy_expiration_date: Policy expiration date.
        damage_deductible: Damage deductible.
        date_of_damage_loss: Date of damage/loss.
        time_of_loss: Time of loss.
        date_prepared: Date prepared.
        property_address: Address of the property.
        mailing_address: Mailing address.
    """

    first_name: Optional[str] = Field(description="First name of the policy holder")
    last_name: Optional[str] = Field(description="Last name of the policy holder")
    telephone_number: Optional[str] = Field(
        description="Telephone number of the policy holder"
    )
    policy_number: Optional[str] = Field(description="Policy number")
    coverage_type: Optional[str] = Field(description="Type of coverage")
    claim_number: Optional[str] = Field(description="Claim number")
    policy_effective_date: Optional[str] = Field(
        description="Policy effective date, e.g. 2023-01-01"
    )
    policy_expiration_date: Optional[str] = Field(
        description="Policy expiration date, e.g. 2024-01-01"
    )
    damage_deductible: Optional[float] = Field(
        description="Damage deductible e.g. 500.0"
    )
    damage_deductible_currency: Optional[str] = Field(
        description="Currency of the damage deductible e.g. USD, just in case it can't be extracted, the value should be got by GPT from Policyholder's Property Address"
    )
    date_of_damage_loss: Optional[str] = Field(
        description="Date of damage/loss e.g. 2023-01-01"
    )
    time_of_loss: Optional[str] = Field(description="Time of loss e.g. 14:30")
    date_prepared: Optional[str] = Field(description="Date prepared e.g. 2023-01-01")
    property_address: Optional[Address] = Field(
        description="Address of the property e.g. 123 Main St., City, Country"
    )
    mailing_address: Optional[Address] = Field(
        description="Mailing address e.g. 456 Elm St., City, Country"
    )

    @staticmethod
    def example():
        """Return an empty instance with default placeholder values."""
        return PolicyClaimInfo(
            first_name="",
            last_name="",
            telephone_number="",
            policy_number="",
            coverage_type="",
            claim_number="",
            policy_effective_date="",
            policy_expiration_date="",
            damage_deductible=0.0,
            damage_deductible_currency="",
            date_of_damage_loss="",
            time_of_loss="",
            date_prepared="",
            property_address=Address.example(),
            mailing_address=Address.example(),
        )

    def to_dict(self):
        """Serialize to a plain dictionary."""
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "telephone_number": self.telephone_number,
            "policy_number": self.policy_number,
            "coverage_type": self.coverage_type,
            "claim_number": self.claim_number,
            "policy_effective_date": self.policy_effective_date,
            "policy_expiration_date": self.policy_expiration_date,
            "damage_deductible": self.damage_deductible,
            "damage_deductible_currency": self.damage_deductible_currency,
            "date_of_damage_loss": self.date_of_damage_loss,
            "time_of_loss": self.time_of_loss,
            "date_prepared": self.date_prepared,
            "property_address": self.property_address.to_dict()
            if self.property_address
            else None,
            "mailing_address": self.mailing_address.to_dict()
            if self.mailing_address
            else None,
        }


class PropertyClaimDetails(BaseModel):
    """
    A class representing property claim details.

    Attributes:
        item: Item name.
        description: Description of the item.
        date_acquired: Date the item was acquired.
        cost_new: Cost of the item when new.
        cost_new_currency: Currency of the cost new.
        replacement_repair: Replacement or repair cost.
        replacement_repair_currency: Currency of the replacement/repair cost.
    """

    item: Optional[str] = Field(description="Item name")
    description: Optional[str] = Field(description="Description of the item")
    date_acquired: Optional[str] = Field(
        description="Date the item was acquired e.g. 2023-01-01"
    )
    cost_new: Optional[float] = Field(
        description="Cost of the item when new e.g. 1000.0"
    )
    cost_new_currency: Optional[str] = Field(
        description="Currency of the cost new e.g. USD. just in case it can't be extracted, the value should be got by GPT from Policyholder's Property Address"
    )
    replacement_repair: Optional[float] = Field(
        description="Replacement or repair cost e.g. 500.0."
    )
    replacement_repair_currency: Optional[str] = Field(
        description="Currency of the replacement/repair cost e.g. USD, just in case it can't be extracted, the value should be got by GPT from Policyholder's Property Address"
    )

    @staticmethod
    def example():
        """Return an empty instance with default placeholder values."""
        return PropertyClaimDetails(
            item="",
            description="",
            date_acquired="",
            cost_new=0.0,
            cost_new_currency="",
            replacement_repair=0.0,
            replacement_repair_currency="",
        )

    def to_dict(self):
        """Serialize to a plain dictionary."""
        return {
            "item": self.item,
            "description": self.description,
            "date_acquired": self.date_acquired,
            "cost_new": self.cost_new,
            "cost_new_currency": self.cost_new_currency,
            "replacement_repair": self.replacement_repair,
            "replacement_repair_currency": self.replacement_repair_currency,
        }


class Signature(BaseModel):
    """Signature block on a property claim form.

    Attributes:
        signatory: Name of the person who signed the form.
        is_signed: Indicates if the form is signed.
    """

    signatory: Optional[str] = Field(
        description="Name of the person who signed the form"
    )
    is_signed: Optional[bool] = Field(
        description="Indicates if the form is signed. GPT should check whether it has signature in image files. if there is Sign, fill it up as True"
    )

    @staticmethod
    def example():
        """Return an empty Signature with default placeholder values."""
        return Signature(signatory="", is_signed=False)

    def to_dict(self):
        """Serialize to a plain dictionary."""
        return {"signatory": self.signatory, "is_signed": self.is_signed}


class ClaimsDisclaimer(BaseModel):
    """
    A class representing claims disclaimer.
    When Text values in the fields has some noise characters, it should be removed by GPT.
    For example, "Apple Computer\" should be "Apple Computer".

    Attributes:
        disclaimer: Disclaimer information.
        policyholder_signature: Signature of the policyholder.
        date: Date of the signature.
    """

    disclaimer: Optional[str] = Field(description="Disclaimer information")
    policyholder_signature: Optional[Signature] = Field(
        description="Signature of the policyholder"
    )
    date: Optional[str] = Field(description="Date of the signature e.g. 2023-01-01")

    @staticmethod
    def example():
        """Return an empty instance with default placeholder values."""
        return ClaimsDisclaimer(
            disclaimer="",
            policyholder_signature=Signature.example(),
            date="",
        )

    def to_dict(self):
        """Serialize to a plain dictionary."""
        return {
            "disclaimer": self.disclaimer,
            "policyholder_signature": self.policyholder_signature,
            "date": self.date,
        }


class PropertyLossDamageClaimForm(BaseModel):
    """
    A class representing a property loss or damage claim form.

    Attributes:
        policy_claim_info: Policy and claim information.
        property_claim_details: List of property claim details.
        claims_disclaimer: Claims disclaimer information.
    """

    policy_claim_info: Optional[PolicyClaimInfo] = Field(
        description="Policy and claim information"
    )
    property_claim_details: Optional[List[PropertyClaimDetails]] = Field(
        description="List of property claim details"
    )
    claims_disclaimer: Optional[ClaimsDisclaimer] = Field(
        description="Claims disclaimer information"
    )

    @staticmethod
    def example():
        """Return an empty instance with default placeholder values."""
        return PropertyLossDamageClaimForm(
            policy_claim_info=PolicyClaimInfo.example(),
            property_claim_details=[PropertyClaimDetails.example()],
            claims_disclaimer=ClaimsDisclaimer.example(),
        )

    def to_dict(self):
        """Serialize to a plain dictionary."""
        return {
            "policy_claim_info": self.policy_claim_info.to_dict()
            if self.policy_claim_info
            else None,
            "property_claim_details": [
                detail.to_dict() for detail in self.property_claim_details
            ]
            if self.property_claim_details
            else [],
            "claims_disclaimer": self.claims_disclaimer.to_dict()
            if self.claims_disclaimer
            else None,
        }
