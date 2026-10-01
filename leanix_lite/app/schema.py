"""Data model: BDAT entity definitions, choice lists and allowed relationships.

Everything the UI and the Excel layer need to know about the data model lives here,
so adding a field or a whole fact sheet type is a change to this file only.
"""
from __future__ import annotations

from dataclasses import dataclass, field

SCHEMA_VERSION = 1

# BDAT layers, in display order.
LAYER_BUSINESS = "Business"
LAYER_DATA = "Data"
LAYER_APPLICATION = "Application"
LAYER_TECHNOLOGY = "Technology"
LAYERS = [LAYER_BUSINESS, LAYER_DATA, LAYER_APPLICATION, LAYER_TECHNOLOGY]

LIFECYCLE = ["Plan", "Phase In", "Active", "Phase Out", "End of Life"]
CRITICALITY = ["Low", "Medium", "High", "Mission Critical"]
DATA_CLASSIFICATION = ["Public", "Internal", "Confidential", "Restricted"]
YES_NO = ["Yes", "No"]
TECH_CATEGORY = [
    "Database", "Operating System", "Middleware", "Hardware", "Network",
    "Cloud Service", "Programming Language / Framework", "Other",
]

# Columns every entity sheet has, in addition to its own fields.
AUDIT_FIELDS = ["Created By", "Created At", "Modified By", "Modified At"]


@dataclass(frozen=True)
class Field:
    name: str
    kind: str = "text"            # text | long | choice | ref
    choices: tuple[str, ...] = ()
    required: bool = False
    ref: str | None = None        # entity key referenced when kind == "ref"
    in_grid: bool = True          # show as a column in the inventory grid


@dataclass(frozen=True)
class Entity:
    key: str                      # internal key, also used in the Relationships sheet
    sheet: str                    # Excel sheet name
    label: str                    # singular display name
    plural: str
    layer: str
    prefix: str                   # ID prefix, e.g. APP -> APP-0001
    fields: tuple[Field, ...] = field(default_factory=tuple)

    @property
    def id_field(self) -> str:
        return f"{self.label} ID"

    @property
    def columns(self) -> list[str]:
        """Excel columns in order: ID, own fields, audit fields."""
        return [self.id_field] + [f.name for f in self.fields] + AUDIT_FIELDS

    def field(self, name: str) -> Field:
        for f in self.fields:
            if f.name == name:
                return f
        raise KeyError(name)


ENTITIES: dict[str, Entity] = {
    "capability": Entity(
        "capability", "Business Capabilities", "Capability", "Business Capabilities",
        LAYER_BUSINESS, "BC",
        (
            Field("Name", required=True),
            Field("Parent Capability", kind="ref", ref="capability"),
            Field("Description", kind="long"),
            Field("Business Owner"),
        ),
    ),
    "process": Entity(
        "process", "Business Processes", "Process", "Business Processes",
        LAYER_BUSINESS, "BP",
        (
            Field("Name", required=True),
            Field("Description", kind="long"),
            Field("Process Owner"),
        ),
    ),
    "dataobject": Entity(
        "dataobject", "Data Objects", "Data Object", "Data Objects",
        LAYER_DATA, "DO",
        (
            Field("Name", required=True),
            Field("Description", kind="long"),
            Field("Data Classification", kind="choice", choices=tuple(DATA_CLASSIFICATION)),
            Field("Contains Personal Data", kind="choice", choices=tuple(YES_NO)),
            Field("Data Owner"),
        ),
    ),
    "application": Entity(
        "application", "Applications", "Application", "Applications",
        LAYER_APPLICATION, "APP",
        (
            Field("Name", required=True),
            Field("Description", kind="long"),
            Field("Lifecycle Status", kind="choice", choices=tuple(LIFECYCLE), required=True),
            Field("Business Criticality", kind="choice", choices=tuple(CRITICALITY)),
            Field("Business Owner"),
            Field("Technical Owner"),
        ),
    ),
    "itcomponent": Entity(
        "itcomponent", "IT Components", "IT Component", "IT Components",
        LAYER_TECHNOLOGY, "ITC",
        (
            Field("Name", required=True),
            Field("Provider"),
            Field("Technical Stack", kind="choice", choices=tuple(TECH_CATEGORY)),
            Field("Lifecycle Status", kind="choice", choices=tuple(LIFECYCLE)),
            Field("Description", kind="long"),
        ),
    ),
}

ENTITY_ORDER = ["capability", "process", "dataobject", "application", "itcomponent"]


@dataclass(frozen=True)
class RelationRule:
    """An allowed link type between two entity types (stored once, source -> target)."""
    source: str
    target: str
    label: str                    # relation type written to the sheet
    source_view: str              # wording seen from the source record
    target_view: str              # wording seen from the target record


RELATION_RULES: list[RelationRule] = [
    RelationRule("application", "capability", "supports", "Supports capabilities", "Supported by applications"),
    RelationRule("application", "process", "supports", "Supports processes", "Supported by applications"),
    RelationRule("process", "capability", "realizes", "Realizes capabilities", "Realized by processes"),
    RelationRule("application", "dataobject", "uses", "Uses data objects", "Used by applications"),
    RelationRule("application", "itcomponent", "runs on", "Runs on IT components", "Hosts applications"),
    RelationRule("dataobject", "itcomponent", "stored on", "Stored on IT components", "Stores data objects"),
    RelationRule("application", "application", "interfaces with", "Interfaces with applications", "Interfaced from applications"),
]

# "Source Name" / "Target Name" are informational (regenerated on every save, ignored on read).
REL_COLUMNS = ["Source Type", "Source ID", "Source Name", "Relation Type",
               "Target Type", "Target ID", "Target Name", "Created By", "Created At"]
REL_SHEET = "Relationships"
META_SHEET = "Meta"


def rules_for(entity_key: str) -> list[tuple[RelationRule, str]]:
    """Rules touching an entity, as (rule, direction) with direction 'out' or 'in'."""
    out = []
    for r in RELATION_RULES:
        if r.source == entity_key:
            out.append((r, "out"))
        if r.target == entity_key and r.source != r.target:
            out.append((r, "in"))
    return out
