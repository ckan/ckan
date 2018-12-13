# -*- coding: utf-8 -*-
# Copyright (c) 2010 Mark Sandstrom
# Copyright (c) 2011-2013 Raphaël Barrois
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


import itertools
import warnings
import logging

from . import compat
from . import utils


logger = logging.getLogger('factory.generate')


class OrderedDeclaration(object):
    """A factory declaration.

    Ordered declarations mark an attribute as needing lazy evaluation.
    This allows them to refer to attributes defined by other OrderedDeclarations
    in the same factory.
    """

    def evaluate(self, sequence, obj, create, extra=None, containers=()):
        """Evaluate this declaration.

        Args:
            sequence (int): the current sequence counter to use when filling
                the current instance
            obj (containers.LazyStub): The object holding currently computed
                attributes
            containers (list of containers.LazyStub): The chain of SubFactory
                which led to building this object.
            create (bool): whether the target class should be 'built' or
                'created'
            extra (DeclarationDict or None): extracted key/value extracted from
                the attribute prefix
        """
        raise NotImplementedError('This is an abstract method')


class LazyAttribute(OrderedDeclaration):
    """Specific OrderedDeclaration computed using a lambda.

    Attributes:
        function (function): a function, expecting the current LazyStub and
            returning the computed value.
    """

    def __init__(self, function, *args, **kwargs):
        super(LazyAttribute, self).__init__(*args, **kwargs)
        self.function = function

    def evaluate(self, sequence, obj, create, extra=None, containers=()):
        logger.debug("LazyAttribute: Evaluating %r on %r", self.function, obj)
        return self.function(obj)


class _UNSPECIFIED(object):
    pass


def deepgetattr(obj, name, default=_UNSPECIFIED):
    """Try to retrieve the given attribute of an object, digging on '.'.

    This is an extended getattr, digging deeper if '.' is found.

    Args:
        obj (object): the object of which an attribute should be read
        name (str): the name of an attribute to look up.
        default (object): the default value to use if the attribute wasn't found

    Returns:
        the attribute pointed to by 'name', splitting on '.'.

    Raises:
        AttributeError: if obj has no 'name' attribute.
    """
    try:
        if '.' in name:
            attr, subname = name.split('.', 1)
            return deepgetattr(getattr(obj, attr), subname, default)
        else:
            return getattr(obj, name)
    except AttributeError:
        if default is _UNSPECIFIED:
            raise
        else:
            return default


class SelfAttribute(OrderedDeclaration):
    """Specific OrderedDeclaration copying values from other fields.

    If the field name starts with two dots or more, the lookup will be anchored
    in the related 'parent'.

    Attributes:
        depth (int): the number of steps to go up in the containers chain
        attribute_name (str): the name of the attribute to copy.
        default (object): the default value to use if the attribute doesn't
            exist.
    """

    def __init__(self, attribute_name, default=_UNSPECIFIED, *args, **kwargs):
        super(SelfAttribute, self).__init__(*args, **kwargs)
        depth = len(attribute_name) -  len(attribute_name.lstrip('.'))
        attribute_name = attribute_name[depth:]

        self.depth = depth
        self.attribute_name = attribute_name
        self.default = default

    def evaluate(self, sequence, obj, create, extra=None, containers=()):
        if self.depth > 1:
            # Fetching from a parent
            target = containers[self.depth - 2]
        else:
            target = obj

        logger.debug("SelfAttribute: Picking attribute %r on %r", self.attribute_name, target)
        return deepgetattr(target, self.attribute_name, self.default)

    def __repr__(self):
        return '<%s(%r, default=%r)>' % (
            self.__class__.__name__,
            self.attribute_name,
            self.default,
        )


class Iterator(OrderedDeclaration):
    """Fill this value using the values returned by an iterator.

    Warning: the iterator should not end !

    Attributes:
        iterator (iterable): the iterator whose value should be used.
        getter (callable or None): a function to parse returned values
    """

    def __init__(self, iterator, cycle=True, getter=None):
        super(Iterator, self).__init__()
        self.getter = getter

        if cycle:
            iterator = itertools.cycle(iterator)
        self.iterator = utils.ResetableIterator(iterator)

    def evaluate(self, sequence, obj, create, extra=None, containers=()):
        logger.debug("Iterator: Fetching next value from %r", self.iterator)
        value = next(iter(self.iterator))
        if self.getter is None:
            return value
        return self.getter(value)

    def reset(self):
        """Reset the internal iterator."""
        self.iterator.reset()


