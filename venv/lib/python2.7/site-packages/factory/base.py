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

import logging

from . import containers
from . import utils

logger = logging.getLogger('factory.generate')

# Strategies
BUILD_STRATEGY = 'build'
CREATE_STRATEGY = 'create'
STUB_STRATEGY = 'stub'


# Special declarations
FACTORY_CLASS_DECLARATION = 'FACTORY_FOR'

# Factory class attributes
CLASS_ATTRIBUTE_DECLARATIONS = '_declarations'
CLASS_ATTRIBUTE_POSTGEN_DECLARATIONS = '_postgen_declarations'
CLASS_ATTRIBUTE_ASSOCIATED_CLASS = '_associated_class'


class FactoryError(Exception):
    """Any exception raised by factory_boy."""


class AssociatedClassError(FactoryError):
    """Exception for Factory subclasses lacking FACTORY_FOR."""


class UnknownStrategy(FactoryError):
    """Raised when a factory uses an unknown strategy."""


class UnsupportedStrategy(FactoryError):
    """Raised when trying to use a strategy on an incompatible Factory."""


# Factory metaclasses

def get_factory_bases(bases):
    """Retrieve all FactoryMetaClass-derived bases from a list."""
    return [b for b in bases if issubclass(b, BaseFactory)]


class FactoryMetaClass(type):
    """Factory metaclass for handling ordered declarations."""

    def __call__(cls, **kwargs):
        """Override the default Factory() syntax to call the default strategy.

        Returns an instance of the associated class.
        """

        if cls.FACTORY_STRATEGY == BUILD_STRATEGY:
            return cls.build(**kwargs)
        elif cls.FACTORY_STRATEGY == CREATE_STRATEGY:
            return cls.create(**kwargs)
        elif cls.FACTORY_STRATEGY == STUB_STRATEGY:
            return cls.stub(**kwargs)
        else:
            raise UnknownStrategy('Unknown FACTORY_STRATEGY: {0}'.format(
                cls.FACTORY_STRATEGY))

    @classmethod
    def _discover_associated_class(mcs, class_name, attrs, inherited=None):
        """Try to find the class associated with this factory.

        In order, the following tests will be performed:
        - Lookup the FACTORY_CLASS_DECLARATION attribute
        - If an inherited associated class was provided, use it.

        Args:
            class_name (str): the name of the factory class being created
            attrs (dict): the dict of attributes from the factory class
                definition
            inherited (class): the optional associated class inherited from a
                parent factory

        Returns:
            class: the class to associate with this factory

        Raises:
            AssociatedClassError: If we were unable to associate this factory
                to a class.
        """
        if FACTORY_CLASS_DECLARATION in attrs:
            return attrs[FACTORY_CLASS_DECLARATION]

        # No specific associated class was given, and one was defined for our
        # parent, use it.
        if inherited is not None:
            return inherited

        raise AssociatedClassError(
            "Could not determine the class associated with %s. "
            "Use the FACTORY_FOR attribute to specify an associated class." %
            class_name)

    @classmethod
    def _extract_declarations(mcs, bases, attributes):
        """Extract declarations from a class definition.

        Args:
            bases (class list): parent Factory subclasses
            attributes (dict): attributes declared in the class definition

        Returns:
            dict: the original attributes, where declarations have been moved to
                _declarations and post-generation declarations to
                _postgen_declarations.
        """
        declarations = containers.DeclarationDict()
        postgen_declarations = containers.PostGenerationDeclarationDict()

        # Add parent declarations in reverse order.
        for base in reversed(bases):
            # Import parent PostGenerationDeclaration
            postgen_declarations.update_with_public(
                getattr(base, CLASS_ATTRIBUTE_POSTGEN_DECLARATIONS, {}))
            # Import all 'public' attributes (avoid those starting with _)
            declarations.update_with_public(
                    getattr(base, CLASS_ATTRIBUTE_DECLARATIONS, {}))

        # Import attributes from the class definition
        attributes = postgen_declarations.update_with_public(attributes)
        # Store protected/private attributes in 'non_factory_attrs'.
        attributes = declarations.update_with_public(attributes)

        # Store the DeclarationDict in the attributes of the newly created class
        attributes[CLASS_ATTRIBUTE_DECLARATIONS] = declarations
        attributes[CLASS_ATTRIBUTE_POSTGEN_DECLARATIONS] = postgen_declarations

        return attributes

    def __new__(mcs, class_name, bases, attrs, extra_attrs=None):
        """Record attributes as a pattern for later instance construction.

        This is called when a new Factory subclass is defined; it will collect
        attribute declaration from the class definition.

        Args:
            class_name (str): the name of the class being created
            bases (list of class): the parents of the class being created
            attrs (str => obj dict): the attributes as defined in the class
                definition
            extra_attrs (str => obj dict): extra attributes that should not be
                included in the factory defaults, even if public. This
                argument is only provided by extensions of this metaclass.

        Returns:
            A new class
        """
        parent_factories = get_factory_bases(bases)
        if not parent_factories:
            return super(FactoryMetaClass, mcs).__new__(
                    mcs, class_name, bases, attrs)

        is_abstract = attrs.pop('ABSTRACT_FACTORY', False)
        extra_attrs = {}

        if not is_abstract:

            base = parent_factories[0]

            inherited_associated_class = getattr(base,
                    CLASS_ATTRIBUTE_ASSOCIATED_CLASS, None)
            associated_class = mcs._discover_associated_class(class_name, attrs,
                    inherited_associated_class)

            # If inheriting the factory from a parent, keep a link to it.
            # This allows to use the sequence counters from the parents.
            if associated_class == inherited_associated_class:
                attrs['_base_factory'] = base

            # The CLASS_ATTRIBUTE_ASSOCIATED_CLASS must *not* be taken into
            # account when parsing the declared attributes of the new class.
            extra_attrs = {CLASS_ATTRIBUTE_ASSOCIATED_CLASS: associated_class}

        # Extract pre- and post-generation declarations
        attributes = mcs._extract_declarations(parent_factories, attrs)

        # Add extra args if provided.
        if extra_attrs:
            attributes.update(extra_attrs)

        return super(FactoryMetaClass, mcs).__new__(
                mcs, class_name, bases, attributes)

    def __str__(cls):
        return '<%s for %s>' % (cls.__name__,
            getattr(cls, CLASS_ATTRIBUTE_ASSOCIATED_CLASS).__name__)


