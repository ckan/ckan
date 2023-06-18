# -*- coding: utf-8 -*-
"""This module defines Option class and its helpers.

"""
from __future__ import annotations

import enum
from typing import Any, Generic, Optional, TypeVar, cast

from typing_extensions import Self

from ckan.types import Validator, ValidatorFactory

T = TypeVar("T")
_sentinel = object()


class SectionMixin:
    """Mixin that allows adding objects to different sections of INI-file.
    """
    _section = "app:main"

    def set_section(self, section: str) -> Self:
        """Change the section of this annotation
        """
        self._section = section
        return self


class Flag(enum.Flag):
    """Modifiers for :py:class:`~ckan.config.declaration.option.Option`


    ignored: this option is ignored by CKAN(not used or unconditionally
    overriden)

    experimental: this option is not stabilized and can change in
    future. Mainly exist for extension developers, as only stable features are
    included into public CKAN release.

    internal: this option is used internally by CKAN or Flask. Such options are
    not documented and are not supposed to be modified by users. Think about
    them as private class attributes.

    required: this option cannot be missing/empty. Add such flag to the option
    only if CKAN application won't even start without them and there is no
    sensible default. If option does not have ``not_empty`` validator, it will
    be added before all other validators.

    editable: this option is runtime editable. Technically, every option can be
    modified. This flag means that there is an expectation that option will be
    modified. For example, this option is exposed via configuration form in the
    Admin UI.

    commented: this option is commented by default in the config file.  Use it
    for optional settings that may break the application when default value is
    used. Example of such option is a cookie domain. When it's missing, the
    current domain is used, so this value is optional. But if you try to
    provide default value, `example.com` or any other domain, CKAN
    authentication will not work as long as application runs on different
    domain. While it's similar to `placeholder` attribute of the
    :py:class:`~ckan.config.declaration.option.Option`, their goals are
    different.
    Option.placeholer:
    - shows an example of expectend value
    - is ignored when config option is **missing** from the config file
    - shown as a default value in the config file generated from template. For
      example, `Option<key=a, placeholder=b, commented=False>` is added to the
      config file as `a = b`. After this, `config.get('a')` returns `b`,
      because it's explicitely written in the config file.
    Flag.commented:
    - Marks option as commented by default
    - Does not changes behavior of `Option.default` and `Option.placeholder`.
    - switches option to the commented state in the config file generated from
      template.  For example, `Option<key=a, placeholder=b, commented=True>` is
      added to the config file as `# a = b`. After this,
      `config.get('a')` returns `None`, because there is no option `a` in
      the config file(it's commented, which makes this option non-existing)
    If the option is missing from the config file, both `placeholder` and
    `commented` are virtually ignored, having absolutely no impact on the value
    of the config option.

    reserved_*(01-10): these flags are added for extension developers. CKAN
    doesn't treat them specially, neither includes them in groups, like
    `not_safe`/`not_iterable`. These flags are completely ignored by CKAN. If
    your extension enchances the behavior of config options using some sort of
    boolean flags - use reserved markers. Always rely on a config option that
    controls, which reserved marker to use, in order to avoid conflicts with
    other extensions. Example:

        >>> # BAD
        >>> marker = Flag.reserved_02
        >>>
        >>> # GOOD
        >>> ### config file
        >>> # my_extension.feature_flag = reserved_02
        >>> key = config.get('my_extension.feature_flag')
        >>> marker = Flag[key]

    This allows the end user to manually solve conflicts, when multiple
    extensions are trying to use the same reserved flag.

    """
    ignored = enum.auto()
    experimental = enum.auto()
    internal = enum.auto()
    required = enum.auto()
    editable = enum.auto()
    commented = enum.auto()

    reserved_01 = enum.auto()
    reserved_02 = enum.auto()
    reserved_03 = enum.auto()
    reserved_04 = enum.auto()
    reserved_05 = enum.auto()
    reserved_06 = enum.auto()
    reserved_07 = enum.auto()
    reserved_08 = enum.auto()
    reserved_09 = enum.auto()
    reserved_10 = enum.auto()

    @classmethod
    def none(cls):
        """Return the base flag with no modifiers enabled.
        """
        return cls(0)

    @classmethod
    def non_iterable(cls):
        """Return the union of flags that should not be iterated over.

        If an option has any of these flags, it isn't listed by the majority of
        serializers. For example, such option is not added to the documentation
        and to the config template.

        """
        return cls.ignored | cls.experimental | cls.internal

    @classmethod
    def not_safe(cls):
        """Return the union of flags marking an unsafe option.

        It's never safe to use an unsafe option. For example, unsafe option
        won't have any default value, so one should never try
        `config[unsafe_option]`. Basically, unsafe options must be treated as
        non-existing and never be used in code.

        """
        return cls.ignored | cls.internal


class Annotation(SectionMixin, str):
    """Details that are not attached to any option.

    Mainly serves documentation purposes. Can be used for creating section
    separators or blocks of text with the recomendations, that are not
    connected to any particular option and rather describle the whole section.

    """
    pass