class Sequence(OrderedDeclaration):
    """Specific OrderedDeclaration to use for 'sequenced' fields.

    These fields are typically used to generate increasing unique values.

    Attributes:
        function (function): A function, expecting the current sequence counter
            and returning the computed value.
        type (function): A function converting an integer into the expected kind
            of counter for the 'function' attribute.
    """
    def __init__(self, function, type=int):  # pylint: disable=W0622
        super(Sequence, self).__init__()
        self.function = function
        self.type = type

    def evaluate(self, sequence, obj, create, extra=None, containers=()):
        logger.debug("Sequence: Computing next value of %r for seq=%d", self.function, sequence)
        return self.function(self.type(sequence))


class LazyAttributeSequence(Sequence):
    """Composite of a LazyAttribute and a Sequence.

    Attributes:
        function (function): A function, expecting the current LazyStub and the
            current sequence counter.
        type (function): A function converting an integer into the expected kind
            of counter for the 'function' attribute.
    """
    def evaluate(self, sequence, obj, create, extra=None, containers=()):
        logger.debug("LazyAttributeSequence: Computing next value of %r for seq=%d, obj=%r",
                self.function, sequence, obj)
        return self.function(obj, self.type(sequence))


class ContainerAttribute(OrderedDeclaration):
    """Variant of LazyAttribute, also receives the containers of the object.

    Attributes:
        function (function): A function, expecting the current LazyStub and the
            (optional) object having a subfactory containing this attribute.
        strict (bool): Whether evaluating should fail when the containers are
            not passed in (i.e used outside a SubFactory).
    """
    def __init__(self, function, strict=True, *args, **kwargs):
        super(ContainerAttribute, self).__init__(*args, **kwargs)
        self.function = function
        self.strict = strict

    def evaluate(self, sequence, obj, create, extra=None, containers=()):
        """Evaluate the current ContainerAttribute.

        Args:
            obj (LazyStub): a lazy stub of the object being constructed, if
                needed.
            containers (list of LazyStub): a list of lazy stubs of factories
                being evaluated in a chain, each item being a future field of
                next one.
        """
        if self.strict and not containers:
            raise TypeError(
                "A ContainerAttribute in 'strict' mode can only be used "
                "within a SubFactory.")

        return self.function(obj, containers)


class ParameteredAttribute(OrderedDeclaration):
    """Base class for attributes expecting parameters.

    Attributes:
        defaults (dict): Default values for the paramters.
            May be overridden by call-time parameters.

    Class attributes:
        CONTAINERS_FIELD (str): name of the field, if any, where container
            information (e.g for SubFactory) should be stored. If empty,
            containers data isn't merged into generate() parameters.
    """

    CONTAINERS_FIELD = '__containers'

    # Whether to add the current object to the stack of containers
    EXTEND_CONTAINERS = False

    def __init__(self, **kwargs):
        super(ParameteredAttribute, self).__init__()
        self.defaults = kwargs

    def _prepare_containers(self, obj, containers=()):
        if self.EXTEND_CONTAINERS:
            return (obj,) + tuple(containers)

        return containers

    def evaluate(self, sequence, obj, create, extra=None, containers=()):
        """Evaluate the current definition and fill its attributes.

        Uses attributes definition in the following order:
        - values defined when defining the ParameteredAttribute
        - additional values defined when instantiating the containing factory

        Args:
            create (bool): whether the parent factory is being 'built' or
                'created'
            extra (containers.DeclarationDict): extra values that should
                override the defaults
            containers (list of LazyStub): List of LazyStub for the chain of
                factories being evaluated, the calling stub being first.
        """
        defaults = dict(self.defaults)
        if extra:
            defaults.update(extra)
        if self.CONTAINERS_FIELD:
            containers = self._prepare_containers(obj, containers)
            defaults[self.CONTAINERS_FIELD] = containers

        return self.generate(sequence, obj, create, defaults)

    def generate(self, sequence, obj, create, params):  # pragma: no cover
        """Actually generate the related attribute.

        Args:
            sequence (int): the current sequence number
            obj (LazyStub): the object being constructed
            create (bool): whether the calling factory was in 'create' or
                'build' mode
            params (dict): parameters inherited from init and evaluation-time
                overrides.

        Returns:
            Computed value for the current declaration.
        """
        raise NotImplementedError()


