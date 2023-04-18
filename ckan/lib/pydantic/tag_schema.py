import pydantic
from typing import Optional
from typing_extensions import Literal


class DefaultTagSchema(pydantic.BaseModel):
    name: str
    vocabulary_id: Optional[str]
    _revision_timestamp: Optional[str]
    _state: Optional[str]
    _display_name: Optional[str]


class DefaultCreateTagSchema(DefaultTagSchema):

    vocabulary_id: str
    id: Literal[None]
