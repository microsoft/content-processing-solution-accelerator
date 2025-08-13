from __future__ import annotations
import json
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Address(BaseModel):
    """
    Represents a structured postal address for a party in the MSA.
    """
    street: Optional[str] = Field(description="Street address, e.g., 123 Main St.")
    city: Optional[str] = Field(description="City, e.g., Chicago")
    state: Optional[str] = Field(description="State or province abbreviation, e.g., IL")
    postal_code: Optional[str] = Field(description="Postal/ZIP code, e.g., 60601")
    country: Optional[str] = Field(description="Country, e.g., USA")

    @staticmethod
    def example():
        return Address(
            street="123 Main St.",
            city="Chicago",
            state="IL",
            postal_code="60601",
            country="USA"
        )

    def to_dict(self):
        return {
            "street": self.street,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country
        }


class PartyDetails(BaseModel):
    """
    Represents one party to the MSA (either the client or the vendor).
    """
    company_name: Optional[str] = Field(
        description="Legal name of the company, e.g., 'Allina Health System'"
    )
    address: Optional[Address] = Field(
        description="Registered business address of the company"
    )
    contact_name: Optional[str] = Field(
        description="Primary contact person for the contract, e.g., 'John Doe'"
    )
    contact_email: Optional[str] = Field(
        description="Email address of the primary contact, e.g., 'john.doe@example.com'"
    )
    signatory_name: Optional[str] = Field(
        description="Full legal name of the authorized signatory, e.g., 'Jane Smith'"
    )
    signatory_title: Optional[str] = Field(
        description="Job title of the signatory, e.g., 'Chief Procurement Officer'"
    )
    signatory_email: Optional[str] = Field(
        description="Email address of the signatory, e.g., 'jane.smith@example.com'"
    )
    signatory_role_id: Optional[str] = Field(
        description="Signer role ID from DocuSign/CRM if available, e.g., 'Signer1'"
    )
    sign_date: Optional[str] = Field(
        description="Date the signatory signed the agreement, format YYYY-MM-DD"
    )

    @staticmethod
    def example():
        return PartyDetails(
            company_name="Example Client Inc.",
            address=Address.example(),
            contact_name="John Doe",
            contact_email="john.doe@example.com",
            signatory_name="Jane Smith",
            signatory_title="Chief Legal Officer",
            signatory_email="jane.smith@example.com",
            signatory_role_id="Signer1",
            sign_date=datetime.now().strftime("%Y-%m-%d")
        )

    def to_dict(self):
        return {
            "company_name": self.company_name,
            "address": self.address.to_dict() if self.address else None,
            "contact_name": self.contact_name,
            "contact_email": self.contact_email,
            "signatory_name": self.signatory_name,
            "signatory_title": self.signatory_title,
            "signatory_email": self.signatory_email,
            "signatory_role_id": self.signatory_role_id,
            "sign_date": self.sign_date
        }