class _FactoryWrapper(object):
    """Handle a 'factory' arg.

    Such args can be either a Factory subclass, or a fully qualified import
    path for that subclass (e.g 'myapp.factories.MyFactory').
    """
    def __init__(self, factory_or_path):
        self.factory = None
        self.module = self.name = ''
        if isinstance(factory_or_path, type):
            self.factory = factory_or_path
        else:
            if not (compat.is_string(factory_or_path) and '.' in factory_or_path):
                raise ValueError(
                        "A factory= argument must receive either a class "
                        "or the fully qualified path to a Factory subclass; got "
                        "%r instead." % factory_or_path)
            self.module, self.name = factory_or_path.rsplit('.', 1)

    def get(self):
        if self.factory is None:
            self.factory = utils.import_object(
                self.module,
                self.name,
            )
        return self.factory

    def __repr__(self):
        if self.factory is None:
            return '<_FactoryImport: %s.%s>' % (self.module, self.name)
        else:
            return '<_FactoryImport: %s>' % self.factory.__class__


class SubFactory(ParameteredAttribute):
    """Base class for attributes based upon a sub-factory.

    Attributes:
        defaults (dict): Overrides to the defaults defined in the wrapped
            factory
        factory (base.Factory): the wrapped factory
    """

    EXTEND_CONTAINERS = True

    def __init__(self, factory, **kwargs):
        super(SubFactory, self).__init__(**kwargs)
        self.factory_wrapper = _FactoryWrapper(factory)

    def get_factory(self):
        """Retrieve the wrapped factory.Factory subclass."""
        return self.factory_wrapper.get()

    def generate(self, sequence, obj, create, params):
        """Evaluate the current definition and fill its attributes.

        Args:
            create (bool): whether the subfactory should call 'build' or
                'create'
            params (containers.DeclarationDict): extra values that should
                override the wrapped factory's defaults
        """
        subfactory = self.get_factory()
        logger.debug("SubFactory: Instantiating %s.%s(%s), create=%r",
            subfactory.__module__, subfactory.__name__,
            utils.log_pprint(kwargs=params),
            create,
        )
        return subfactory.simple_generate(create, **params)


class Dict(SubFactory):
    """Fill a dict with usual declarations."""

    def __init__(self, params, dict_factory='factory.DictFactory'):
        super(Dict, self).__init__(dict_factory, **dict(params))

    def generate(self, sequence, obj, create, params):
        dict_factory = self.get_factory()
        logger.debug("Dict: Building dict(%s)", utils.log_pprint(kwargs=params))
        return dict_factory.simple_generate(create,
            __sequence=sequence,
            **params)


class List(SubFactory):
    """Fill a list with standard declarations."""

    def __init__(self, params, list_factory='factory.ListFactory'):
        params = dict((str(i), v) for i, v in enumerate(params))
        super(List, self).__init__(list_factory, **params)

    def generate(self, sequence, obj, create, params):
        list_factory = self.get_factory()
        logger.debug('List: Building list(%s)',
            utils.log_pprint(args=[v for _i, v in sorted(params.items())]),
        )
        return list_factory.simple_generate(create,
            __sequence=sequence,
            **params)


class ExtractionContext(object):
    """Private class holding all required context from extraction to postgen."""
    def __init__(self, value=None, did_extract=False, extra=None, for_field=''):
        self.value = value
        self.did_extract = did_extract
        self.extra = extra or {}
        self.for_field = for_field

    def __repr__(self):
        return 'ExtractionContext(%r, %r, %r)' % (
            self.value,
            self.did_extract,
            self.extra,
        )


