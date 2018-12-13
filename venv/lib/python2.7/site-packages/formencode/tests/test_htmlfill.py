# -*- coding: utf-8 -*-

import os
import re
import sys

import xml.etree.ElementTree as ET
try:
    XMLParseError = ET.ParseError
except AttributeError:  # Python < 2.7
    from xml.parsers.expat import ExpatError as XMLParseError

from htmlentitydefs import name2codepoint

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from formencode import htmlfill, htmlfill_schemabuilder
from formencode.doctest_xml_compare import xml_compare


def test_inputoutput():
    data_dir = os.path.join(os.path.dirname(__file__), 'htmlfill_data')
    for fn in os.listdir(data_dir):
        if fn.startswith('data-'):
            fn = os.path.join(data_dir, fn)
            yield run_filename, fn


def run_filename(filename):
    f = open(filename)
    content = f.read()
    f.close()
    parts = re.split(r'---*', content)
    template = parts[0]
    expected = parts[1]
    if len(parts) == 3:
        data_content = parts[2].strip()
    elif len(parts) > 3:
        assert False, "Too many sections: %s" % parts[3:]
    else:
        data_content = ''
    namespace = {}
    if data_content:
        exec data_content in namespace
    data = namespace.copy()
    data['defaults'] = data.get('defaults', {})
    if 'check' in data:
        checker = data.pop('check')
    else:
        def checker(p, s):
            pass
    for name in data.keys():
        if name.startswith('_') or hasattr('__builtin__', name):
            del data[name]
    listener = htmlfill_schemabuilder.SchemaBuilder()
    p = htmlfill.FillingParser(listener=listener, **data)
    p.feed(template)
    p.close()
    output = p.text()

    def reporter(v):
        print v

    try:
        output_xml = ET.XML(output)
        expected_xml = ET.XML(expected)
    except XMLParseError:
        comp = output.strip() == expected.strip()
    else:
        comp = xml_compare(output_xml, expected_xml, reporter)
    if not comp:
        print '---- Output:   ----'
        print output
        print '---- Expected: ----'
        print expected
        assert False
    checker(p, listener.schema())
    checker(p, htmlfill_schemabuilder.parse_schema(template))


def test_no_trailing_newline():
    assert (htmlfill.render('<html><body></body></html>', {}, {})
            == '<html><body></body></html>')


def test_escape_defaults():
    rarr = unichr(name2codepoint['rarr'])
    assert (htmlfill.render('<input type="submit" value="next&gt;&rarr;">', {}, {})
            == '<input type="submit" value="next&gt;%s">' % rarr)
    assert (htmlfill.render('<input type="submit" value="1&amp;2">', {}, {})
            == '<input type="submit" value="1&amp;2">')
    assert (htmlfill.render('<input type="submit" value="Japan - &#x65E5;&#x672C; Nihon" />',
                            {}, {}) ==
            u'<input type="submit" value="Japan - 日本 Nihon" />')


def test_xhtml():
    result = htmlfill.render('<form:error name="code"/>', errors={'code': 'an error'})
    assert 'an error' in result


def test_html5():
    result = htmlfill.render('<input type="number" name="quantity">', {'quantity': '10'})
    assert result == '<input type="number" name="quantity" value="10">'
    try:
        result = htmlfill.render('<input type="unknown" name="quantity">', {'quantity': '10'})
    except AssertionError as e:
        assert "I don't know about this kind of <input>: unknown at 1:0" in str(e)
    result = htmlfill.render('<input type="unknown" name="quantity">', {'quantity': '10'}, text_as_default=True)
    assert result == '<input type="unknown" name="quantity" value="10">'


def test_trailing_error():
    assert (htmlfill.render('<input type="text" name="email">', errors={'email': 'error'},
                            prefix_error=False)
            == '<input type="text" name="email" class="error" value=""><!-- for: email -->\n<span class="error-message">error</span><br />\n')
    assert (htmlfill.render('<textarea name="content"></textarea>', errors={'content': 'error'},
                            prefix_error=False)
            == '<textarea name="content" class="error"></textarea><!-- for: content -->\n<span class="error-message">error</span><br />\n')
    assert (htmlfill.render('<select name="type"><option value="foo">foo</option></select>', errors={'type': 'error'},
                            prefix_error=False)
            == '<select name="type" class="error"><option value="foo">foo</option></select><!-- for: type -->\n<span class="error-message">error</span><br />\n')


