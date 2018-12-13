"""
Parser for HTML forms, that fills in defaults and errors.  See ``render``.
"""

import re

from formencode.rewritingparser import RewritingParser, html_quote

__all__ = ['render', 'htmlliteral', 'default_formatter',
           'none_formatter', 'escape_formatter',
           'FillingParser']


def render(form, defaults=None, errors=None, use_all_keys=False,
           error_formatters=None, add_attributes=None,
           auto_insert_errors=True, auto_error_formatter=None,
           text_as_default=False, checkbox_checked_if_present=False,
           listener=None, encoding=None,
           error_class='error', prefix_error=True,
           force_defaults=True, skip_passwords=False):
    """
    Render the ``form`` (which should be a string) given the ``defaults``
    and ``errors``.  Defaults are the values that go in the input fields
    (overwriting any values that are there) and errors are displayed
    inline in the form (and also effect input classes).  Returns the
    rendered string.

    If ``auto_insert_errors`` is true (the default) then any errors
    for which ``<form:error>`` tags can't be found will be put just
    above the associated input field, or at the top of the form if no
    field can be found.

    If ``use_all_keys`` is true, if there are any extra fields from
    defaults or errors that couldn't be used in the form it will be an
    error.

    ``error_formatters`` is a dictionary of formatter names to
    one-argument functions that format an error into HTML.  Some
    default formatters are provided if you don't provide this.

    ``error_class`` is the class added to input fields when there is
    an error for that field.

    ``add_attributes`` is a dictionary of field names to a dictionary
    of attribute name/values.  If the name starts with ``+`` then the
    value will be appended to any existing attribute (e.g.,
    ``{'+class': ' important'}``).

    ``auto_error_formatter`` is used to create the HTML that goes
    above the fields.  By default it wraps the error message in a span
    and adds a ``<br>``.

    If ``text_as_default`` is true (default false) then ``<input
    type="unknown">`` will be treated as text inputs.

    If ``checkbox_checked_if_present`` is true (default false) then
    ``<input type="checkbox">`` will be set to ``checked`` if any
    corresponding key is found in the ``defaults`` dictionary, even
    a value that evaluates to False (like an empty string).  This
    can be used to support pre-filling of checkboxes that do not have
    a ``value`` attribute, since browsers typically will only send
    the name of the checkbox in the form submission if the checkbox
    is checked, so simply the presence of the key would mean the box
    should be checked.

    ``listener`` can be an object that watches fields pass; the only
    one currently is in ``htmlfill_schemabuilder.SchemaBuilder``

    ``encoding`` specifies an encoding to assume when mixing str and
    unicode text in the template.

    ``prefix_error`` specifies if the HTML created by auto_error_formatter is
    put before the input control (default) or after the control.

    ``force_defaults`` specifies if a field default is not given in
    the ``defaults`` dictionary then the control associated with the
    field should be set as an unsuccessful control. So checkboxes will
    be cleared, radio and select controls will have no value selected,
    and textareas will be emptied. This defaults to ``True``, which is
    appropriate the defaults are the result of a form submission.

    ``skip_passwords`` specifies if password fields should be skipped when
    rendering form-content.  If disabled the password fields will not be filled
    with anything, which is useful when you don't want to return a user's
    password in plain-text source.
    """
    if defaults is None:
        defaults = {}
    if auto_insert_errors and auto_error_formatter is None:
        auto_error_formatter = default_formatter
    p = FillingParser(
        defaults=defaults, errors=errors,
        use_all_keys=use_all_keys,
        error_formatters=error_formatters,
        add_attributes=add_attributes,
        auto_error_formatter=auto_error_formatter,
        text_as_default=text_as_default,
        checkbox_checked_if_present=checkbox_checked_if_present,
        listener=listener, encoding=encoding,
        prefix_error=prefix_error,
        error_class=error_class,
        force_defaults=force_defaults,
        skip_passwords=skip_passwords,
        )
    p.feed(form)
    p.close()
    return p.text()


class htmlliteral(object):

    def __init__(self, html, text=None):
        if text is None:
            text = re.sub(r'<.*?>', '', html)
            text = html.replace('&gt;', '>')
            text = html.replace('&lt;', '<')
            text = html.replace('&quot;', '"')
            # @@: Not very complete
        self.html = html
        self.text = text

    def __str__(self):
        return self.text

    def __repr__(self):
        return '<%s html=%r text=%r>' % (
            self.__class__.__name__, self.html, self.text)

    def __html__(self):
        return self.html


def default_formatter(error):
    """
    Formatter that escapes the error, wraps the error in a span with
    class ``error-message``, and adds a ``<br>``
    """
    return '<span class="error-message">%s</span><br />\n' % html_quote(error)