# Factory base classes

class BaseFactory(object):
    """Factory base support for sequences, attributes and stubs."""

    # Backwards compatibility
    UnknownStrategy = UnknownStrategy
    UnsupportedStrategy = UnsupportedStrategy

    def __new__(cls, *args, **kwargs):
        """Would be called if trying to instantiate the class."""
        raise FactoryError('You cannot instantiate BaseFactory')

    # ID to use for the next 'declarations.Sequence' attribute.
    _next_sequence = None

    # Base factory, if this class was inherited from another factory. This is
    # used for sharing the _next_sequence counter among factories for the same
    # class.
    _base_factory = None

    # Holds the target class, once resolved.
    _associated_class = None

    # List of arguments that should be passed as *args instead of **kwargs
    FACTORY_ARG_PARAMETERS = ()

    # List of attributes that should not be passed to the underlying class
    FACTORY_HIDDEN_ARGS = ()

    @classmethod
    def reset_sequence(cls, value=None, force=False):
        """Reset the sequence counter."""
        if cls._base_factory:
            if force:
                cls._base_factory.reset_sequence(value=value)
            else:
                raise ValueError(
                    "Cannot reset the sequence of a factory subclass. "
                    "Please call reset_sequence() on the root factory, "
                    "or call reset_sequence(forward=True)."
                )
        else:
            cls._next_sequence = value

    @classmethod
    def _setup_next_sequence(cls):
        """Set up an initial sequence value for Sequence attributes.

        Returns:
            int: the first available ID to use for instances of this factory.
        """
        return 0

    @classmethod
    def _generate_next_sequence(cls):
        """Retrieve a new sequence ID.

        This will call, in order:
        - _generate_next_sequence from the base factory, if provided
        - _setup_next_sequence, if this is the 'toplevel' factory and the
            sequence counter wasn't initialized yet; then increase it.
        """

        # Rely upon our parents
        if cls._base_factory:
            return cls._base_factory._generate_next_sequence()

        # Make sure _next_sequence is initialized
        if cls._next_sequence is None:
            cls._next_sequence = cls._setup_next_sequence()

        # Pick current value, then increase class counter for the next call.
        next_sequence = cls._next_sequence
        cls._next_sequence += 1
        return next_sequence

    @classmethod
    def attributes(cls, create=False, extra=None):
        """Build a dict of attribute values, respecting declaration order.

        The process is:
        - Handle 'orderless' attributes, overriding defaults with provided
            kwargs when applicable
        - Handle ordered attributes, overriding them with provided kwargs when
            applicable; the current list of computed attributes is available
            to the currently processed object.
        """
        force_sequence = None
        if extra:
            force_sequence = extra.pop('__sequence', None)
        log_ctx = '%s.%s' % (cls.__module__, cls.__name__)
        logger.debug('BaseFactory: Preparing %s.%s(extra=%r)',
            cls.__module__,
            cls.__name__,
            extra,
        )
        return containers.AttributeBuilder(cls, extra, log_ctx=log_ctx).build(
            create=create,
            force_sequence=force_sequence,
        )

    @classmethod
    def declarations(cls, extra_defs=None):
        """Retrieve a copy of the declared attributes.

        Args:
            extra_defs (dict): additional definitions to insert into the
                retrieved DeclarationDict.
        """
        return getattr(cls, CLASS_ATTRIBUTE_DECLARATIONS).copy(extra_defs)

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        """Extension point for custom kwargs adjustment."""
        return kwargs

    @classmethod
    def _prepare(cls, create, **kwargs):
        """Prepare an object for this factory.

        Args:
            create: bool, whether to create or to build the object
            **kwargs: arguments to pass to the creation function
        """
        target_class = getattr(cls, CLASS_ATTRIBUTE_ASSOCIATED_CLASS)
        kwargs = cls._adjust_kwargs(**kwargs)

        # Remove 'hidden' arguments.
        for arg in cls.FACTORY_HIDDEN_ARGS:
            del kwargs[arg]

        # Extract *args from **kwargs
        args = tuple(kwargs.pop(key) for key in cls.FACTORY_ARG_PARAMETERS)

        logger.debug('BaseFactory: Generating %s.%s(%s)',
            cls.__module__,
            cls.__name__,
            utils.log_pprint(args, kwargs),
        )
        if create:
            return cls._create(target_class, *args, **kwargs)
        else:
            return cls._build(target_class, *args, **kwargs)

    @classmethod
    def _generate(cls, create, attrs):
        """generate the object.

        Args:
            create (bool): whether to 'build' or 'create' the object
            attrs (dict): attributes to use for generating the object
        """
        # Extract declarations used for post-generation
        postgen_declarations = getattr(cls,
                CLASS_ATTRIBUTE_POSTGEN_DECLARATIONS)
        postgen_attributes = {}
        for name, decl in sorted(postgen_declarations.items()):
            postgen_attributes[name] = decl.extract(name, attrs)

        # Generate the object
        obj = cls._prepare(create, **attrs)

        # Handle post-generation attributes
        results = {}
        for name, decl in sorted(postgen_declarations.items()):
            extraction_context = postgen_attributes[name]
            results[name] = decl.call(obj, create, extraction_context)

        cls._after_postgeneration(obj, create, results)

        return obj

    @classmethod
    def _after_postgeneration(cls, obj, create, results=None):
        """Hook called after post-generation declarations have been handled.

        Args:
            obj (object): the generated object
            create (bool): whether the strategy was 'build' or 'create'
            results (dict or None): result of post-generation declarations
        """
        pass

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        """Actually build an instance of the target_class.

        Customization point, will be called once the full set of args and kwargs
        has been computed.

        Args:
            target_class (type): the class for which an instance should be
                built
            args (tuple): arguments to use when building the class
            kwargs (dict): keyword arguments to use when building the class
        """
        return target_class(*args, **kwargs)

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        """Actually create an instance of the target_class.

        Customization point, will be called once the full set of args and kwargs
        has been computed.

        Args:
            target_class (type): the class for which an instance should be
                created
            args (tuple): arguments to use when creating the class
            kwargs (dict): keyword arguments to use when creating the class
        """
        return target_class(*args, **kwargs)

    @classmethod
    def build(cls, **kwargs):
        """Build an instance of the associated class, with overriden attrs."""
        attrs = cls.attributes(create=False, extra=kwargs)
        return cls._generate(False, attrs)

    @classmethod
    def build_batch(cls, size, **kwargs):
        """Build a batch of instances of the given class, with overriden attrs.

        Args:
            size (int): the number of instances to build

        Returns:
            object list: the built instances
        """
        return [cls.build(**kwargs) for _ in range(size)]

    @classmethod
    def create(cls, **kwargs):
        """Create an instance of the associated class, with overriden attrs."""
        attrs = cls.attributes(create=True, extra=kwargs)
        return cls._generate(True, attrs)

    @classmethod
    def create_batch(cls, size, **kwargs):
        """Create a batch of instances of the given class, with overriden attrs.

        Args:
            size (int): the number of instances to create

        Returns:
            object list: the created instances
        """
        return [cls.create(**kwargs) for _ in range(size)]

    @classmethod
    def stub(cls, **kwargs):
        """Retrieve a stub of the associated class, with overriden attrs.

        This will return an object whose attributes are those defined in this
        factory's declarations or in the extra kwargs.
        """
        stub_object = containers.StubObject()
        for name, value in cls.attributes(create=False, extra=kwargs).items():
            setattr(stub_object, name, value)
        return stub_object

    @classmethod
    def stub_batch(cls, size, **kwargs):
        """Stub a batch of instances of the given class, with overriden attrs.

        Args:
            size (int): the number of instances to stub

        Returns:
            object list: the stubbed instances
        """
        return [cls.stub(**kwargs) for _ in range(size)]

    @classmethod
    def generate(cls, strategy, **kwargs):
        """Generate a new instance.

        The instance will be created with the given strategy (one of
        BUILD_STRATEGY, CREATE_STRATEGY, STUB_STRATEGY).

        Args:
            strategy (str): the strategy to use for generating the instance.

        Returns:
            object: the generated instance
        """
        assert strategy in (STUB_STRATEGY, BUILD_STRATEGY, CREATE_STRATEGY)
        action = getattr(cls, strategy)
        return action(**kwargs)

    @classmethod
    def generate_batch(cls, strategy, size, **kwargs):
        """Generate a batch of instances.

        The instances will be created with the given strategy (one of
        BUILD_STRATEGY, CREATE_STRATEGY, STUB_STRATEGY).

        Args:
            strategy (str): the strategy to use for generating the instance.
            size (int): the number of instances to generate

        Returns:
            object list: the generated instances
        """
        assert strategy in (STUB_STRATEGY, BUILD_STRATEGY, CREATE_STRATEGY)
        batch_action = getattr(cls, '%s_batch' % strategy)
        return batch_action(size, **kwargs)

    @classmethod
    def simple_generate(cls, create, **kwargs):
        """Generate a new instance.

        The instance will be either 'built' or 'created'.

        Args:
            create (bool): whether to 'build' or 'create' the instance.

        Returns:
            object: the generated instance
        """
        strategy = CREATE_STRATEGY if create else BUILD_STRATEGY
        return cls.generate(strategy, **kwargs)

    @classmethod
    def simple_generate_batch(cls, create, size, **kwargs):
        """Generate a batch of instances.

        These instances will be either 'built' or 'created'.

        Args:
            size (int): the number of instances to generate
            create (bool): whether to 'build' or 'create' the instances.

        Returns:
            object list: the generated instances
        """
        strategy = CREATE_STRATEGY if create else BUILD_STRATEGY
        return cls.generate_batch(strategy, size, **kwargs)


