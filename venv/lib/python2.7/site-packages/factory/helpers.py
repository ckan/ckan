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


"""Simple wrappers around Factory class definition."""


from . import base
from . import declarations


def make_factory(klass, **kwargs):
    """Create a new, simple factory for the given class."""
    factory_name = '%sFactory' % klass.__name__
    kwargs[base.FACTORY_CLASS_DECLARATION] = klass
    base_class = kwargs.pop('FACTORY_CLASS', base.Factory)

    factory_class = type(base.Factory).__new__(
            type(base.Factory), factory_name, (base_class,), kwargs)
    factory_class.__name__ = '%sFactory' % klass.__name__
    factory_class.__doc__ = 'Auto-generated factory for class %s' % klass
    return factory_class


def build(klass, **kwargs):
    """Create a factory for the given class, and build an instance."""
    return make_factory(klass, **kwargs).build()


def build_batch(klass, size, **kwargs):
    """Create a factory for the given class, and build a batch of instances."""
    return make_factory(klass, **kwargs).build_batch(size)


def create(klass, **kwargs):
    """Create a factory for the given class, and create an instance."""
    return make_factory(klass, **kwargs).create()


def create_batch(klass, size, **kwargs):
    """Create a factory for the given class, and create a batch of instances."""
    return make_factory(klass, **kwargs).create_batch(size)


def stub(klass, **kwargs):
    """Create a factory for the given class, and stub an instance."""
    return make_factory(klass, **kwargs).stub()


def stub_batch(klass, size, **kwargs):
    """Create a factory for the given class, and stub a batch of instances."""
    return make_factory(klass, **kwargs).stub_batch(size)


def generate(klass, strategy, **kwargs):
    """Create a factory for the given class, and generate an instance."""
    return make_factory(klass, **kwargs).generate(strategy)


def generate_batch(klass, strategy, size, **kwargs):
    """Create a factory for the given class, and generate instances."""
    return make_factory(klass, **kwargs).generate_batch(strategy, size)


# We're reusing 'create' as a keyword.
# pylint: disable=W0621


def simple_generate(klass, create, **kwargs):
    """Create a factory for the given class, and simple_generate an instance."""
    return make_factory(klass, **kwargs).simple_generate(create)


def simple_generate_batch(klass, create, size, **kwargs):
    """Create a factory for the given class, and simple_generate instances."""
    return make_factory(klass, **kwargs).simple_generate_batch(create, size)


# pylint: enable=W0621


def lazy_attribute(func):
    return declarations.LazyAttribute(func)


def iterator(func):
    """Turn a generator function into an iterator attribute."""
    return declarations.Iterator(func())


def sequence(func):
    return declarations.Sequence(func)


def lazy_attribute_sequence(func):
    return declarations.LazyAttributeSequence(func)


def container_attribute(func):
    return declarations.ContainerAttribute(func, strict=False)


def post_generation(fun):
    return declarations.PostGeneration(fun)
