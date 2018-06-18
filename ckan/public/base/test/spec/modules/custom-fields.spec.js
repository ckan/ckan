/*globals describe before beforeEach afterEach it assert sinon ckan jQuery */
describe('ckan.module.CustomFieldsModule()', function () {
  var CustomFieldsModule = ckan.module.registry['custom-fields'];

  before(function (done) {
    this.loadFixture('custom_fields.html', function (template) {
      this.template = template;
      done();
    });
  });

  beforeEach(function () {
    this.fixture.html(this.template);
    this.el = this.fixture.find('[data-module]');
    this.sandbox = ckan.sandbox();
    this.sandbox.body = this.fixture;
    this.module = new CustomFieldsModule(this.el, {}, this.sandbox);
  });

  afterEach(function () {
    this.module.teardown();
  });

  describe('.initialize()', function () {
    it('should bind all functions beginning with _on to the module scope', function () {
      var target = sinon.stub(jQuery, 'proxyAll');

      this.module.initialize();

      assert.called(target);
      assert.calledWith(target, this.module, /_on/);

      target.restore();
    });

    it('should listen for changes to the last "key" input', function () {
      var target = sinon.stub(this.module, '_onChange');

      this.module.initialize();
      this.module.$('input[name*=key]').change();

      assert.calledOnce(target);
    });

    it('should listen for changes to all checkboxes', function () {
      var target = sinon.stub(this.module, '_onRemove');

      this.module.initialize();
      this.module.$(':checkbox').trigger('change');

      assert.calledOnce(target);
    });
  });

  describe('.newField(element)', function () {
    it('should append a new field to the element', function () {
      var element = document.createElement('div');
      sinon.stub(this.module, 'cloneField').returns(element);

      this.module.newField();

      assert.ok(jQuery.contains(this.module.el[0], element));
    });
  });

  describe('.cloneField(element)', function () {
    it('should clone the provided field', function () {
      var element = document.createElement('div');
      var init  = sinon.stub(jQuery.fn, 'init', jQuery.fn.init);
      var clone = sinon.stub(jQuery.fn, 'clone', jQuery.fn.clone);

      this.module.cloneField(element);

      assert.called(init);
      assert.calledWith(init, element);
      assert.called(clone);

      init.restore();
      clone.restore();
    });

    it('should return the cloned element', function () {
      var element = document.createElement('div');
      var cloned  = document.createElement('div');
      var init  = sinon.stub(jQuery.fn, 'init', jQuery.fn.init);
      var clone = sinon.stub(jQuery.fn, 'clone').returns(jQuery(cloned));

      assert.ok(this.module.cloneField(element)[0] === cloned);

      init.restore();
      clone.restore();
    });
  });

  describe('.resetField(element)', function () {
    beforeEach(function () {
      this.field = jQuery('<div><label for="field-1">Field 1</label><input name="field-1" value="value" /></div>');
    });

    it('should empty all input values', function () {
      var target = this.module.resetField(this.field);
      assert.equal(target.find(':input').val(), '');
    });

    it('should increment any integers in the input names by one', function () {
      var target = this.module.resetField(this.field);
      assert.equal(target.find(':input').attr('name'), 'field-2');
    });

    it('should increment any numbers in the label text by one', function () {
      var target = this.module.resetField(this.field);
      assert.equal(target.find('label').text(), 'Field 2');
    });

    it('should increment any numbers in the label for by one', function () {
      var target = this.module.resetField(this.field);
      assert.equal(target.find('label').attr('for'), 'field-2');
    });
  });

  describe('.disableField(field, disable)', function () {
    beforeEach(function () {
      this.target = this.module.$('.control-custom:first');
    });

    it('should add a .disable class to the element', function () {
      this.module.disableField(this.target);
      assert.isTrue(this.target.hasClass('disabled'));
    });

    it('should remove a .disable class to the element if disable is false', function () {
      this.target.addClass('disable');

      this.module.disableField(this.target, false);
      assert.isFalse(this.target.hasClass('disabled'));
    });

  });

  describe('._onChange(event)', function () {
    it('should call .newField() with the custom control', function () {
      var target = sinon.stub(this.module, 'newField');
      var field  = this.module.$('[name*=key]:last').val('test');

      this.module._onChange(jQuery.Event('change', {target: field[0]}));

      assert.called(target);
    });

    it('should not call .newField() if the target field is empty', function () {
      var target = sinon.stub(this.module, 'newField');
      var field  = this.module.$('[name*=key]:last').val('');

      this.module._onChange(jQuery.Event('change', {target: field[0]}));

      assert.notCalled(target);
    });
  });

  describe('._onRemove(event)', function () {
    it('should call .disableField() with the custom control', function () {
      var target = sinon.stub(this.module, 'disableField');
      this.module._onRemove(jQuery.Event('change', {target: this.module.$(':checkbox')[0]}));

      assert.called(target);
    });
  });
});
