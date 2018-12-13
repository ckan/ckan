"""
Interfaces for FormEncode (for documentation purposes only)
"""


class Attribute(object):

    def __init__(self, description, name=None):
        self.description = description
        self.name = name


class Interface(object):
    pass


class IDeclarative(Interface):

    def __init__(**kw):
        """
        Instantiates this class with all the keywords being used to
        update the instance variables.
        """

    def __call__(**kw):
        """
        Returns a copy with all attributes using the given keywords,
        being updated.
        """


class IValidator(IDeclarative):

    messages = Attribute("""
    A dictionary of messages (with formatting strings) for error
    responses""", name='messages')
    if_missing = Attribute("""
    If the source that this validator would handle is missing (e.g.,
    a field that was not specified), use this value.  If
    Validator.NoDefault, then if the field is missing an exception
    should be raised.""", name='ifMissing')
    repeating = Attribute("""
    A boolean; this object accepts lists if true, subvalidators can be
    found in the validators attribute.""", name='repeating')
    compound = Attribute("""
    A boolean; this object has a dictionary of validators if this is
    true, subvalidators can be found in the field attribute (a
    dictionary).""", name='compound')

    def to_python(value, state=None):
        """
        Convert `value` from its foreign representation to its Python
        representation.  `state` is for application-specific hooks.
        """

    def from_python(value, state=None):
        """
        Convert `value` from its Python representation to the foreign
        representation.  `state` is for application-specific hooks.
        """

    def message(name, default):
        """
        Return the message (from the `messages` attribute) that goes
        with `name`, or return default if `name` not found `default`.
        """


class ISchema(IValidator):

    fields = Attribute('A dictionary of (field name: validator)',
        name='fields')
