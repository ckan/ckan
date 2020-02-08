describe('ckan.i18n', function () {
  before(() => {
    cy.visit('/')
    cy.window().then(win => {
      win.ckan.i18n.load({
        '': {
          "domain": "ckan",
          "lang": "en",
          "plural_forms": "nplurals=2; plural=(n != 1);"
        },
        'foo': [null, 'FOO'],
        'hello %(name)s!': [null, 'HELLO %(name)s!'],
        'bar': ['bars', 'BAR', 'BARS'],
        '%(color)s shirt': [
          '%(color)s shirts',
          '%(color)s SHIRT',
          '%(color)s SHIRTS'
        ],
        '%(num)d item': ['%(num)d items', '%(num)d ITEM', '%(num)d ITEMS']
      });

    })
  });

  describe('ckan.i18n.translate', function () {
    it('should work while being deprecated', function () {
      cy.window().then(win => {
        let x = win.ckan.i18n.translate('foo');
        expect(x).to.have.deep.property( 'fetch');
        assert.equal(x.fetch(), 'FOO');
        expect(x).to.have.deep.property( 'ifPlural');
      })
    });
  });

  describe('._(string, [values])', function () {
    it('should return the translated string', function () {
      cy.window().then(win => {
        assert.equal(win.ckan.i18n._('foo'), 'FOO');
      })
    });

    it('should return the key when no translation exists', function () {
      cy.window().then(win => {
        assert.equal(win.ckan.i18n._('no translation'), 'no translation');
      })
    });

    it('should fill in placeholders', function () {
      cy.window().then(win => {
        assert.equal(
          win.ckan.i18n._('hello %(name)s!', {name: 'Julia'}),
          'HELLO Julia!'
        );
      })
    });

    it('should fill in placeholders when no translation exists', function () {
      cy.window().then(win => {
        assert.equal(
          win.ckan.i18n._('no %(attr)s translation', {attr: 'good'}),
          'no good translation'
        );
      })
    });
  });

  describe('.ngettext(singular, plural, number, [values])', function () {
    beforeEach(() => {
      cy.window().then(win => {
        cy.wrap(win.ckan.i18n.ngettext).as('ngettext');
      })
    })

    it('should return the translated strings', function () {
      assert.equal(this.ngettext('bar', 'bars', 1), 'BAR');
      assert.equal(this.ngettext('bar', 'bars', 0), 'BARS');
      assert.equal(this.ngettext('bar', 'bars', 2), 'BARS');
    });

    it('should return the key when no translation exists', function () {
      assert.equal(
        this.ngettext('no translation', 'no translations', 1),
        'no translation'
      );
      assert.equal(
        this.ngettext('no translation', 'no translations', 0),
        'no translations'
      );
      assert.equal(
        this.ngettext('no translation', 'no translations', 2),
        'no translations'
      );
    });

    it('should fill in placeholders', function () {
      assert.equal(
        this.ngettext('%(color)s shirt', '%(color)s shirts', 1, {color: 'RED'}),
        'RED SHIRT'
      );
      assert.equal(
        this.ngettext('%(color)s shirt', '%(color)s shirts', 0, {color: 'RED'}),
        'RED SHIRTS'
      );
      assert.equal(
        this.ngettext('%(color)s shirt', '%(color)s shirts', 2, {color: 'RED'}),
        'RED SHIRTS'
      );
    });

    it('should fill in placeholders when no translation exists', function () {
      assert.equal(
        this.ngettext('no %(attr)s translation', 'no %(attr)s translations',
                 1, {attr: 'good'}),
        'no good translation'
      );
      assert.equal(
        this.ngettext('no %(attr)s translation', 'no %(attr)s translations',
                 0, {attr: 'good'}),
        'no good translations'
      );
      assert.equal(
        this.ngettext('no %(attr)s translation', 'no %(attr)s translations',
                 2, {attr: 'good'}),
        'no good translations'
      );
    });

    it('should provide a magic `num` placeholder', function () {
      assert.equal(this.ngettext('%(num)d item', '%(num)d items', 1), '1 ITEM');
      assert.equal(this.ngettext('%(num)d item', '%(num)d items', 0), '0 ITEMS');
      assert.equal(this.ngettext('%(num)d item', '%(num)d items', 2), '2 ITEMS');
    });

    it('should provide `num` when no translation exists', function () {
      assert.equal(
        this.ngettext('%(num)d missing translation',
                 '%(num)d missing translations', 1),
        '1 missing translation'
      );
      assert.equal(
        this.ngettext('%(num)d missing translation',
                 '%(num)d missing translations', 0),
        '0 missing translations'
      );
      assert.equal(
        this.ngettext('%(num)d missing translation',
                 '%(num)d missing translations', 2),
        '2 missing translations'
      );
    });
  });
});
