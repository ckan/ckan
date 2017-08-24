/*globals describe beforeEach afterEach it assert sinon ckan jQuery */
describe('ckan.module.BasicFormModule()', function () {
  var BasicFormModule = ckan.module.registry['basic-form'];

  beforeEach(function () {
    sinon.stub(jQuery.fn, 'incompleteFormWarning');

    this.el = document.createElement('form');
    this.el.innerHTML = '<button name="save" type="submit">Save</button>'
    this.sandbox = ckan.sandbox();
    this.sandbox.body = this.fixture;
    this.sandbox.body.append(this.el)
    this.module = new BasicFormModule(this.el, {}, this.sandbox);
  });

  afterEach(function () {
    this.module.teardown();
    jQuery.fn.incompleteFormWarning.restore();
  });

  describe('.initialize()', function () {
    it('should attach the jQuery.fn.incompleteFormWarning() to the form', function () {
      this.module.initialize();
      assert.called(jQuery.fn.incompleteFormWarning);
    });

    it('should disable the submit button on form submit', function(done) {
      this.module.initialize();
      this.module._onSubmit();

      setTimeout(function() {
        var buttonAttrDisabled = this.el.querySelector('button').getAttribute('disabled');

        assert.ok(buttonAttrDisabled === 'disabled')
        done();
      }.bind(this), 0);
    });
  });
});