def none_formatter(error):
    """
    Formatter that does nothing, no escaping HTML, nothin'
    """
    return error


def escape_formatter(error):
    """
    Formatter that escapes HTML, no more.
    """
    return html_quote(error)


def escapenl_formatter(error):
    """
    Formatter that escapes HTML, and translates newlines to ``<br>``
    """
    error = html_quote(error)
    error = error.replace('\n', '<br>\n')
    return error


def ignore_formatter(error):
    """
    Formatter that emits nothing, regardless of the error.
    """
    return ''


class FillingParser(RewritingParser):
    r"""
    Fills HTML with default values, as in a form.

    Examples::

        >>> defaults = dict(name='Bob Jones',
        ...             occupation='Crazy Cultist',
        ...             address='14 W. Canal\nNew Guinea',
        ...             living='no',
        ...             nice_guy=0)
        >>> parser = FillingParser(defaults)
        >>> parser.feed('''<input type="text" name="name" value="fill">
        ... <select name="occupation"> <option value="">Default</option>
        ... <option value="Crazy Cultist">Crazy cultist</option> </select>
        ... <textarea cols="20" style="width: 100%" name="address">
        ... An address</textarea>
        ... <input type="radio" name="living" value="yes">
        ... <input type="radio" name="living" value="no">
        ... <input type="checkbox" name="nice_guy" checked="checked">''')
        >>> parser.close()
        >>> print parser.text() # doctest: +NORMALIZE_WHITESPACE
        <input type="text" name="name" value="Bob Jones">
        <select name="occupation">
        <option value="">Default</option>
        <option value="Crazy Cultist" selected="selected">Crazy cultist</option>
        </select>
        <textarea cols="20" style="width: 100%" name="address">14 W. Canal
        New Guinea</textarea>
        <input type="radio" name="living" value="yes">
        <input type="radio" name="living" value="no" checked="checked">
        <input type="checkbox" name="nice_guy">

    """

    default_encoding = 'utf8'

    text_input_types = set("text hidden search tel url email datetime date"
        " month week time datetime-local number range color".split())

    def __init__(self, defaults, errors=None, use_all_keys=False,
                 error_formatters=None, error_class='error',
                 add_attributes=None, listener=None,
                 auto_error_formatter=None,
                 text_as_default=False, checkbox_checked_if_present=False,
                 encoding=None, prefix_error=True,
                 force_defaults=True, skip_passwords=False):
        RewritingParser.__init__(self)
        self.source = None
        self.lines = None
        self.source_pos = None
        self.defaults = defaults
        self.in_textarea = None
        self.skip_textarea = False
        self.last_textarea_name = None
        self.in_select = None
        self.skip_next = False
        self.errors = errors or {}
        if isinstance(self.errors, basestring):
            self.errors = {None: self.errors}
        self.in_error = None
        self.skip_error = False
        self.use_all_keys = use_all_keys
        self.used_keys = set()
        self.used_errors = set()
        if error_formatters is None:
            self.error_formatters = default_formatter_dict
        else:
            self.error_formatters = error_formatters
        self.error_class = error_class
        self.add_attributes = add_attributes or {}
        self.listener = listener
        self.auto_error_formatter = auto_error_formatter
        self.text_as_default = text_as_default
        self.checkbox_checked_if_present = checkbox_checked_if_present
        self.encoding = encoding
        self.prefix_error = prefix_error
        self.force_defaults = force_defaults
        self.skip_passwords = skip_passwords

    def str_compare(self, str1, str2):
        """
        Compare the two objects as strings (coercing to strings if necessary).
        Also uses encoding to compare the strings.
        """
        if not isinstance(str1, basestring):
            if hasattr(str1, '__unicode__'):
                str1 = unicode(str1)
            else:
                str1 = str(str1)
        if type(str1) == type(str2):
            return str1 == str2
        if isinstance(str1, unicode):
            str1 = str1.encode(self.encoding or self.default_encoding)
        else:
            str2 = str2.encode(self.encoding or self.default_encoding)
        return str1 == str2

    def close(self):
        self.handle_misc(None)
        RewritingParser.close(self)
        unused_errors = self.errors.copy()
        for key in self.used_errors:
            if key in unused_errors:
                del unused_errors[key]
        if self.auto_error_formatter:
            for key, value in unused_errors.iteritems():
                error_message = self.auto_error_formatter(value)
                error_message = '<!-- for: %s -->\n%s' % (key, error_message)
                self.insert_at_marker(
                    key, error_message)
            unused_errors = {}
        if self.use_all_keys:
            unused = self.defaults.copy()
            for key in self.used_keys:
                if key in unused:
                    del unused[key]
            assert not unused, (
                "These keys from defaults were not used in the form: %s"
                % ', '.join(unused))
            if unused_errors:
                error_text = ['%s: %s' % (key, self.errors[key])
                    for key in sorted(unused_errors)]
                assert False, (
                    "These errors were not used in the form: %s"
                    % ', '.join(error_text))
        if self.encoding is not None:
            new_content = []
            for item in self._content:
                if (unicode is not str  # Python 2
                        and isinstance(item, str)):
                    item = item.decode(self.encoding)
                new_content.append(item)
            self._content = new_content
        self._text = self._get_text()

    def skip_output(self):
        return (self.in_textarea and self.skip_textarea) or self.skip_error

    def add_key(self, key):
        self.used_keys.add(key)

    def handle_starttag(self, tag, attrs, startend=False):
        self.write_pos()
        if tag == 'input':
            self.handle_input(attrs, startend)
        elif tag == 'textarea':
            self.handle_textarea(attrs)
        elif tag == 'select':
            self.handle_select(attrs)
        elif tag == 'option':
            self.handle_option(attrs)
            return
        elif tag == 'form:error':
            self.handle_error(attrs)
            return
        elif tag == 'form:iferror':
            self.handle_iferror(attrs)
            return
        else:
            return
        if self.listener:
            self.listener.listen_input(self, tag, attrs)

    def handle_endtag(self, tag):
        self.write_pos()
        if tag == 'textarea':
            self.handle_end_textarea()
        elif tag == 'select':
            self.handle_end_select()
        elif tag == 'form:error':
            self.handle_end_error()
        elif tag == 'form:iferror':
            self.handle_end_iferror()

    def handle_startendtag(self, tag, attrs):
        return self.handle_starttag(tag, attrs, True)

    def handle_iferror(self, attrs):
        name = self.get_attr(attrs, 'name')
        assert name, (
            "Name attribute in <iferror> required at %i:%i" % self.getpos())
        notted = name.startswith('not ')
        if notted:
            name = name.split(None, 1)[1]
        self.in_error = name
        ok = self.errors.get(name)
        if notted:
            ok = not ok
        if not ok:
            self.skip_error = True
        self.skip_next = True

    def handle_end_iferror(self):
        self.in_error = None
        self.skip_error = False
        self.skip_next = True

    def handle_error(self, attrs):
        name = self.get_attr(attrs, 'name')
        if name is None:
            name = self.in_error
        assert name is not None, (
            "Name attribute in <form:error> required"
            " if not contained in <form:iferror> at %i:%i" % self.getpos())
        formatter = self.get_attr(attrs, 'format') or 'default'
        error = self.errors.get(name, '')
        if error:
            error = self.error_formatters[formatter](error)
            self.write_text(error)
        self.skip_next = True
        self.used_errors.add(name)

    def handle_end_error(self):
        self.skip_next = True

    def handle_input(self, attrs, startend):
        t = (self.get_attr(attrs, 'type') or 'text').lower()
        name = self.get_attr(attrs, 'name')
        if self.prefix_error:
            self.write_marker(name)
        value = self.defaults.get(name)
        if (unicode is not str  # Python 2
                and isinstance(name, unicode) and isinstance(value, str)):
            value = value.decode(self.encoding or self.default_encoding)
        if name in self.add_attributes:
            for attr_name, attr_value in self.add_attributes[name].iteritems():
                if attr_name.startswith('+'):
                    attr_name = attr_name[1:]
                    self.set_attr(attrs, attr_name,
                        self.get_attr(attrs, attr_name, '') + attr_value)
                else:
                    self.set_attr(attrs, attr_name, attr_value)
        if (self.error_class
                and self.errors.get(self.get_attr(attrs, 'name'))):
            self.add_class(attrs, self.error_class)
        if t in self.text_input_types:
            if value is None and not self.force_defaults:
                value = self.get_attr(attrs, 'value', '')
            self.set_attr(attrs, 'value', value)
            self.write_tag('input', attrs, startend)
            self.skip_next = True
            self.add_key(name)
        elif t == 'checkbox':
            if self.force_defaults:
                selected = False
            else:
                selected = self.get_attr(attrs, 'checked')
            if not self.get_attr(attrs, 'value'):
                if self.checkbox_checked_if_present:
                    selected = name in self.defaults
                else:
                    selected = value
            elif self.selected_multiple(value,
                                        self.get_attr(attrs, 'value', '')):
                selected = True
            if selected:
                self.set_attr(attrs, 'checked', 'checked')
            else:
                self.del_attr(attrs, 'checked')
            self.write_tag('input', attrs, startend)
            self.skip_next = True
            self.add_key(name)
        elif t == 'radio':
            if self.str_compare(value, self.get_attr(attrs, 'value', '')):
                self.set_attr(attrs, 'checked', 'checked')
            elif self.force_defaults or name in self.defaults:
                self.del_attr(attrs, 'checked')
            self.write_tag('input', attrs, startend)
            self.skip_next = True
            self.add_key(name)
        elif t == 'password':
            if self.skip_passwords:
                return
            if value is None and not self.force_defaults:
                value = value or self.get_attr(attrs, 'value', '')
            self.set_attr(attrs, 'value', value)
            self.write_tag('input', attrs, startend)
            self.skip_next = True
            self.add_key(name)
        elif t in ('file', 'image'):
            self.write_tag('input', attrs, startend)
            self.skip_next = True
            self.add_key(name)
        elif t in ('submit', 'reset', 'button'):
            self.set_attr(attrs, 'value', value or
                          self.get_attr(attrs, 'value', ''))
            self.write_tag('input', attrs, startend)
            self.skip_next = True
            self.add_key(name)
        elif self.text_as_default:
            if value is None:
                value = self.get_attr(attrs, 'value', '')
            self.set_attr(attrs, 'value', value)
            self.write_tag('input', attrs, startend)
            self.skip_next = True
            self.add_key(name)
        else:
            assert False, ("I don't know about this kind of <input>:"
                " %s at %i:%i" % ((t,) + self.getpos()))
        if not self.prefix_error:
            self.write_marker(name)

    def handle_textarea(self, attrs):
        name = self.get_attr(attrs, 'name')
        if self.prefix_error:
            self.write_marker(name)
        if (self.error_class
                and self.errors.get(name)):
            self.add_class(attrs, self.error_class)
        value = self.defaults.get(name, '')
        if value or self.force_defaults:
            self.write_tag('textarea', attrs)
            self.write_text(html_quote(value))
            self.write_text('</textarea>')
            self.skip_textarea = True
        self.in_textarea = True
        self.last_textarea_name = name
        self.add_key(name)

    def handle_end_textarea(self):
        if self.skip_textarea:
            self.skip_textarea = False
        else:
            self.write_text('</textarea>')
        self.in_textarea = False
        self.skip_next = True
        if not self.prefix_error:
            self.write_marker(self.last_textarea_name)
        self.last_textarea_name = None

    def handle_select(self, attrs):
        name = self.get_attr(attrs, 'name', False)
        if name and self.prefix_error:
            self.write_marker(name)
        if (self.error_class
                and self.errors.get(name)):
            self.add_class(attrs, self.error_class)
        self.in_select = self.get_attr(attrs, 'name', False)
        self.write_tag('select', attrs)
        self.skip_next = True
        self.add_key(self.in_select)

    def handle_end_select(self):
        self.write_text('</select>')
        self.skip_next = True
        if not self.prefix_error and self.in_select:
            self.write_marker(self.in_select)
        self.in_select = None

    def handle_option(self, attrs):
        assert self.in_select is not None, (
            "<option> outside of <select> at %i:%i" % self.getpos())
        if self.in_select is not False:
            if self.force_defaults or self.in_select in self.defaults:
                if self.selected_multiple(self.defaults.get(self.in_select),
                                          self.get_attr(attrs, 'value', '')):
                    self.set_attr(attrs, 'selected', 'selected')
                    self.add_key(self.in_select)
                else:
                    self.del_attr(attrs, 'selected')
        self.write_tag('option', attrs)
        self.skip_next = True

    def selected_multiple(self, obj, value):
        """
        Returns true/false if obj indicates that value should be
        selected.  If obj has a __contains__ method it is used, otherwise
        identity is used.
        """
        if obj is None:
            return False
        if isinstance(obj, basestring):
            return obj == value
        if hasattr(obj, '__contains__'):
            if value in obj:
                return True
        if hasattr(obj, '__iter__'):
            for inner in obj:
                if self.str_compare(inner, value):
                    return True
        return self.str_compare(obj, value)

    def write_marker(self, marker):
        self._content.append((marker,))

    def insert_at_marker(self, marker, text):
        for i, item in enumerate(self._content):
            if item == (marker,):
                self._content.insert(i, text)
                break
        else:
            self._content.insert(0, text)


# This can potentially be extended globally
default_formatter_dict = dict(
    default=default_formatter,
    none=none_formatter,
    escape=escape_formatter,
    escapenl=escapenl_formatter,
    ignore=ignore_formatter)
