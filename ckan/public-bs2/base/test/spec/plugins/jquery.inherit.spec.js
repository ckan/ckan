/*globals describe beforeEach afterEach it assert sinon ckan jQuery */
describe('jQuery.inherit()', function () {
  beforeEach(function () {
    this.MyClass = function MyClass() {};
    this.MyClass.static = function () {};
    this.MyClass.prototype.method = function () {};
  });

  it('should create a subclass of the constructor provided', function () {
    var target = new (jQuery.inherit(this.MyClass))();
    assert.isTrue(target instanceof this.MyClass);
  });

  it('should set the childs prototype object', function () {
    var target = new (jQuery.inherit(this.MyClass))();
    assert.isFunction(target.method);
  });

  it('should copy over the childs static properties', function () {
    var Target = jQuery.inherit(this.MyClass);
    assert.isFunction(Target.static);
  });

  it('should allow instance properties to be overridden', function () {
    function method() {}

    var target = new (jQuery.inherit(this.MyClass, {method: method}))();
    assert.equal(target.method, method);
  });

  it('should allow static properties to be overridden', function () {
    function staticmethod() {}

    var Target = jQuery.inherit(this.MyClass, {}, {static: staticmethod});
    assert.equal(Target.static, staticmethod);
  });

  it('should allow a custom constructor to be provided', function () {
    var MyConstructor = sinon.spy();
    var Target = jQuery.inherit(this.MyClass, {constructor: MyConstructor});

    new Target();

    sinon.assert.called(MyConstructor);
  });
});
