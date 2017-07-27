/*globals describe beforeEach afterEach it assert sinon ckan jQuery */
describe('ckan.modules.ImageUploadModule()', function () {
  var ImageUploadModule = ckan.module.registry['image-upload'];

  beforeEach(function () {
    this.el = document.createElement('div');
    this.sandbox = ckan.sandbox();
    this.module = new ImageUploadModule(this.el, {}, this.sandbox);
    this.module.el.html([
      '<div class="control-group"><input name="image_url" /></div>',
      '<input name="image_upload" />',
    ]);
    this.module.initialize();
    this.module.field_name = jQuery('<input>', {type: 'text'})
  });

  afterEach(function () {
    this.module.teardown();
  });

  describe('._onFromWeb()', function () {

    it('should change name when url changed', function () {
      this.module.field_url_input.val('http://example.com/some_image.png');
      this.module._onFromWebBlur();
      assert.equal(this.module.field_name.val(), 'some_image.png');

      this.module.field_url_input.val('http://example.com/undefined_file');
      this.module._onFromWebBlur();
      assert.equal(this.module.field_name.val(), 'undefined_file');
    });

    it('should ignore url changes if name was manualy changed', function () {
      this.module.field_url_input.val('http://example.com/some_image.png');
      this.module._onFromWebBlur();
      assert.equal(this.module.field_name.val(), 'some_image.png');

      this.module._onModifyName();

      this.module.field_url_input.val('http://example.com/undefined_file');
      this.module._onFromWebBlur();
      assert.equal(this.module.field_name.val(), 'some_image.png');
    });

    it('should ignore url changes if name was filled before', function () {
      this.module._nameIsDirty = true;
      this.module.field_name.val('prefilled');

      this.module.field_url_input.val('http://example.com/some_image.png');
      this.module._onFromWebBlur();
      assert.equal(this.module.field_name.val(), 'prefilled');

      this.module.field_url_input.val('http://example.com/second_some_image.png');
      this.module._onFromWebBlur();
      assert.equal(this.module.field_name.val(), 'prefilled');

      this.module._onModifyName()

      this.module.field_url_input.val('http://example.com/undefined_file');
      this.module._onFromWebBlur();
      assert.equal(this.module.field_name.val(), 'prefilled');
    });
  });

});
