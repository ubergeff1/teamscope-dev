"""
Pydantic schemas for Template CRUD operations (Project, Deliverable, Workshop).

These schemas validate request/response data for the /templates API endpoints.
They correspond to the following SQLAlchemy models defined in
``models_template.py``:
    - ``ProjectTemplate``      (table: ``project_templates``)
    - ``DeliverableTemplate``  (table: ``deliverable_templates``)
    - ``WorkshopTemplate``     (table: ``workshop_templates``)

Templates are reusable blueprints for creating standardized project
configurations.  When a new project is instantiated from a template, all
child deliverable and workshop templates are cloned into the project with
their default settings, saving setup time and ensuring consistency.

Schema pattern per entity:
    - *Out     -- Response body  (mirrors DB columns)
    - *Create  -- POST endpoint  (required fields + defaults)
    - *Update  -- PATCH endpoint (all fields optional for partial updates)

ProjectTemplateOut nests DeliverableTemplateOut and WorkshopTemplateOut to
provide a complete template definition in a single response.
"""
from pydantic import BaseModel, Field

# Regex pattern for deliverable type validation, shared across schemas.
_DELIVERABLE_TYPES = r"^(control_family|appendix|workshop|flat_hours|custom)$"


class DeliverableTemplateOut(BaseModel):
    """Response schema for a single deliverable template.

    Contains the default configuration values that will be applied when a
    deliverable is created from this template.  Nested inside
    ``ProjectTemplateOut``.

    Corresponds to the ``DeliverableTemplate`` SQLAlchemy model
    (table: ``deliverable_templates``).
    """
    # Auto-generated primary key.
    id: int
    # Default display name for the deliverable (e.g., "AC - Access Control").
    name: str
    # Deliverable type: control_family | appendix | workshop | flat_hours | custom.
    deliverable_type: str
    # Control family code (e.g., "AC", "AU") for resolving the control family
    # at project instantiation time. Only applicable for control_family type.
    control_family_code: str | None
    # Default hours per control for control_family type deliverables.
    default_hours_per_control: float | None
    # Default flat consultant hours for flat_hours/appendix/custom types.
    default_flat_hours: float | None     # consultant hours
    # Default QA/review hours allocated for this deliverable.
    default_qa_hours: float | None
    # Default number of business days for the drafting phase.
    default_business_days: int | None
    # FK to an associated workshop template for phase dependency.
    workshop_template_id: int | None
    # Display ordering within the parent project template.
    sort_order: int

    # Enable construction from SQLAlchemy ORM instances.
    model_config = {"from_attributes": True}


class DeliverableTemplateCreate(BaseModel):
    """Schema for creating a new deliverable template
    (POST /templates/{id}/deliverables).

    Only ``name`` is required; other fields have sensible defaults.
    The ``deliverable_type`` defaults to "custom".

    Corresponds to the ``DeliverableTemplate`` SQLAlchemy model
    (table: ``deliverable_templates``).
    """
    # Display name for the deliverable template; required, max 200 characters.
    name: str = Field(..., max_length=200)
    # Deliverable type determining hour-calculation formula. Defaults to "custom".
    # Valid values: control_family | appendix | workshop | flat_hours | custom
    deliverable_type: str = Field("custom", pattern=_DELIVERABLE_TYPES)
    # Control family code (e.g., "AC"); max 10 chars. Used to resolve the
    # matching ControlFamily at project instantiation time.
    control_family_code: str | None = Field(None, max_length=10)
    # Default hours per control for control_family type deliverables.
    default_hours_per_control: float | None = None
    # Default flat consultant hours for flat_hours/appendix/custom types.
    default_flat_hours: float | None = None      # consultant hours
    # Default QA/review hours.
    default_qa_hours: float | None = None
    # Default business days for the drafting phase.
    default_business_days: int | None = None
    # FK to an associated workshop template. Optional.
    workshop_template_id: int | None = None
    # Display ordering. Defaults to 0 (first position).
    sort_order: int = 0


class DeliverableTemplateUpdate(BaseModel):
    """Schema for partially updating a deliverable template
    (PATCH /templates/{id}/deliverables/{deliverable_template_id}).

    All fields are optional; only non-None values are applied.

    Corresponds to the ``DeliverableTemplate`` SQLAlchemy model
    (table: ``deliverable_templates``).
    """
    # Updated template name; max 200 characters. None = keep current value.
    name: str | None = Field(None, max_length=200)
    # Updated deliverable type. None = keep current value.
    deliverable_type: str | None = Field(None, pattern=_DELIVERABLE_TYPES)
    # Updated control family code; max 10 chars. None = keep current value.
    control_family_code: str | None = Field(None, max_length=10)
    # Updated default hours per control. None = keep current value.
    default_hours_per_control: float | None = None
    # Updated default flat hours. None = keep current value.
    default_flat_hours: float | None = None      # consultant hours
    # Updated default QA hours. None = keep current value.
    default_qa_hours: float | None = None
    # Updated default business days. None = keep current value.
    default_business_days: int | None = None
    # Updated workshop template FK. None = keep current value.
    workshop_template_id: int | None = None
    # Updated display ordering. None = keep current value.
    sort_order: int | None = None