Factory = FactoryMetaClass('Factory', (BaseFactory,), {
    'ABSTRACT_FACTORY': True,
    'FACTORY_STRATEGY': CREATE_STRATEGY,
    '__doc__': """Factory base with build and create support.

    This class has the ability to support multiple ORMs by using custom creation
    functions.
    """,
    })


# Backwards compatibility
Factory.AssociatedClassError = AssociatedClassError  # pylint: disable=W0201


class StubFactory(Factory):

    FACTORY_STRATEGY = STUB_STRATEGY
    FACTORY_FOR = containers.StubObject

    @classmethod
    def build(cls, **kwargs):
        raise UnsupportedStrategy()

    @classmethod
    def create(cls, **kwargs):
        raise UnsupportedStrategy()


class BaseDictFactory(Factory):
    """Factory for dictionary-like classes."""
    ABSTRACT_FACTORY = True

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        if args:
            raise ValueError(
                "DictFactory %r does not support FACTORY_ARG_PARAMETERS.", cls)
        return target_class(**kwargs)

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        return cls._build(target_class, *args, **kwargs)


class DictFactory(BaseDictFactory):
    FACTORY_FOR = dict


class BaseListFactory(Factory):
    """Factory for list-like classes."""
    ABSTRACT_FACTORY = True

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        if args:
            raise ValueError(
                "ListFactory %r does not support FACTORY_ARG_PARAMETERS.", cls)

        values = [v for k, v in sorted(kwargs.items())]
        return target_class(values)

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        return cls._build(target_class, *args, **kwargs)