def test_iferror():
    assert (htmlfill.render('<form:iferror name="field1">an error</form:iferror>', errors={}, auto_insert_errors=False)
            == '')
    assert (htmlfill.render('<form:iferror name="field1">an error</form:iferror>', errors={'field1': 'foo'}, auto_insert_errors=False)
            == 'an error')
    assert (htmlfill.render('<form:iferror name="not field1">no errors</form:iferror>', errors={}, auto_insert_errors=False)
            == 'no errors')
    assert (htmlfill.render('<form:iferror name="not field1">no errors</form:iferror>', errors={'field1': 'foo'}, auto_insert_errors=False)
            == '')
    assert (htmlfill.render('<form:iferror name="field1">errors</form:iferror><form:iferror name="not field1">no errors</form:iferror>',
                            errors={}, auto_insert_errors=False)
            == 'no errors')
    assert (htmlfill.render('<form:iferror name="field1">errors</form:iferror><form:iferror name="not field1">no errors</form:iferror>',
                            errors={'field1': 'foo'}, auto_insert_errors=False)
            == 'errors')
    try:
        htmlfill.render('<form:iferror noname="nothing">errors</form:iferror>')
    except AssertionError as e:
        assert str(e) == "Name attribute in <iferror> required at 1:0"


def test_literal():
    assert (htmlfill.render('<form:error name="foo" />',
                            errors={'foo': htmlfill.htmlliteral('<test>')})
            == '<span class="error-message"><test></span><br />\n')


def test_image_submit():
    assert (htmlfill.render('<input name="image-submit" type="image" src="foo.jpg" value="bar">',
                            defaults={'image-submit': 'blahblah'})
            == '<input name="image-submit" type="image" src="foo.jpg" value="bar">')


def test_checkbox():
    assert (htmlfill.render('<input name="checkbox" type="checkbox" value="bar">',
                            defaults={'checkbox': 'bar'})
            == '<input name="checkbox" type="checkbox" value="bar" checked="checked">')
    assert (htmlfill.render('<input name="checkbox" type="checkbox">',
                            defaults={'checkbox': ''})
            == '<input name="checkbox" type="checkbox">')
    assert (htmlfill.render('<input name="checkbox" type="checkbox">',
                            defaults={'checkbox': ''}, checkbox_checked_if_present=True)
            == '<input name="checkbox" type="checkbox" checked="checked">')
    assert (htmlfill.render('<input name="checkbox" type="checkbox" value="bar">',
                            defaults={'checkbox': ''}, checkbox_checked_if_present=True)
            == '<input name="checkbox" type="checkbox" value="bar">')
    assert (htmlfill.render('<input name="checkbox" type="checkbox" value="">',
                            defaults={'checkbox': ''}, checkbox_checked_if_present=True)
            == '<input name="checkbox" type="checkbox" value="" checked="checked">')
    assert (htmlfill.render('<input name="checkbox" type="checkbox" value="">',
                            defaults={'checkbox': ''})
            == '<input name="checkbox" type="checkbox" value="">')


def test_unicode():
    assert (htmlfill.render(u'<input type="checkbox" name="tags" value="2" />',
                           dict(tags=[])) ==
            '<input type="checkbox" name="tags" value="2" />')


def test_password():
    assert (htmlfill.render('<input name="password" type="password" value="">',
                            defaults={'password': 'secure passwd'})
            == '<input name="password" type="password" value="secure passwd">')
    assert (htmlfill.render('<input name="password" type="password" value="">',
                            defaults={'password': 'secure passwd'},
                            skip_passwords=True)
            == '<input name="password" type="password" value="">')
    assert (htmlfill.render('<input name="password" type="password">',
                            defaults={'password': 'secure passwd'})
            == '<input name="password" type="password" value="secure passwd">')
    assert (htmlfill.render('<input name="password" type="password">',
                            defaults={'password': 'secure passwd'},
                            skip_passwords=True)
            == '<input name="password" type="password">')


def test_not_force_defaults_text():
    html = """<input type="text" name="text-1" class="my_text" value="i like this text" />"""
    rendered_html = htmlfill.render(html, defaults=dict(),
                                    force_defaults=False)
    assert html == rendered_html, rendered_html


def test_not_force_defaults_text_value():
    html = """<input type="text" name="text-1" class="my_text" value="i like this text" />"""
    expected_html = """<input type="text" name="text-1" class="my_text" value="this text is better" />"""
    rendered_html = htmlfill.render(html, defaults={"text-1": "this text is better"},
                                    force_defaults=False)
    assert expected_html == rendered_html, rendered_html


def test_not_force_defaults_text_explicit_empty_value():
    html = """<input type="text" name="text-1" class="my_text" value="i like this text" />"""
    expected_html = """<input type="text" name="text-1" class="my_text" value="" />"""
    rendered_html = htmlfill.render(html, defaults={"text-1": ""},
                                    force_defaults=False)
    assert expected_html == rendered_html, rendered_html