class WorkshopTemplateOut(BaseModel):
    """Response schema for a single workshop template.

    Contains the default name and duration that will be applied when a
    workshop is created from this template.  Nested inside
    ``ProjectTemplateOut``.

    Corresponds to the ``WorkshopTemplate`` SQLAlchemy model
    (table: ``workshop_templates``).
    """
    # Auto-generated primary key.
    id: int
    # Default display name for the workshop (e.g., "Kickoff Meeting").
    name: str
    # Default duration of the workshop in hours.
    duration_hours: float | None
    # Display ordering within the parent project template.
    sort_order: int

    # Enable construction from SQLAlchemy ORM instances.
    model_config = {"from_attributes": True}


class WorkshopTemplateCreate(BaseModel):
    """Schema for creating a new workshop template
    (POST /templates/{id}/workshops).

    Only ``name`` is required.

    Corresponds to the ``WorkshopTemplate`` SQLAlchemy model
    (table: ``workshop_templates``).
    """
    # Display name for the workshop template; required, max 200 characters.
    name: str = Field(..., max_length=200)
    # Default duration of the session in hours.
    duration_hours: float | None = None
    # Display ordering. Defaults to 0 (first position).
    sort_order: int = 0


class WorkshopTemplateUpdate(BaseModel):
    """Schema for partially updating a workshop template
    (PATCH /templates/{id}/workshops/{workshop_template_id}).

    All fields are optional; only non-None values are applied.

    Corresponds to the ``WorkshopTemplate`` SQLAlchemy model
    (table: ``workshop_templates``).
    """
    # Updated template name; max 200 characters. None = keep current value.
    name: str | None = Field(None, max_length=200)
    # Updated default duration in hours. None = keep current value.
    duration_hours: float | None = None
    # Updated display ordering. None = keep current value.
    sort_order: int | None = None


class ProjectTemplateCreate(BaseModel):
    """Schema for creating a new project template (POST /templates).

    Only ``name`` is required.  Framework and impact level can be assigned
    to scope the template to a specific compliance standard.

    Corresponds to the ``ProjectTemplate`` SQLAlchemy model
    (table: ``project_templates``).
    """
    # Display name for the template (e.g., "FedRAMP Moderate Standard"); max 100 chars.
    name: str = Field(..., max_length=100)
    # FK to the compliance framework this template is designed for. Optional.
    framework_id: int | None = None
    # FK to the impact level within the framework. Optional.
    impact_level_id: int | None = None
    # Description of when to use this template and what it includes.
    description: str | None = None


class ProjectTemplateUpdate(BaseModel):
    """Schema for partially updating a project template
    (PATCH /templates/{id}).

    All fields are optional; only non-None values are applied.
    Child deliverable/workshop templates are managed via their own endpoints.

    Corresponds to the ``ProjectTemplate`` SQLAlchemy model
    (table: ``project_templates``).
    """
    # Updated template name; max 100 characters. None = keep current value.
    name: str | None = Field(None, max_length=100)
    # Updated framework FK. None = keep current value.
    framework_id: int | None = None
    # Updated impact level FK. None = keep current value.
    impact_level_id: int | None = None
    # Updated description. None = keep current value.
    description: str | None = None


class ProjectTemplateOut(BaseModel):
    """Response schema for project template endpoints.

    Mirrors the ``project_templates`` table columns plus nested lists of
    ``DeliverableTemplateOut`` and ``WorkshopTemplateOut`` objects, providing
    a complete template definition in a single response.

    Excludes internal timestamps (created_at) and relationship objects
    (framework, impact_level) -- use their IDs to look up details from
    the /reference endpoints.

    ``from_attributes = True`` enables direct construction from a SQLAlchemy
    ``ProjectTemplate`` ORM instance.
    """
    # Auto-generated primary key.
    id: int
    # Template display name.
    name: str
    # FK to the compliance framework, if scoped.
    framework_id: int | None
    # FK to the impact level, if scoped.
    impact_level_id: int | None
    # Description of the template, if set.
    description: str | None
    # Deliverable blueprints belonging to this template.
    deliverable_templates: list[DeliverableTemplateOut] = []
    # Workshop blueprints belonging to this template.
    workshop_templates: list[WorkshopTemplateOut] = []

    # Enable construction from SQLAlchemy ORM instances.
    model_config = {"from_attributes": True}
