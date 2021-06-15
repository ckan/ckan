describe('ckan.module.CustomFieldsModule()', function () {
   before(() => {
    cy.visit('/');
    cy.window().then(win => {
      cy.wrap(win.ckan.module.registry['custom-fields']).as('CustomFieldsModule');
      win.jQuery('<div id="fixture">').appendTo(win.document.body)
      cy.loadFixture('custom_fields.html').then((template) => {
        cy.wrap(template).as('template');
      });
    })

  });

  beforeEach(function () {
    cy.window().then(win => {
      win.jQuery('#fixture').html(this.template);
      this.el = win.jQuery('#fixture').find('[data-module]');
      this.sandbox = win.ckan.sandbox();
      this.sandbox.body = win.jQuery('#fixture');
      this.module = new this.CustomFieldsModule(this.el, {}, this.sandbox);
    });
  });

  afterEach(function () {
    this.module.teardown();
  });

  describe('.initialize()', function () {
    it('should bind all functions beginning with _on to the module scope', function () {
      cy.window().then(win => {
        let target = cy.stub(win.jQuery, 'proxyAll');

        this.module.initialize();

        expect(target).to.be.called;
        expect(target).to.be.calledWith(this.module, /_on/);

        target.restore();
      });
    });

    it('should listen for changes to the last "key" input', function () {
      let target = cy.stub(this.module, '_onChange');

      this.module.initialize();
      this.module.$('input[name*=key]').change();

      expect(target).to.be.calledOnce;
    });

    it('should listen for changes to all checkboxes', function () {
      let target = cy.stub(this.module, '_onRemove');

      this.module.initialize();
      this.module.$(':checkbox').trigger('change');

      expect(target).to.be.calledOnce;
    });
  });

  describe('.newField(element)', function () {
    it('should append a new field to the element', function () {
      cy.window().then(win => {
        let element = win.document.createElement('div');
        cy.stub(this.module, 'cloneField').returns(element);

        this.module.newField();

        assert.ok(win.jQuery.contains(this.module.el[0], element));
      });
    });
  });

  describe('.cloneField(element)', function () {
    it('should clone the provided field', function () {
      cy.window().then(win => {
        let element = win.document.createElement('div');
        let init = cy.spy(win.jQuery.fn, 'init');
        let clone = cy.spy(win.jQuery.fn, 'clone',);

        this.module.cloneField(element);

        expect(init).to.be.called;
        expect(init).to.be.calledWith(element);
        expect(clone).to.be.called;

        init.restore();
        clone.restore();
      });
    });

    it('should return the cloned element', function () {
      cy.window().then(win => {
        let element = win.document.createElement('div');
        let cloned = win.document.createElement('div');
        let init = cy.spy(win.jQuery.fn, 'init');
        let clone = cy.stub(win.jQuery.fn, 'clone').returns(win.jQuery(cloned));

        assert.ok(this.module.cloneField(element)[0] === cloned);

        init.restore();
        clone.restore();
      });
    });
  });

  describe('.resetField(element)', function () {
    beforeEach(function () {
      cy.window().then(win => {
        cy.wrap(win.jQuery('<div><label for="field-1">Field 1</label><input name="field-1" value="value" /></div>')).as('field');
      })
    });

    it('should empty all input values', function () {
      let target = this.module.resetField(this.field);
      assert.equal(target.find(':input').val(), '');
    });

    it('should increment any integers in the input names by one', function () {
      let target = this.module.resetField(this.field);
      assert.equal(target.find(':input').attr('name'), 'field-2');
    });

    it('should increment any numbers in the label text by one', function () {
      let target = this.module.resetField(this.field);
      assert.equal(target.find('label').text(), 'Field 2');
    });

    it('should increment any numbers in the label for by one', function () {
      let target = this.module.resetField(this.field);
      assert.equal(target.find('label').attr('for'), 'field-2');
    });
  });

  describe('.disableField(field, disable)', function () {
    beforeEach(function () {
      this.target = this.module.$('.control-custom:first');
    });

    it('should add a .disabled class to the element', function () {
      this.module.disableField(this.target);
      assert.isTrue(this.target.hasClass('disabled'));
    });

    it('should remove a .disabled class to the element if disable is false', function () {
      this.target.addClass('disabled');

      this.module.disableField(this.target, false);
      assert.isFalse(this.target.hasClass('disabled'));
    });

  });

  describe('._onChange(event)', function () {
    it('should call .newField() with the custom control', function () {
      cy.window().then(win => {
        let target = cy.stub(this.module, 'newField');
        let field  = this.module.$('[name*=key]:last').val('test');

        this.module._onChange(win.jQuery.Event('change', {target: field[0]}));

        expect(target).to.be.called;
      })
    });

    it('should not call .newField() if the target field is empty', function () {
      cy.window().then(win => {
        let target = cy.stub(this.module, 'newField');
        let field  = this.module.$('[name*=key]:last').val('');

        this.module._onChange(win.jQuery.Event('change', {target: field[0]}));

        expect(target).to.not.be.called;
      })
    });
  });

  describe('._onRemove(event)', function () {
    it('should call .disableField() with the custom control', function () {
      cy.window().then(win => {
        let target = cy.stub(this.module, 'disableField');
        this.module._onRemove(win.jQuery.Event('change', {target: this.module.$(':checkbox')[0]}));

        expect(target).to.be.called;
      })
    });
  });
});