class Option(SectionMixin, Generic[T]):
    """All the known details about config option.

    Option-objects are created from the config declaration and describe the
    individual config options. They contain all the known details about config
    option, such as default values, validators and visibility flags.

    Avoid direct creation of Option-objects. Use corresponding
    :py:class:`~ckan.config.declaration.Declaration` methods instead:

    - declare
    - declare_bool
    - declare_int
    - declare_list
    - declare_dynamic
    """
    __slots__ = (
        "flags",
        "default",
        "description",
        "validators",
        "placeholder",
        "example",
        "legacy_key",
    )

    flags: Flag
    default: Optional[T]
    description: Optional[str]
    placeholder: Optional[str]
    example: Optional[Any]
    validators: str
    legacy_key: Optional[str]

    def __init__(self, default: Optional[T] = None):
        self.flags = Flag.none()
        self.description = None
        self.placeholder = None
        self.example = None
        self.validators = ""
        self.default = default
        self.legacy_key = None

    def str_value(self, value: T | object = _sentinel) -> str:
        """Convert value into the string using option's settings.

        If `value` argument is not present, convert the default value of the
        option into a string.

        If the option has `as_list` validator and the value is represented by
        the Python's `list` object, result is a space-separated list of all the
        members of the value. In other cases this method just does naive string
        conversion.

        If validators are doing complex transformations, for example string ID
        turns into :py:class:`~ckan.model.User` object, this method won't
        convert the user object back into ID. Instead it will just do something
        like `str(user)` and give you `<User ...>`. So it's up to the person
        who declares config option to add a combination of default value and
        validators that won't throw an error after such conversion.

        If more sophisticated logic cannot be avoided, consider creating a
        subclass of :py:class:`~ckan.config.declaration.option.Option` with
        custom `str_value` implemetation and declaring the option using
        `declare_option` method of
        :py:class:`~ckan.config.declaration.Declaration`.

        """
        as_list = "as_list" in self.get_validators()
        v = self.default if value is _sentinel else value

        if isinstance(v, list) and as_list:
            return " ".join(map(str, v))

        if self.has_default() or value is not _sentinel:
            return str(v)

        return ""

    def set_flag(self, flag: Flag) -> Self:
        """Enable specified flag.
        """
        self.flags |= flag
        return self

    def has_flag(self, flag: Flag) -> bool:
        """Check if option has specified flag enabled.
        """
        return bool(self.flags & flag)

    def has_default(self) -> bool:
        """Check if option has configured default.
        """
        return self.default is not None

    def set_default(self, default: T) -> Self:
        """Change the default value of option.

        The default value is used whenever the option is missing from the
        config file.

        """
        self.default = default
        return self

    def set_example(self, example: str) -> Self:
        """Provide an example(documentation) of the valid value for option.
        """
        self.example = example
        return self

    def set_description(self, description: str) -> Self:
        """Change the description of option.
        """
        self.description = description
        return self

    def set_placeholder(self, placeholder: str) -> Self:
        """Add a placeholder for option.

        Placeholder is used during generation of the config template. It's
        similar to the default value, because it will be shown in the generated
        configuration file as a value for option. But, unlike the default
        value, if the option is missing from the config file, no default value
        is used.

        Placeholder can be used for different kind of secrets and URLs, when
        you want to show the user how the value should look like.

        """
        self.placeholder = placeholder
        return self

    def set_validators(self, validators: str) -> Self:
        """Replace validators of the option.

        Use a space-separated string with the names of validators that must be
        applied to the value.

        """
        self.validators = validators
        return self

    def append_validators(self, validators: str, before: bool = False) -> Self:
        """Add extra validators before or after the existing validators.

        Use it together with `Declaration.declare_*` shortcuts in order to
        define more specific common options::

            >>> # Declare a mandatory boolean option
            >>> declaration.declare_bool(...).append_validators(
                    "not_missing", before=True)

        By default, validators are added after the existing validators. In
        order to add a new validator before the other validators, pass
        `before=True` argument.

        """
        left = self.validators
        right = validators
        if before:
            left, right = right, left

        glue = " " if left and right else ""
        self.validators = left + glue + right
        return self

    def get_validators(self) -> str:
        """Return the string with current validators.
        """
        validators = self.validators
        if self.has_flag(Flag.required) and "not_empty" not in validators:
            validators = f"not_empty {validators}"

        return validators

    def experimental(self) -> Self:
        """Enable experimental-flag for value.
        """
        self.set_flag(Flag.experimental)
        return self

    def required(self) -> Self:
        """Enable required-flag for value.
        """
        self.set_flag(Flag.required)
        return self

    def normalize(self, value: Any) -> Any:
        """Return the value processed by option's validators.
        """
        from ckan.lib.navl.dictization_functions import validate

        data, _ = validate(
            {"value": value}, {"value": self._parse_validators()}
        )

        return data.get("value")

    def _parse_validators(self) -> list[Validator]:
        """Turn the string with validators into the list of functions.
        """
        return _validators_from_string(self.get_validators())


# taken from ckanext-scheming
# (https://github.com/ckan/ckanext-scheming/blob/master/ckanext/scheming/validation.py#L332).
# This syntax is familiar for everyone and we can switch to the original
# when scheming become a part of core.
def _validators_from_string(s: str) -> list[Validator]:
    """
    convert a schema validators string to a list of validators

    e.g. "if_empty_same_as(name) unicode_safe" becomes:
    [if_empty_same_as("name"), unicode_safe]
    """
    import ast
    from ckan.logic import get_validator

    out = []
    parts = s.split()
    for p in parts:
        if '(' in p and p[-1] == ')':
            name, args = p.split('(', 1)
            args = args[:-1]  # trim trailing ')'
            try:
                parsed_args = ast.literal_eval(args)
                if not isinstance(parsed_args, tuple) or not parsed_args:
                    # it's a signle argument. `not parsed_args` means that this
                    # single argument is an empty tuple,
                    # for example: "default(())"

                    parsed_args = (parsed_args,)

            except (ValueError, TypeError, SyntaxError, MemoryError):
                parsed_args = args.split(',')

            factory = cast(ValidatorFactory, get_validator(name))
            v = factory(*parsed_args)
        else:
            v = get_validator(p)
        out.append(v)
    return out