class PostGenerationDeclaration(object):
    """Declarations to be called once the target object has been generated."""

    def extract(self, name, attrs):
        """Extract relevant attributes from a dict.

        Args:
            name (str): the name at which this PostGenerationDeclaration was
                defined in the declarations
            attrs (dict): the attribute dict from which values should be
                extracted

        Returns:
            (object, dict): a tuple containing the attribute at 'name' (if
                provided) and a dict of extracted attributes
        """
        try:
            extracted = attrs.pop(name)
            did_extract = True
        except KeyError:
            extracted = None
            did_extract = False

        kwargs = utils.extract_dict(name, attrs)
        return ExtractionContext(extracted, did_extract, kwargs, name)

    def call(self, obj, create, extraction_context):  # pragma: no cover
        """Call this hook; no return value is expected.

        Args:
            obj (object): the newly generated object
            create (bool): whether the object was 'built' or 'created'
            extraction_context: An ExtractionContext containing values
                extracted from the containing factory's declaration
        """
        raise NotImplementedError()


class PostGeneration(PostGenerationDeclaration):
    """Calls a given function once the object has been generated."""
    def __init__(self, function):
        super(PostGeneration, self).__init__()
        self.function = function

    def call(self, obj, create, extraction_context):
        logger.debug('PostGeneration: Calling %s.%s(%s)',
            self.function.__module__,
            self.function.__name__,
            utils.log_pprint(
                (obj, create, extraction_context.value),
                extraction_context.extra,
            ),
        )
        return self.function(obj, create,
            extraction_context.value, **extraction_context.extra)


class RelatedFactory(PostGenerationDeclaration):
    """Calls a factory once the object has been generated.

    Attributes:
        factory (Factory): the factory to call
        defaults (dict): extra declarations for calling the related factory
        name (str): the name to use to refer to the generated object when
            calling the related factory
    """

    def __init__(self, factory, factory_related_name='', **defaults):
        super(RelatedFactory, self).__init__()
        if factory_related_name == '' and defaults.get('name') is not None:
            warnings.warn(
                "Usage of RelatedFactory(SomeFactory, name='foo') is deprecated"
                " and will be removed in the future. Please use the"
                " RelatedFactory(SomeFactory, 'foo') or"
                " RelatedFactory(SomeFactory, factory_related_name='foo')"
                " syntax instead", PendingDeprecationWarning, 2)
            factory_related_name = defaults.pop('name')

        self.name = factory_related_name
        self.defaults = defaults
        self.factory_wrapper = _FactoryWrapper(factory)

    def get_factory(self):
        """Retrieve the wrapped factory.Factory subclass."""
        return self.factory_wrapper.get()

    def call(self, obj, create, extraction_context):
        factory = self.get_factory()

        if extraction_context.did_extract:
            # The user passed in a custom value
            logger.debug('RelatedFactory: Using provided %r instead of '
                    'generating %s.%s.',
                    extraction_context.value,
                    factory.__module__, factory.__name__,
            )
            return extraction_context.value

        passed_kwargs = dict(self.defaults)
        passed_kwargs.update(extraction_context.extra)
        if self.name:
            passed_kwargs[self.name] = obj

        logger.debug('RelatedFactory: Generating %s.%s(%s)',
            factory.__module__,
            factory.__name__,
            utils.log_pprint((create,), passed_kwargs),
        )
        return factory.simple_generate(create, **passed_kwargs)


class PostGenerationMethodCall(PostGenerationDeclaration):
    """Calls a method of the generated object.

    Attributes:
        method_name (str): the method to call
        method_args (list): arguments to pass to the method
        method_kwargs (dict): keyword arguments to pass to the method

    Example:
        class UserFactory(factory.Factory):
            ...
            password = factory.PostGenerationMethodCall('set_pass', password='')
    """
    def __init__(self, method_name, *args, **kwargs):
        super(PostGenerationMethodCall, self).__init__()
        self.method_name = method_name
        self.method_args = args
        self.method_kwargs = kwargs

    def call(self, obj, create, extraction_context):
        if not extraction_context.did_extract:
            passed_args = self.method_args

        elif len(self.method_args) <= 1:
            # Max one argument expected
            passed_args = (extraction_context.value,)
        else:
            passed_args = tuple(extraction_context.value)

        passed_kwargs = dict(self.method_kwargs)
        passed_kwargs.update(extraction_context.extra)
        method = getattr(obj, self.method_name)
        logger.debug('PostGenerationMethodCall: Calling %r.%s(%s)',
            obj,
            self.method_name,
            utils.log_pprint(passed_args, passed_kwargs),
        )
        return method(*passed_args, **passed_kwargs)
