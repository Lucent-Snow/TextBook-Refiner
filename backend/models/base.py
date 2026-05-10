"""Base model with camelCase JSON serialization for frontend compatibility."""

from pydantic import BaseModel as PydanticBaseModel
from pydantic.alias_generators import to_camel


class CamelModel(PydanticBaseModel):
    """Pydantic model that serializes to camelCase JSON.

    Python attributes use snake_case (e.g. `project_id`).
    JSON output uses camelCase (e.g. `projectId`).
    JSON input accepts both styles.
    """

    model_config = {
        "alias_generator": to_camel,
        "populate_by_name": True,
    }
