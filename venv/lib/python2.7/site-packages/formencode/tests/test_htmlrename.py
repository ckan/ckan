from formencode.htmlrename import rename, add_prefix


def test_rename():
    assert (rename('<input type="text" name="a_name">', lambda name: name.upper())
            == '<input type="text" name="A_NAME">')
    assert (add_prefix('<input type="text" name="a_name"><input type="text" name="">', 'test', dotted=True)
            == '<input type="text" name="test.a_name"><input type="text" name="test">')
    assert (add_prefix('text<textarea name="a_name">value</textarea>text2', 'prefix.')
            == 'text<textarea name="prefix.a_name">value</textarea>text2')
    assert (add_prefix('<textarea name="" rows=2 style="width: 100%" id="field-0"></textarea>',
                       'street', dotted=True)
            == '<textarea name="street" rows="2" style="width: 100%" id="field-0"></textarea>')
