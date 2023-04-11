# -*- coding: utf-8 -*-
from __future__ import annotations

from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    Mapping,
    Optional,
    Union,
)

from typing_extensions import Protocol, TypeAlias, TypedDict
from blinker import Signal
from flask.wrappers import Response, Request

from .logic import ActionResult
from .model import (
    Model, AlchemySession,
    Query,
)

if TYPE_CHECKING:
    from ckanext.activity.model import Activity


__all__ = [
    "Response", "Request",
    "ActionResult",
    "Model", "AlchemySession", "Query",
    "Config", "CKANApp",
    "DataDict", "ErrorDict",
    "FlattenKey", "FlattenErrorDict", "FlattenDataDict",
    "SignalMapping", "Context",
    "ValueValidator", "ContextValidator", "DataValidator",
    "Validator", "ValidatorFactory",
    "Schema", "PlainSchemaFunc", "ComplexSchemaFunc",
    "AuthResult",
    "Action", "ChainedAction", "AuthFunction", "ChainedAuthFunction",
    "PFeed", "PFeedFactory", "PResourceUploader", "PUploader",
]
Config: TypeAlias = Dict[str, Union[str, Mapping[str, str]]]
CKANApp = Any

# dictionary passed to actions
DataDict: TypeAlias = "dict[str, Any]"
# dictionary passed to the ValidationError
ErrorDict: TypeAlias = (
    "dict[str, Union[int, str, list[Union[str, dict[str, Any]]]]]"
)

FlattenKey: TypeAlias = "tuple[Any, ...]"
FlattenDataDict: TypeAlias = "dict[FlattenKey, Any]"
FlattenErrorDict: TypeAlias = "dict[FlattenKey, list[str]]"

SignalMapping: TypeAlias = Dict[Signal, Iterable[Union[Any, Dict[str, Any]]]]


class Context(TypedDict, total=False):
    """Mutable private dictionary passed along through many layers of code.

    Used for all sorts of questionable parameter passing and global state
    sharing.  We're trying to *not* add to this dictionary and use normal
    parameters instead.  Bonus points for anything that can be removed from
    here.
    """
    user: str
    model: Model
    session: AlchemySession

    __auth_user_obj_checked: bool
    __auth_audit: list[tuple[str, int]]
    auth_user_obj: Optional["Model.User"]
    user_obj: "Model.User"

    schema_keys: list[Any]
    revision_id: Optional[Any]
    revision_date: Optional[Any]

    connection: Any
    check_access: Callable[..., Any]

    id: str
    user_id: str
    user_is_admin: bool
    search_query: bool
    return_query: bool
    return_id_only: bool
    defer_commit: bool
    reset_password: bool
    save: bool
    active: bool
    allow_partial_update: bool
    for_update: bool
    for_edit: bool
    for_view: bool
    ignore_auth: bool
    preview: bool
    allow_state_change: bool
    is_member: bool
    use_cache: bool
    include_plugin_extras: bool
    message: str

    keep_email: bool
    keep_apikey: bool
    skip_validation: bool
    validate: bool
    count_private_and_draft_datasets: bool

    schema: "Schema"
    group: "Model.Group"
    package: "Model.Package"
    vocabulary: "Model.Vocabulary"
    tag: "Model.Tag"
    activity: "Activity"
    task_status: "Model.TaskStatus"
    resource: "Model.Resource"
    resource_view: "Model.ResourceView"
    relationship: "Model.PackageRelationship"
    api_version: int
    dataset_counts: dict[str, Any]
    limits: dict[str, Any]
    metadata_modified: str
    with_capacity: bool

    table_names: list[str]


class AuthResult(TypedDict, total=False):
    """Result of any access check
    """
    success: bool
    msg: Optional[str]


# Simplest validator that accepts only validated value.
ValueValidator = Callable[[Any], Any]
# Validator that accepts validation context alongside with the value.
ContextValidator = Callable[[Any, Context], Any]
# Complex validator that has access the whole validated dictionary.
DataValidator = Callable[
    [FlattenKey, FlattenDataDict, FlattenErrorDict, Context], None]

Validator = Union[ValueValidator, ContextValidator, DataValidator]
ValidatorFactory = Callable[..., Validator]

Schema: TypeAlias = "dict[str, Union[list[Validator], Schema]]"

# Function that accepts arbitary number of validators(decorated by
# ckan.logic.schema.validator_args) and returns Schema dictionary
ComplexSchemaFunc = Callable[..., Schema]
# ComplexSchemaFunc+validator_args decorator = function that accepts no args
# and returns Schema dictionary
PlainSchemaFunc = Callable[[], Schema]

AuthFunctionWithOptionalDataDict = Callable[
    [Context, Optional[DataDict]], AuthResult
]
AuthFunctionWithMandatoryDataDict = Callable[[Context, DataDict], AuthResult]
AuthFunction = Union[
    AuthFunctionWithOptionalDataDict,
    AuthFunctionWithMandatoryDataDict,
    'partial[AuthResult]',
]
ChainedAuthFunction = Callable[
    [AuthFunction, Context, Optional[DataDict]], AuthResult
]

Action = Callable[[Context, DataDict], Any]
ChainedAction = Callable[[Action, Context, DataDict], Any]


class PFeed(Protocol):
    def add_item(self: Any, **kwargs: Any) -> None:
        ...

    def writeString(self: Any, encoding: str) -> str:
        ...


class PFeedFactory(Protocol):
    """Contract for IFeed.get_feed_class
    """

    def __call__(
        self,
        feed_title: str,
        feed_link: str,
        feed_description: str,
        language: Optional[str],
        author_name: Optional[str],
        feed_guid: Optional[str],
        feed_url: Optional[str],
        previous_page: Optional[str],
        next_page: Optional[str],
        first_page: Optional[str],
        last_page: Optional[str],
    ) -> PFeed:
        ...


class PUploader(Protocol):
    """Contract for IUploader.get_uploader
    """

    def __init__(
        self, object_type: str, old_filename: Optional[str] = None
    ) -> None:
        ...

    def upload(self, max_size: int = ...) -> None:
        ...

    def update_data_dict(
        self,
        data_dict: dict[str, Any],
        url_field: str,
        file_field: str,
        clear_field: str,
    ) -> None:
        ...


class PResourceUploader(Protocol):
    """Contract for IUploader.get_uploader
    """

    mimetype: Optional[str]
    filesize: int

    def __init__(self, resource: dict[str, Any]) -> None:
        ...

    def get_path(self, id: str) -> str:
        ...

    def upload(self, id: str, max_size: int = ...) -> None:
        ...
