# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""Pydantic models for damaged vehicle image assessment data extraction.

Defines the schema used by the content processing pipeline to extract
structured damage information from vehicle photographs.
"""

from __future__ import annotations

import json
from typing import List, Optional

from pydantic import BaseModel, Field


class ImageInfo(BaseModel):
    """Metadata about an input image.

    Note: Most fields may be unknown unless provided by the caller or extracted from EXIF.
    """

    filename: Optional[str] = Field(description="Original filename of the image")
    content_type: Optional[str] = Field(description="MIME type, e.g. image/jpeg")
    width: Optional[int] = Field(description="Image width in pixels")
    height: Optional[int] = Field(description="Image height in pixels")
    capture_datetime: Optional[str] = Field(
        description="Capture datetime if available, e.g. 2025-11-28T14:15:00"
    )

    @staticmethod
    def example() -> "ImageInfo":
        """Return an empty instance with default placeholder values."""
        return ImageInfo(
            filename="",
            content_type="",
            width=0,
            height=0,
            capture_datetime="",
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "filename": self.filename,
            "content_type": self.content_type,
            "width": self.width,
            "height": self.height,
            "capture_datetime": self.capture_datetime,
        }


class VehicleAppearance(BaseModel):
    """Visible vehicle identification extracted from the image.

    Guidance:
    - Prefer fields that can be seen. If uncertain, leave null.
    - Do not guess VIN from images.
    """

    vehicle_type: Optional[str] = Field(description="Vehicle type, e.g. sedan, SUV")
    make: Optional[str] = Field(description="Vehicle make, e.g. Toyota")
    model: Optional[str] = Field(description="Vehicle model, e.g. Camry")
    trim: Optional[str] = Field(description="Vehicle trim, e.g. SE")
    model_year: Optional[int] = Field(description="Vehicle model year, e.g. 2022")
    color: Optional[str] = Field(description="Vehicle color, e.g. silver")

    license_plate_visible: Optional[bool] = Field(
        description="Whether the license plate is visible in the image"
    )
    license_plate_text: Optional[str] = Field(
        description="License plate text if clearly readable; otherwise null"
    )

    visible_vehicle_parts: Optional[List[str]] = Field(
        description=(
            "List of vehicle parts/panels actually visible in this image "
            "given the camera angle, e.g. ['hood', 'front bumper', "
            "'front-left fender', 'front-left headlight']. "
            "Only parts that can be seen should be listed. "
            "Left/right MUST use the VEHICLE's own frame of reference "
            "and MUST match the side in camera_viewpoint.view_angle."
        )
    )

    @staticmethod
    def example() -> "VehicleAppearance":
        """Return an empty instance with default placeholder values."""
        return VehicleAppearance(
            vehicle_type="",
            make="",
            model="",
            trim="",
            model_year=0,
            color="",
            license_plate_visible=False,
            license_plate_text="",
            visible_vehicle_parts=[],
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "vehicle_type": self.vehicle_type,
            "make": self.make,
            "model": self.model,
            "trim": self.trim,
            "model_year": self.model_year,
            "color": self.color,
            "license_plate_visible": self.license_plate_visible,
            "license_plate_text": self.license_plate_text,
            "visible_vehicle_parts": self.visible_vehicle_parts or [],
        }


class CameraViewpoint(BaseModel):
    """Scene-level camera perspective.

    Describes the overall camera position relative to the scene. For
    multi-vehicle images the per-vehicle view angle and spatial reasoning
    live on each ``VehicleAssessment`` instead.

    Attributes:
        description: Free-text summary of the camera position.
    """

    description: Optional[str] = Field(
        description=(
            "Free-text description of the camera position relative "
            "to the overall scene, e.g. 'Side view of a rear-end "
            "collision between two sedans on a residential street.'"
        )
    )

    @staticmethod
    def example() -> "CameraViewpoint":
        """Return an empty instance with default placeholder values."""
        return CameraViewpoint(description="")

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "description": self.description,
        }


class DamageBoundingBox(BaseModel):
    """Bounding box in normalized image coordinates [0..1]."""

    x_min: Optional[float] = Field(description="Left edge in [0..1]")
    y_min: Optional[float] = Field(description="Top edge in [0..1]")
    x_max: Optional[float] = Field(description="Right edge in [0..1]")
    y_max: Optional[float] = Field(description="Bottom edge in [0..1]")

    @staticmethod
    def example() -> "DamageBoundingBox":
        """Return an empty instance with default placeholder values."""
        return DamageBoundingBox(x_min=0.0, y_min=0.0, x_max=0.0, y_max=0.0)

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "x_min": self.x_min,
            "y_min": self.y_min,
            "x_max": self.x_max,
            "y_max": self.y_max,
        }


class DamageRegion(BaseModel):
    """A detected region of damage on the vehicle."""

    location_on_vehicle: Optional[str] = Field(
        description=(
            "Location on the vehicle using the VEHICLE's own left/right "
            "(driver-perspective facing forward). "
            "The side MUST match camera_viewpoint.view_angle. "
            "Examples: 'front-left fender', 'rear-right quarter panel'."
        )
    )
    damage_types: Optional[List[str]] = Field(
        description="Damage types, e.g. ['scratch','dent','crack','paint-transfer']"
    )
    severity: Optional[str] = Field(
        description="Severity label, e.g. minor, moderate, severe"
    )
    description: Optional[str] = Field(
        description="Free-text description of the damage"
    )

    bounding_box: Optional[DamageBoundingBox] = Field(
        description="Approx bounding box of the damage area (normalized coordinates)"
    )

    confidence: Optional[float] = Field(
        description="Confidence score in [0..1] for this damage region"
    )

    @staticmethod
    def example() -> "DamageRegion":
        """Return an empty instance with default placeholder values."""
        return DamageRegion(
            location_on_vehicle="",
            damage_types=[],
            severity="",
            description="",
            bounding_box=DamageBoundingBox.example(),
            confidence=0.0,
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "location_on_vehicle": self.location_on_vehicle,
            "damage_types": self.damage_types or [],
            "severity": self.severity,
            "description": self.description,
            "bounding_box": self.bounding_box.to_dict() if self.bounding_box else None,
            "confidence": self.confidence,
        }


class OverallDamageAssessment(BaseModel):
    """Overall assessment across the full image."""

    has_visible_damage: Optional[bool] = Field(
        description="Whether any damage is visible"
    )
    overall_severity: Optional[str] = Field(
        description="Overall severity label, e.g. minor, moderate, severe"
    )

    affected_parts: Optional[List[str]] = Field(
        description=(
            "Affected parts/panels using the VEHICLE's own left/right. "
            "Side labels MUST match camera_viewpoint.view_angle."
        )
    )

    estimated_repair_complexity: Optional[str] = Field(
        description="Rough complexity, e.g. cosmetic_only, panel_repair, replacement_likely"
    )

    notes: Optional[str] = Field(
        description="Notes or caveats, e.g. lighting/angle limitations"
    )

    @staticmethod
    def example() -> "OverallDamageAssessment":
        """Return an empty instance with default placeholder values."""
        return OverallDamageAssessment(
            has_visible_damage=False,
            overall_severity="",
            affected_parts=[],
            estimated_repair_complexity="",
            notes="",
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "has_visible_damage": self.has_visible_damage,
            "overall_severity": self.overall_severity,
            "affected_parts": self.affected_parts or [],
            "estimated_repair_complexity": self.estimated_repair_complexity,
            "notes": self.notes,
        }


class VehicleAssessment(BaseModel):
    """Per-vehicle damage assessment extracted from an image.

    Groups appearance, damage regions, and overall assessment for a single
    vehicle detected in the photograph.

    Attributes:
        vehicle_id: Human-readable identifier distinguishing this vehicle.
        vehicle_appearance: Visible vehicle identification.
        damage_regions: Detected damage regions for this vehicle.
        overall_assessment: Overall damage assessment for this vehicle.
    """

    vehicle_id: Optional[str] = Field(
        description=(
            "A short human-readable identifier for this vehicle, "
            "e.g. 'Vehicle 1 - silver sedan (front-left)'. "
            "Use color, type, and position to distinguish vehicles."
        )
    )
    spatial_reasoning: Optional[str] = Field(
        description=(
            "MANDATORY per-vehicle chain-of-thought reasoning. "
            "Must answer IN ORDER: "
            "(1) Can I see this vehicle's FRONT (grille/headlights) or "
            "REAR (tail lights/trunk)? "
            "(2) Which direction does the car FACE in the image — LEFT "
            "or RIGHT? The grille points the same way the car faces. "
            "If only rear visible, the car faces AWAY from the tail lights. "
            "(3) The facing direction IS the side you see: "
            "faces RIGHT + FRONT = front-right (see RIGHT side), "
            "faces RIGHT + REAR  = rear-right  (see RIGHT side), "
            "faces LEFT  + FRONT = front-left  (see LEFT side), "
            "faces LEFT  + REAR  = rear-left   (see LEFT side). "
            "(4) FALLBACK for pure side view only: use steering wheel "
            "position (LHD: left, RHD: right)."
        )
    )
    view_angle: Optional[str] = Field(
        description=(
            "Camera viewing angle for THIS vehicle. "
            "Must be one of: front, front-left, front-right, "
            "left-side, right-side, rear-left, rear-right, rear, "
            "top, underneath, interior, unknown. "
            "Left/right = VEHICLE's own left/right (driver-perspective)."
        )
    )
    vehicle_appearance: Optional[VehicleAppearance] = Field(
        description="Visible vehicle identification for this vehicle"
    )
    damage_regions: Optional[List[DamageRegion]] = Field(
        description="List of detected damage regions for this vehicle"
    )
    overall_assessment: Optional[OverallDamageAssessment] = Field(
        description="Overall damage assessment for this vehicle"
    )

    @staticmethod
    def example() -> "VehicleAssessment":
        """Return an empty instance with default placeholder values."""
        return VehicleAssessment(
            vehicle_id="",
            spatial_reasoning="",
            view_angle="",
            vehicle_appearance=VehicleAppearance.example(),
            damage_regions=[DamageRegion.example()],
            overall_assessment=OverallDamageAssessment.example(),
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "vehicle_id": self.vehicle_id,
            "spatial_reasoning": self.spatial_reasoning,
            "view_angle": self.view_angle,
            "vehicle_appearance": self.vehicle_appearance.to_dict()
            if self.vehicle_appearance
            else None,
            "damage_regions": [r.to_dict() for r in (self.damage_regions or [])],
            "overall_assessment": self.overall_assessment.to_dict()
            if self.overall_assessment
            else None,
        }


class DamagedVehicleImageAssessment(BaseModel):
    """Schema for extracting damaged vehicle information from an image.

    Supports single- and multi-vehicle images. Each vehicle detected in the
    photograph gets its own entry in the ``vehicles`` list.

    Attributes:
        image_info: Image metadata (shared across all vehicles).
        camera_viewpoint: Camera perspective relative to the scene.
        vehicle_count: Number of distinct vehicles detected in the image.
        vehicles: Per-vehicle assessment list.
    """

    image_info: Optional[ImageInfo] = Field(description="Image metadata")
    camera_viewpoint: Optional[CameraViewpoint] = Field(
        description=(
            "Camera perspective relative to the scene. "
            "MUST be determined BEFORE labelling any damage "
            "locations so that left/right orientation is anchored "
            "to each vehicle's own frame of reference."
        )
    )
    vehicle_count: Optional[int] = Field(
        description=(
            "Number of distinct vehicles detected in the image. "
            "Must equal the length of the vehicles list."
        )
    )
    vehicles: Optional[List[VehicleAssessment]] = Field(
        description=(
            "Per-vehicle damage assessments. One entry per vehicle "
            "detected in the image. For single-vehicle images this "
            "list contains exactly one item."
        )
    )
    consistency_check: Optional[str] = Field(
        description=(
            "MANDATORY self-verification with two checks. "
            "CHECK 1 — Per-vehicle: For each vehicle, state the side from "
            "its view_angle, then list every left/right label in its "
            "visible_vehicle_parts, damage_regions, and affected_parts. "
            "Confirm they ALL match. "
            "CHECK 2 — Cross-vehicle: If multiple vehicles are photographed "
            "from the same camera position, they must ALL show the SAME "
            "vehicle side (e.g. all LEFT or all RIGHT). If any vehicle "
            "shows the opposite side, re-examine its spatial_reasoning "
            "step 2 (confirm the facing direction is correct) and correct it. "
            "State the final side for each vehicle and confirm consistency."
        )
    )

    @staticmethod
    def example() -> "DamagedVehicleImageAssessment":
        """Return an empty instance with default placeholder values."""
        return DamagedVehicleImageAssessment(
            image_info=ImageInfo.example(),
            camera_viewpoint=CameraViewpoint.example(),
            vehicle_count=1,
            vehicles=[VehicleAssessment.example()],
            consistency_check="",
        )

    @staticmethod
    def from_json(json_str: str) -> "DamagedVehicleImageAssessment":
        """Deserialize a JSON string into a DamagedVehicleImageAssessment instance."""
        json_content = json.loads(json_str)

        def create_image_info(details: Optional[dict]) -> Optional[ImageInfo]:
            if not details:
                return None
            return ImageInfo(
                filename=details.get("filename"),
                content_type=details.get("content_type"),
                width=details.get("width"),
                height=details.get("height"),
                capture_datetime=details.get("capture_datetime"),
            )

        def create_viewpoint(
            details: Optional[dict],
        ) -> Optional[CameraViewpoint]:
            if not details:
                return None
            return CameraViewpoint(
                description=details.get("description"),
            )

        def create_appearance(
            details: Optional[dict],
        ) -> Optional[VehicleAppearance]:
            if not details:
                return None
            return VehicleAppearance(
                vehicle_type=details.get("vehicle_type"),
                make=details.get("make"),
                model=details.get("model"),
                trim=details.get("trim"),
                model_year=details.get("model_year"),
                color=details.get("color"),
                license_plate_visible=details.get("license_plate_visible"),
                license_plate_text=details.get("license_plate_text"),
                visible_vehicle_parts=details.get("visible_vehicle_parts") or [],
            )

        def create_bbox(details: Optional[dict]) -> Optional[DamageBoundingBox]:
            if not details:
                return None
            return DamageBoundingBox(
                x_min=details.get("x_min"),
                y_min=details.get("y_min"),
                x_max=details.get("x_max"),
                y_max=details.get("y_max"),
            )

        def create_region(details: Optional[dict]) -> Optional[DamageRegion]:
            if not details:
                return None
            return DamageRegion(
                location_on_vehicle=details.get("location_on_vehicle"),
                damage_types=details.get("damage_types") or [],
                severity=details.get("severity"),
                description=details.get("description"),
                bounding_box=create_bbox(details.get("bounding_box")),
                confidence=details.get("confidence"),
            )

        def create_overall(
            details: Optional[dict],
        ) -> Optional[OverallDamageAssessment]:
            if not details:
                return None
            return OverallDamageAssessment(
                has_visible_damage=details.get("has_visible_damage"),
                overall_severity=details.get("overall_severity"),
                affected_parts=details.get("affected_parts") or [],
                estimated_repair_complexity=details.get("estimated_repair_complexity"),
                notes=details.get("notes"),
            )

        def create_vehicle_assessment(
            details: Optional[dict],
        ) -> Optional[VehicleAssessment]:
            if not details:
                return None
            regions_raw = details.get("damage_regions") or []
            regions = [r for r in (create_region(r) for r in regions_raw) if r]
            return VehicleAssessment(
                vehicle_id=details.get("vehicle_id"),
                spatial_reasoning=details.get("spatial_reasoning"),
                view_angle=details.get("view_angle"),
                vehicle_appearance=create_appearance(details.get("vehicle_appearance")),
                damage_regions=regions,
                overall_assessment=create_overall(details.get("overall_assessment")),
            )

        vehicles_raw = json_content.get("vehicles") or []
        vehicles = [
            v for v in (create_vehicle_assessment(v) for v in vehicles_raw) if v
        ]

        return DamagedVehicleImageAssessment(
            image_info=create_image_info(json_content.get("image_info")),
            camera_viewpoint=create_viewpoint(json_content.get("camera_viewpoint")),
            vehicle_count=json_content.get("vehicle_count"),
            vehicles=vehicles,
            consistency_check=json_content.get("consistency_check"),
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "image_info": self.image_info.to_dict() if self.image_info else None,
            "camera_viewpoint": self.camera_viewpoint.to_dict()
            if self.camera_viewpoint
            else None,
            "vehicle_count": self.vehicle_count,
            "vehicles": [v.to_dict() for v in (self.vehicles or [])],
            "consistency_check": self.consistency_check,
        }