class MasterServiceAgreement(BaseModel):
    """
    A class representing a Master Service Agreement (MSA).
    Schema for extracting and structuring data from Master Service Agreements.
    Designed for the Microsoft Content Processing Solution Accelerator.

    Attributes:
        document_name: Original filename of the MSA document
        agreement_id: Unique identifier for the MSA in CRM or DocuSign
        created_by: Name or email of the user who created the MSA record
        created_date: Date the MSA record was created
        location_path: Storage location path for the MSA
        account_id: CRM/Salesforce account ID
        account_name: Name of the customer organization
        template_used: Type of contract template used
        client_party: Details of the client organization signing the MSA
        vendor_party: Details of the vendor signing the MSA
        effective_date: Date the agreement becomes effective
        termination_date: Date the agreement terminates (if applicable)
        term_for_convenience_days: Number of days notice required for termination without cause
        automatic_renewal: Whether the agreement automatically renews
        payment_terms: Agreed payment terms
        damage_cap_amount: Monetary cap on damages
        governing_law: Jurisdiction governing the contract
        data_protection_agreement: Whether a Data Protection Agreement (DPA) is included
        business_associate_agreement: Whether a Business Associate Agreement (BAA) is included
        assignment_clause: Whether assignment of the contract is permitted
        signature_process: Status of the DocuSign signature process
        source_system: Originating system for the record
        record_link: Direct link to the CRM or source system record
    """

    # Contract Metadata
    document_name: Optional[str] = Field(
        description="Original filename of the MSA document, e.g., 'Mimeo Inc-3Cloud-MSA_07-23-2025.pdf'"
    )
    agreement_id: Optional[str] = Field(
        description="Unique identifier for the MSA in CRM or DocuSign, e.g., 'MSA-2025-001'"
    )
    created_by: Optional[str] = Field(
        description="Name or email of the user who created the MSA record, e.g., 'khummerich@3cloudsolutions.com'"
    )
    created_date: Optional[str] = Field(
        description="Date the MSA record was created, format YYYY-MM-DD"
    )
    location_path: Optional[str] = Field(
        description="Storage location path for the MSA, e.g., '/3Cloud/Contracts/MSA/'"
    )
    account_id: Optional[str] = Field(
        description="CRM/Salesforce account ID, e.g., '001f400000SOG47AAH'"
    )
    account_name: Optional[str] = Field(
        description="Name of the customer organization, e.g., 'Noble Drilling Corp'"
    )
    template_used: Optional[str] = Field(
        description="Type of contract template used, e.g., 'Customer Template', '3Cloud Template'"
    )

    # Parties
    client_party: Optional[PartyDetails] = Field(
        description="Details of the client organization signing the MSA"
    )
    vendor_party: Optional[PartyDetails] = Field(
        description="Details of the vendor (3Cloud) signing the MSA"
    )

    # Agreement Terms
    effective_date: Optional[str] = Field(
        description="Date the agreement becomes effective, format YYYY-MM-DD"
    )
    termination_date: Optional[str] = Field(
        description="Date the agreement terminates (if applicable), format YYYY-MM-DD"
    )
    term_for_convenience_days: Optional[int] = Field(
        description="Number of days notice required for termination without cause, e.g., 30"
    )
    automatic_renewal: Optional[bool] = Field(
        description="Whether the agreement automatically renews at the end of its term"
    )
    payment_terms: Optional[str] = Field(
        description="Agreed payment terms, e.g., 'thirty (30)'"
    )
    damage_cap_amount: Optional[float] = Field(
        description="Monetary cap on damages, e.g., 1000000.00"
    )
    governing_law: Optional[str] = Field(
        description="Jurisdiction governing the contract, e.g., 'Illinois'"
    )
    data_protection_agreement: Optional[bool] = Field(
        description="Indicates whether a Data Protection Agreement (DPA) is included"
    )
    business_associate_agreement: Optional[bool] = Field(
        description="Indicates whether a Business Associate Agreement (BAA) is included"
    )
    assignment_clause: Optional[bool] = Field(
        description="Indicates whether assignment of the contract is permitted"
    )

    # System/Workflow Tracking
    signature_process: Optional[str] = Field(
        description="Status of the DocuSign signature process, e.g., 'Fully Executed'"
    )
    source_system: Optional[str] = Field(
        description="Originating system for the record, e.g., 'Salesforce', 'DocuSign'"
    )
    record_link: Optional[str] = Field(
        description="Direct link to the CRM or source system record"
    )

    @staticmethod
    def example():
        """
        Creates an example MasterServiceAgreement object.

        Returns:
            MasterServiceAgreement: An example MasterServiceAgreement object.
        """
        return MasterServiceAgreement(
            document_name="Client-3Cloud-MSA.pdf",
            agreement_id="MSA-2025-001",
            created_by="user@example.com",
            created_date=datetime.now().strftime("%Y-%m-%d"),
            location_path="/3Cloud/Contracts/MSA/",
            account_id="001XYZ123",
            account_name="Example Client Inc.",
            template_used="3Cloud Template",
            client_party=PartyDetails.example(),
            vendor_party=PartyDetails.example(),
            effective_date=datetime.now().strftime("%Y-%m-%d"),
            termination_date="2027-07-23",
            term_for_convenience_days=30,
            automatic_renewal=True,
            payment_terms="thirty (30)",
            damage_cap_amount=1000000.00,
            governing_law="Illinois",
            data_protection_agreement=True,
            business_associate_agreement=False,
            assignment_clause=True,
            signature_process="Fully Executed",
            source_system="DocuSign",
            record_link="https://crm.example.com/record/001XYZ123"
        )

    @staticmethod
    def from_json(json_str: str):
        """
        Creates a MasterServiceAgreement object from a JSON string.

        Args:
            json_str: The JSON string representing the MasterServiceAgreement object.

        Returns:
            MasterServiceAgreement: A MasterServiceAgreement object.
        """
        json_content = json.loads(json_str)

        def create_address(addr):
            """
            Creates an Address object from a dictionary.

            Args:
                addr: A dictionary representing an Address object.

            Returns:
                Address: An Address object or None if addr is None.
            """
            if addr is None:
                return None
            return Address(
                street=addr.get("street"),
                city=addr.get("city"),
                state=addr.get("state"),
                postal_code=addr.get("postal_code"),
                country=addr.get("country")
            )

        def create_party(party):
            """
            Creates a PartyDetails object from a dictionary.

            Args:
                party: A dictionary representing a PartyDetails object.

            Returns:
                PartyDetails: A PartyDetails object or None if party is None.
            """
            if party is None:
                return None
            return PartyDetails(
                company_name=party.get("company_name"),
                address=create_address(party.get("address")),
                contact_name=party.get("contact_name"),
                contact_email=party.get("contact_email"),
                signatory_name=party.get("signatory_name"),
                signatory_title=party.get("signatory_title"),
                signatory_email=party.get("signatory_email"),
                signatory_role_id=party.get("signatory_role_id"),
                sign_date=party.get("sign_date")
            )

        return MasterServiceAgreement(
            document_name=json_content.get("document_name"),
            agreement_id=json_content.get("agreement_id"),
            created_by=json_content.get("created_by"),
            created_date=json_content.get("created_date"),
            location_path=json_content.get("location_path"),
            account_id=json_content.get("account_id"),
            account_name=json_content.get("account_name"),
            template_used=json_content.get("template_used"),
            client_party=create_party(json_content.get("client_party")),
            vendor_party=create_party(json_content.get("vendor_party")),
            effective_date=json_content.get("effective_date"),
            termination_date=json_content.get("termination_date"),
            term_for_convenience_days=json_content.get("term_for_convenience_days"),
            automatic_renewal=json_content.get("automatic_renewal"),
            payment_terms=json_content.get("payment_terms"),
            damage_cap_amount=json_content.get("damage_cap_amount"),
            governing_law=json_content.get("governing_law"),
            data_protection_agreement=json_content.get("data_protection_agreement"),
            business_associate_agreement=json_content.get("business_associate_agreement"),
            assignment_clause=json_content.get("assignment_clause"),
            signature_process=json_content.get("signature_process"),
            source_system=json_content.get("source_system"),
            record_link=json_content.get("record_link")
        )

    def to_dict(self):
        """
        Converts the MasterServiceAgreement object to a dictionary.

        Returns:
            dict: The MasterServiceAgreement object as a dictionary.
        """
        return {
            "document_name": self.document_name,
            "agreement_id": self.agreement_id,
            "created_by": self.created_by,
            "created_date": self.created_date,
            "location_path": self.location_path,
            "account_id": self.account_id,
            "account_name": self.account_name,
            "template_used": self.template_used,
            "client_party": self.client_party.to_dict() if self.client_party else None,
            "vendor_party": self.vendor_party.to_dict() if self.vendor_party else None,
            "effective_date": self.effective_date,
            "termination_date": self.termination_date,
            "term_for_convenience_days": self.term_for_convenience_days,
            "automatic_renewal": self.automatic_renewal,
            "payment_terms": self.payment_terms,
            "damage_cap_amount": f"{self.damage_cap_amount:.2f}" if self.damage_cap_amount is not None else None,
            "governing_law": self.governing_law,
            "data_protection_agreement": self.data_protection_agreement,
            "business_associate_agreement": self.business_associate_agreement,
            "assignment_clause": self.assignment_clause,
            "signature_process": self.signature_process,
            "source_system": self.source_system,
            "record_link": self.record_link
        }
