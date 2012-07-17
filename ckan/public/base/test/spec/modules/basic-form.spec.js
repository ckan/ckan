/*globals describe beforeEach afterEach it assert sinon ckan jQuery */
describe('ckan.module.BasicFormModule()', function () {
  var BasicFormModule = ckan.module.registry['basic-form'];

  beforeEach(function () {
    jQuery.fn.incompleteFormWarning = sinon.spy();

    this.el = document.createElement('button');
    this.sandbox = ckan.sandbox();
    this.sandbox.body = this.fixture;
    this.module = new BasicFormModule(this.el, {}, this.sandbox);
  });

  afterEach(function () {
    this.module.teardown();
  });

  describe('.initialize()', function () {
    it('should attach the jQuery.fn.incompleteFormWarning() to the form', function () {
      this.module.initialize();
      assert.called(jQuery.fn.incompleteFormWarning);
    });
  });
});
