describe('ckan.i18n', function () {
  describe('ckan.i18n.translate', function () {
    it('should work while being deprecated', function () {
      var x = ckan.i18n.translate('foo');
      assert.deepProperty(x, 'fetch');
      assert.equal(x.fetch(), 'FOO');
      assert.deepProperty(x, 'ifPlural');
    });
  });

  describe('._(string, [values])', function () {
    it('should return the translated string', function () {
      assert.equal(ckan.i18n._('foo'), 'FOO');
    });

    it('should return the key when no translation exists', function () {
      assert.equal(ckan.i18n._('no translation'), 'no translation');
    });

    it('should fill in placeholders', function () {
      assert.equal(
        ckan.i18n._('hello %(name)s!', {name: 'Julia'}),
        'HELLO Julia!'
      );
    });

    it('should fill in placeholders when no translation exists', function () {
      assert.equal(
        ckan.i18n._('no %(attr)s translation', {attr: 'good'}),
        'no good translation'
      );
    });
  });

  describe('.ngettext(singular, plural, number, [values])', function () {
    var ngettext = ckan.i18n.ngettext;

    it('should return the translated strings', function () {
      assert.equal(ngettext('bar', 'bars', 1), 'BAR');
      assert.equal(ngettext('bar', 'bars', 0), 'BARS');
      assert.equal(ngettext('bar', 'bars', 2), 'BARS');
    });

    it('should return the key when no translation exists', function () {
      assert.equal(
        ngettext('no translation', 'no translations', 1),
        'no translation'
      );
      assert.equal(
        ngettext('no translation', 'no translations', 0),
        'no translations'
      );
      assert.equal(
        ngettext('no translation', 'no translations', 2),
        'no translations'
      );
    });

    it('should fill in placeholders', function () {
      assert.equal(
        ngettext('%(color)s shirt', '%(color)s shirts', 1, {color: 'RED'}),
        'RED SHIRT'
      );
      assert.equal(
        ngettext('%(color)s shirt', '%(color)s shirts', 0, {color: 'RED'}),
        'RED SHIRTS'
      );
      assert.equal(
        ngettext('%(color)s shirt', '%(color)s shirts', 2, {color: 'RED'}),
        'RED SHIRTS'
      );
    });

    it('should fill in placeholders when no translation exists', function () {
      assert.equal(
        ngettext('no %(attr)s translation', 'no %(attr)s translations',
                 1, {attr: 'good'}),
        'no good translation'
      );
      assert.equal(
        ngettext('no %(attr)s translation', 'no %(attr)s translations',
                 0, {attr: 'good'}),
        'no good translations'
      );
      assert.equal(
        ngettext('no %(attr)s translation', 'no %(attr)s translations',
                 2, {attr: 'good'}),
        'no good translations'
      );
    });

    it('should provide a magic `num` placeholder', function () {
      assert.equal(ngettext('%(num)d item', '%(num)d items', 1), '1 ITEM');
      assert.equal(ngettext('%(num)d item', '%(num)d items', 0), '0 ITEMS');
      assert.equal(ngettext('%(num)d item', '%(num)d items', 2), '2 ITEMS');
    });

    it('should provide `num` when no translation exists', function () {
      assert.equal(
        ngettext('%(num)d missing translation',
                 '%(num)d missing translations', 1),
        '1 missing translation'
      );
      assert.equal(
        ngettext('%(num)d missing translation',
                 '%(num)d missing translations', 0),
        '0 missing translations'
      );
      assert.equal(
        ngettext('%(num)d missing translation',
                 '%(num)d missing translations', 2),
        '2 missing translations'
      );
    });
  });
});
