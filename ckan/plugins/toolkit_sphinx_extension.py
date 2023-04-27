# encoding: utf-8

'''A Sphinx extension to automatically document CKAN's crazy plugins toolkit,
autodoc-style.

Sphinx's autodoc extension can document modules or classes, but although it
masquerades as a module CKAN's plugins toolkit is actually neither a module nor
a class, it's an object-instance of a class, and it's an object with weird
__getattr__ behavior too. Autodoc can't handle it, so we have this custom
Sphinx extension to automate documenting it instead.

This extension plugs into the reading phase of the Sphinx build. It intercepts
the 'toolkit' document (extensions/plugins-toolkit.rst) after Sphinx has read
the reStructuredText source from file. It modifies the source, adding in Sphinx
directives for everything in the plugins toolkit, and then the Sphinx build
continues as normal (just as if the generated reStructuredText had been entered
into plugins-toolkit.rst manually before running Sphinx).

'''
import inspect
from typing import Any, Callable, Optional

import ckan.plugins.toolkit as toolkit


def setup(app: Any):
    '''Setup this Sphinx extension. Called once when initializing Sphinx.

    '''
    # Connect to Sphinx's source-read event, the callback function will be
    # called after each source file is read.
    app.connect('source-read', source_read)


def format_function(name: str,
                    function: Callable[..., Any],
                    docstring: Optional[str] = None) -> str:
    '''Return a Sphinx .. function:: directive for the given function.

    The directive includes the function's docstring if it has one.

    :param name: the name to give to the function in the directive,
        eg. 'get_converter'
    :type name: string

    :param function: the function itself
    :type function: function

    :param docstring: if given, use this instead of introspecting the function
        to find its actual docstring
    :type docstring: string

    :returns: a Sphinx .. function:: directive for the function
    :rtype: string

    '''
    # The template we'll use to render the Sphinx function directive.
    template = ('.. py:function:: ckan.plugins.toolkit.{function}{args}\n'
                '\n'
                '{docstring}\n'
                '\n')

    # Get the arguments of the function, as a string like:
    # "(foo, bar=None, ...)"
    argstring = inspect.formatargspec(
        inspect.getfullargspec(function).args
    )

    docstring = docstring or inspect.getdoc(function)
    if docstring is None:
        docstring = ''
    else:
        # Indent the docstring by 3 spaces, as needed for the Sphinx directive.
        docstring = '\n'.join(['   ' + line for line in docstring.split('\n')])

    return template.format(function=name, args=argstring, docstring=docstring)


def format_class(
        name: str, class_: Any,
        docstring: Optional[str] = None) -> str:
    '''Return a Sphinx .. class:: directive for the given class.

    The directive includes the class's docstring if it has one.

    :param name: the name to give to the class in the directive,
        eg. 'DefaultDatasetForm'
    :type name: string

    :param class_: the class itself
    :type class_: class

    :param docstring: if given, use this instead of introspecting the class
        to find its actual docstring
    :type docstring: string

    :returns: a Sphinx .. class:: directive for the class
    :rtype: string

    '''
    # The template we'll use to render the Sphinx class directive.
    template = ('.. py:class:: ckan.plugins.toolkit.{cls}\n'
                '\n'
                '{docstring}\n'
                '\n')

    docstring = docstring or inspect.getdoc(class_)
    if docstring is None:
        docstring = ''
    else:
        # Indent the docstring by 3 spaces, as needed for the Sphinx directive.
        docstring = '\n'.join(['   ' + line for line in docstring.split('\n')])

    return template.format(cls=name, docstring=docstring)


def format_object(
        name: str, object_: Any, docstring: Optional[str] = None) -> str:
    '''Return a Sphinx .. attribute:: directive for the given object.

    The directive includes the object's class's docstring if it has one.

    :param name: the name to give to the object in the directive,
        eg. 'request'
    :type name: string

    :param object_: the object itself
    :type object_: object

    :param docstring: if given, use this instead of introspecting the object
        to find its actual docstring
    :type docstring: string

    :returns: a Sphinx .. attribute:: directive for the object
    :rtype: string

    '''
    # The template we'll use to render the Sphinx attribute directive.
    template = ('.. py:attribute:: ckan.plugins.toolkit.{obj}\n'
                '\n'
                '{docstring}\n'
                '\n')

    docstring = docstring or inspect.getdoc(object_)
    if docstring is None:
        docstring = ''
    else:
        # Indent the docstring by 3 spaces, as needed for the Sphinx directive.
        docstring = '\n'.join(['   ' + line for line in docstring.split('\n')])

    return template.format(obj=name, docstring=docstring)


def source_read(app: Any, docname: str, source: Any) -> None:
    '''Transform the contents of plugins-toolkit.rst to contain reference docs.

    '''
    # We're only interested in the 'plugins-toolkit' doc (plugins-toolkit.rst).
    if docname != 'extensions/plugins-toolkit':
        return

    source_ = '\n'
    for name, thing in inspect.getmembers(toolkit):
        if name not in toolkit.__all__:
            continue

        # The plugins toolkit can override the docstrings of some of its
        # members (e.g. things that are imported from third-party libraries)
        # by putting custom docstrings in this docstring_overrides dict.
        custom_docstring = toolkit.docstring_overrides.get(name)

        if inspect.isfunction(thing):
            source_ += format_function(name, thing, docstring=custom_docstring)
        elif inspect.ismethod(thing):
            # We document plugins toolkit methods as if they're functions. This
            # is correct because the class ckan.plugins.toolkit._Toolkit
            # actually masquerades as a module ckan.plugins.toolkit, and you
            # call its methods as if they were functions.
            source_ += format_function(name, thing, docstring=custom_docstring)
        elif inspect.isclass(thing):
            source_ += format_class(name, thing, docstring=custom_docstring)
        elif isinstance(thing, object):
            source_ += format_object(name, thing, docstring=custom_docstring)

        else:
            assert False, ("Someone added {name}:{thing} to the plugins "
                           "toolkit and this Sphinx extension doesn't know "
                           "how to document that yet. If you're that someone, "
                           "you need to add a new format_*() function for it "
                           "here or the docs won't build.".format(
                               name=name, thing=thing))

    source[0] += source_

    # This is useful for debugging the generated RST.
    # open('/tmp/source', 'w').write(source[0])
