/*globals describe beforeEach afterEach it assert sinon ckan jQuery */
describe('ckan.modules.ResourceFormModule()', function () {
  var ResourceFormModule = ckan.module.registry['resource-form'];

  beforeEach(function () {
    this.el = document.createElement('form');
    this.sandbox = ckan.sandbox();
    this.module = new ResourceFormModule(this.el, {}, this.sandbox);
  });

  afterEach(function () {
    this.module.teardown();
  });

  describe('.initialize()', function () {
    it('should subscribe to the "resource:uploaded" event', function () {
      var target = sinon.stub(this.sandbox, 'subscribe');

      this.module.initialize();

      assert.called(target);
      assert.calledWith(target, 'resource:uploaded', this.module._onResourceUploaded);

      target.restore();
    });
  });

  describe('.teardown()', function () {
    it('should unsubscribe from the "resource:uploaded" event', function () {
      var target = sinon.stub(this.sandbox, 'unsubscribe');

      this.module.teardown();

      assert.called(target);
      assert.calledWith(target, 'resource:uploaded', this.module._onResourceUploaded);

      target.restore(); 
    });
  });

  describe('._onResourceUploaded()', function () {
    beforeEach(function () {
      this.module.el.html([
        '<input type="text" name="text" />',
        '<input type="checkbox" name="checkbox" value="check" />',
        '<input type="radio" name="radio" value="radio1" />',
        '<input type="radio" name="radio" value="radio2" />',
        '<input type="hidden" name="hidden" />',
        '<select name="select">',
        '<option value="option1" />',
        '<option value="option2" />',
        '</select>'
      ].join(''));

      this.resource = {
        text: 'text',
        checkbox: "check",
        radio: "radio2",
        hidden: "hidden",
        select: "option1"
      };
    });

    it('should set the values on appropriate fields', function () {
      var res = this.resource;

      this.module._onResourceUploaded(res);

      jQuery.each(this.module.el.serializeArray(), function (idx, field) {
        assert.equal(field.value, res[field.name]);
      });
    });
  });
});