class ListFactory(BaseListFactory):
    FACTORY_FOR = list


def use_strategy(new_strategy):
    """Force the use of a different strategy.

    This is an alternative to setting default_strategy in the class definition.
    """
    def wrapped_class(klass):
        klass.FACTORY_STRATEGY = new_strategy
        return klass
    return wrapped_class


class SQLAlchemyModelFactory(Factory):
    """Factory for SQLAlchemy models. """

    ABSTRACT_FACTORY = True
    FACTORY_HIDDEN_ARGS=('SESSION',)

    def __init__(self, session):
        self.session = session

    @classmethod
    def _get_function(cls, function_name):
        session = cls._declarations['SESSION']
        sqlalchemy = __import__(session.__module__)
        max = getattr(sqlalchemy.sql.functions, function_name)

    @classmethod
    def _setup_next_sequence(cls, *args, **kwargs):
        """Compute the next available PK, based on the 'pk' database field."""
        max = cls._get_function('max')
        session = cls._declarations['SESSION']
        pk = cls.FACTORY_FOR.__table__.primary_key.columns.values()[0].key
        max_pk = session.query(max(getattr(cls.FACTORY_FOR, pk))).one()
        return max_pk[0] + 1 if max_pk[0] else 1

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        """Create an instance of the model, and save it to the database."""
        session = cls._declarations['SESSION']
        obj = target_class(*args, **kwargs)
        session.add(obj)
        return obj