def test_force_defaults_text():
    html = """<input type="text" name="text-1" class="my_text" value="i like this text" />"""
    expected_html = """<input type="text" name="text-1" class="my_text" value="" />"""
    rendered_html = htmlfill.render(html, defaults=dict())
    assert expected_html == rendered_html, rendered_html


def test_not_force_defaults_textarea():
    html = """<textarea name="textarea-1" class="my_textarea">i like this text</textarea>"""
    rendered_html = htmlfill.render(html, defaults=dict(),
                                    force_defaults=False)
    assert html == rendered_html, rendered_html


def test_not_force_defaults_textarea_value():
    html = """<textarea name="textarea-1" class="my_textarea">i like this text</textarea>"""
    expected_html = """<textarea name="textarea-1" class="my_textarea">this text is better</textarea>"""
    rendered_html = htmlfill.render(html, defaults={"textarea-1": "this text is better"},
                                    force_defaults=False)
    assert expected_html == rendered_html, rendered_html


def test_force_defaults_textarea():
    html = """<textarea name="textarea-1" class="my_textarea">i like this text</textarea>"""
    expected_html = \
        """<textarea name="textarea-1" class="my_textarea"></textarea>"""
    rendered_html = htmlfill.render(html, defaults=dict())
    assert expected_html == rendered_html, rendered_html


def test_not_force_defaults_password():
    html = """<input type="password" name="password-1" class="my_password" value="i like this password" />"""
    rendered_html = htmlfill.render(html, defaults=dict(),
                                    force_defaults=False)
    assert html == rendered_html, rendered_html


def test_not_force_defaults_password_value():
    html = """<input type="password" name="password-1" class="my_password" value="i like this password" />"""
    expected_html = """<input type="password" name="password-1" class="my_password" value="this password is better" />"""
    rendered_html = htmlfill.render(html, defaults={"password-1": "this password is better"},
                                    force_defaults=False)
    assert expected_html == rendered_html, rendered_html


def test_not_force_defaults_password_explicit_empty_value():
    html = """<input type="password" name="password-1" class="my_password" value="i like this password" />"""
    expected_html = """<input type="password" name="password-1" class="my_password" value="" />"""
    rendered_html = htmlfill.render(html, defaults={"password-1": ""},
                                    force_defaults=False)
    assert expected_html == rendered_html, rendered_html


def test_force_defaults_password():
    html = """<input type="password" name="password-1" class="my_password" value="i like this password" />"""
    expected_html = """<input type="password" name="password-1" class="my_password" value="" />"""
    rendered_html = htmlfill.render(html, defaults=dict())
    assert expected_html == rendered_html, rendered_html


def test_not_force_defaults_checkbox():
    html = """<input type="checkbox" name="checkbox-1" class="my_checkbox" checked="checked" value="cb">"""
    rendered_html = htmlfill.render(html, defaults=dict(),
                                    force_defaults=False)
    assert html == rendered_html, rendered_html


def test_force_defaults_checkbox():
    html = """<input type="checkbox" name="checkbox-1" class="my_checkbox" checked="checked" value="cb">"""
    expected_html = \
        """<input type="checkbox" name="checkbox-1" class="my_checkbox" value="cb">"""
    rendered_html = htmlfill.render(html, defaults=dict())
    assert expected_html == rendered_html, rendered_html


def test_not_force_defaults_checkbox_default_unchecked():
    html = """<input type="checkbox" name="checkbox-1" class="my_checkbox" checked="checked" value="cb">"""
    expected_html = \
        """<input type="checkbox" name="checkbox-1" class="my_checkbox" value="cb">"""
    rendered_html = htmlfill.render(html, defaults={"checkbox-1": False})
    assert expected_html == rendered_html, rendered_html


def test_not_force_defaults_checkbox_default_checked():
    html = """<input type="checkbox" name="checkbox-1" class="my_checkbox" value="cb">"""
    expected_html = \
        """<input type="checkbox" name="checkbox-1" class="my_checkbox" value="cb" checked="checked">"""
    rendered_html = htmlfill.render(html, defaults={"checkbox-1": "cb"},
                                    force_defaults=False)
    assert expected_html == rendered_html, rendered_html


def test_not_force_defaults_radio():
    html = """<input type="radio" name="radio-1" class="my_radio" checked="checked" value="cb">"""
    rendered_html = htmlfill.render(html, defaults=dict(),
                                    force_defaults=False)
    assert html == rendered_html, rendered_html


