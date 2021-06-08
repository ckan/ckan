/*globals describe beforeEach afterEach it assert sinon ckan jQuery */
describe('jQuery.inherit()', function () {
  before(function(){
    cy.visit('/');
  });

  beforeEach(function () {
    this.MyClass = function MyClass() {};
    this.MyClass.static = function () {};
    this.MyClass.prototype.method = function () {};
  });

  it('should create a subclass of the constructor provided', function () {
    cy.window().then(win => {
      let target = new (win.jQuery.inherit(this.MyClass))();
      assert.isTrue(target instanceof this.MyClass);
    })
  });

  it('should set the childs prototype object', function () {
    cy.window().then(win => {
      let target = new (win.jQuery.inherit(this.MyClass))();
      assert.isFunction(target.method);
    })
  });

  it('should copy over the childs static properties', function () {
    cy.window().then(win => {
      let Target = win.jQuery.inherit(this.MyClass);
      assert.isFunction(Target.static);
    })
  });

  it('should allow instance properties to be overridden', function () {
    cy.window().then(win => {
      function method() {
      }

      let target = new (win.jQuery.inherit(this.MyClass, {method: method}))();
      assert.equal(target.method, method);
    });
  });

  it('should allow static properties to be overridden', function () {
    cy.window().then(win => {
      function staticmethod() {
      }

      let Target = win.jQuery.inherit(this.MyClass, {}, {static: staticmethod});
      assert.equal(Target.static, staticmethod);
    })
  });

  it('should allow a custom constructor to be provided', function () {
    cy.window().then(win => {
      let MyConstructor = cy.spy();
      let Target = win.jQuery.inherit(this.MyClass, {constructor: MyConstructor});

      new Target();

      expect(MyConstructor).to.be.called;
    })
  });
});
