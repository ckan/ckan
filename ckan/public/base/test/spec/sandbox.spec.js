/*globals describe beforeEach afterEach it assert sinon ckan jQuery */
describe('ckan.sandbox()', function () {
  describe('Sandbox()', function () {
    var Sandbox = ckan.sandbox.Sandbox;

    beforeEach(function () {
      this.el = document.createElement('div');
      this.options = {prop1: 1, prop2: 2, prop3: 3};
    });

    describe('.options', function () {
      it('should be a reference to the options passed into Sandbox');
    });

    describe('.el', function () {
      it('should the element passed into Sandbox wrapped in jQuery');
    });

    describe('.$()', function () {
      it('should find elements within the .el property');
    });

    describe('.ajax()', function () {
      it('should be an alias for the jQuery.ajax() method', function () {
        var target = new Sandbox(this.el, this.options);
        assert.strictEqual(target.ajax, jQuery.ajax);
      });
    });
  });
});