def test_not_force_defaults_radio_unchecked():
    html = """<input type="radio" name="radio-1" class="my_radio" checked="checked" value="cb">"""
    expected_html = """<input type="radio" name="radio-1" class="my_radio" value="cb">"""
    rendered_html = htmlfill.render(html, defaults={"radio-1": "ba"},
                                    force_defaults=False)
    assert expected_html == rendered_html, rendered_html


def test_not_force_defaults_radio_checked():
    html = """<input type="radio" name="radio-1" class="my_radio" value="cb">"""
    expected_html = """<input type="radio" name="radio-1" class="my_radio" value="cb" checked="checked">"""
    rendered_html = htmlfill.render(html, defaults={"radio-1": "cb"},
                                    force_defaults=False)
    assert expected_html == rendered_html, rendered_html


def test_force_defaults_radio():
    html = """<input type="radio" name="radio-1" class="my_radio" checked="checked" value="cb">"""
    expected_html = """<input type="radio" name="radio-1" class="my_radio" value="cb">"""
    rendered_html = htmlfill.render(html, defaults=dict())
    assert expected_html == rendered_html, rendered_html


def test_not_force_defaults_select():
    html = """
<select name="select-1" class="my_select">
  <option value="option-1" selected="selected">this is option-1</option>
</select>
"""
    rendered_html = htmlfill.render(html, defaults=dict(),
                                    force_defaults=False)
    assert html == rendered_html, rendered_html


def test_not_force_defaults_select_selected():
    html = """
<select name="select-1" class="my_select">
  <option value="option-1">this is option-1</option>
</select>
"""
    expected_html = """
<select name="select-1" class="my_select">
  <option value="option-1" selected="selected">this is option-1</option>
</select>
"""
    rendered_html = htmlfill.render(html, defaults={"select-1": "option-1"},
                                    force_defaults=False)
    assert expected_html == rendered_html, rendered_html


def test_not_force_defaults_select_not_selected():
    html = """
<select name="select-1" class="my_select">
  <option value="option-1" selected="selected">this is option-1</option>
</select>
"""
    expected_html = """
<select name="select-1" class="my_select">
  <option value="option-1">this is option-1</option>
</select>
"""
    rendered_html = htmlfill.render(html, defaults={"select-1": "option-2"},
                                    force_defaults=False)
    assert expected_html == rendered_html, rendered_html


def test_force_defaults_select():
    html = """
<select name="select-1" class="my_select">
  <option value="option-1" selected="selected">this is option-1</option>
</select>
"""
    expected_html = """
<select name="select-1" class="my_select">
  <option value="option-1">this is option-1</option>
</select>
"""
    rendered_html = htmlfill.render(html, defaults=dict())
    assert expected_html == rendered_html, rendered_html


def test_select_empty_option_value_selected():
    html = """
<select name="select-1" class="my_select">
  <option value="">this is option-1</option>
</select>
"""
    expected_html = """
<select name="select-1" class="my_select">
  <option value="" selected="selected">this is option-1</option>
</select>
"""
    rendered_html = htmlfill.render(html, defaults={"select-1": ""})
    assert expected_html == rendered_html, rendered_html


def test_select_empty_option_value_not_selected():
    html = """
<select name="select-1" class="my_select">
  <option value="">this is option-1</option>
</select>
"""
    expected_html = """
<select name="select-1" class="my_select">
  <option value="">this is option-1</option>
</select>
"""
    rendered_html = htmlfill.render(html, defaults={})
    assert expected_html == rendered_html, rendered_html


def test_script_quoting():
    html = """
<script>Some <weird JS</script>
Then a form <input type="text" name="name">
"""
    expected_html = """
<script>Some <weird JS</script>
Then a form <input type="text" name="name" value="foo">
"""
    rendered_html = htmlfill.render(html, defaults=dict(name="foo"))
    assert expected_html == rendered_html, rendered_html


def test_error_class_textarea():
    assert (htmlfill.render('<textarea name="content"></textarea>', errors={'content': 'error'})
            == '<!-- for: content -->\n<span class="error-message">error</span><br />\n<textarea name="content" class="error"></textarea>')


def test_mix_str_and_unicode():
    html = '<input type="text" name="cheese">'
    uhtml = unicode(html)
    cheese = dict(cheese='Käse')
    ucheese = dict(cheese=u'Käse')
    expected = u'<input type="text" name="cheese" value="Käse">'
    rendered = htmlfill.render(html, defaults=cheese, encoding='utf-8')
    assert expected == rendered
    rendered = htmlfill.render(html, defaults=ucheese, encoding='utf-8')
    assert expected == rendered
    rendered = htmlfill.render(uhtml, defaults=cheese, encoding='utf-8')
    assert expected == rendered
    rendered = htmlfill.render(uhtml, defaults=ucheese, encoding='utf-8')
    assert expected == rendered
