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
    Generic,
)

from typing_extensions import Protocol, TypeAlias, TypedDict, TypeVar
from blinker import Signal
from flask.ctx import RequestContext
from flask.wrappers import Response, Request
from sqlalchemy.orm.scoping import ScopedSession
from sqlalchemy.orm.query import Query


from .logic import ActionResult

if TYPE_CHECKING:
    from ckan.config.middleware.flask_app import CKANFlask
    import ckan.model as model
    from ckan.tests.helpers import CKANTestApp
    from ckanext.activity.model import Activity


__all__ = [
    "Response", "Request",
    "ActionResult",
    "AlchemySession", "Query",
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

AlchemySession = ScopedSession[Any]

Config: TypeAlias = Dict[str, Union[str, Mapping[str, str]]]
CKANApp: TypeAlias = "CKANFlask"

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
    session: AlchemySession

    __auth_user_obj_checked: bool
    __auth_audit: list[tuple[str, int]]
    auth_user_obj: model.User | model.AnonymousUser | None
    user_obj: model.User

    schema_keys: list[Any]
    revision_id: Optional[Any]
    revision_date: Optional[Any]

    connection: Any
    check_access: Callable[..., Any]

    id: str | None
    user_id: str
    user_is_admin: bool
    search_query: bool
    return_query: bool
    return_id_only: bool
    defer_commit: bool
    reset_password: bool
    save: bool
    active: bool
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
    extras_as_string: bool
    with_private: bool
    group_type: str
    parent: Optional[str]

    keep_email: bool
    keep_apikey: bool
    skip_validation: bool
    validate: bool
    count_private_and_draft_datasets: bool

    schema: "Schema"
    group: model.Group
    package: model.Package
    vocabulary: model.Vocabulary
    tag: model.Tag
    activity: "Activity"
    task_status: model.TaskStatus
    resource: model.Resource
    resource_view: model.ResourceView
    relationship: model.PackageRelationship
    api_version: int
    dataset_counts: dict[str, Any]
    limits: dict[str, Any]
    metadata_modified: str
    with_capacity: bool

    table_names: list[str]
    plugin_data: dict[Any, Any]
    original_package: dict[str, Any]
    changed_entities: dict[str, set[str]]


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

# Function that accepts arbitrary number of validators(decorated by
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


TFactoryResult = TypeVar("TFactoryResult", default="dict[str, Any]")
TFactoryModel = TypeVar("TFactoryModel", default=Any, covariant=True)


class TestFactory(Protocol, Generic[TFactoryModel, TFactoryResult]):
    def __call__(self, **kwargs: Any) -> TFactoryResult:
        ...

    def api_create(self, data_dict: dict[str, Any]) -> TFactoryResult:
        ...

    def model(self, **kwargs: Any) -> TFactoryModel:
        ...

    def create_batch(self, size: int, **kwargs: Any) -> list[TFactoryResult]:
        ...

    def stub(self, **kwargs: Any) -> object:
        ...


FixtureProvidePlugin = Callable[[str, Callable[..., Any]], None]
FixtureCkanConfig = dict[str, Any]
FixtureMakeApp = Callable[[], "CKANTestApp"]
FixtureApp: TypeAlias = "CKANTestApp"
FixtureResetRedis = Callable[[], None]
FixtureResetDb = Callable[[], None]
FixtureResetQueues = Callable[[], None]
FixtureResetIndex = Callable[[], None]
FixtureTestRequestContext = Callable[..., RequestContext]
