describe('jQuery.proxyAll(obj, args...)', function () {
  before(function () {
    cy.visit('/');
  });

  beforeEach(function () {
    cy.window().then(win => {
      this.proxy = cy.stub(win.jQuery, 'proxy').returns(function proxied() {
      });
      this.target = {
        prop1: '',
        method1: function method1() {
        },
        method2: function method2() {
        },
        method3: function method3() {
        }
      };

      this.cloned = win.jQuery.extend({}, this.target);
    });
  });

  it('should bind the methods provided to the object', function () {
    cy.window().then(win => {
      win.jQuery.proxyAll(this.target, 'method1', 'method2');

      expect(this.proxy).to.be.called;

      expect(this.proxy).to.be.calledWith(this.cloned.method1, this.target);
      expect(this.proxy).to.be.calledWith(this.cloned.method2, this.target);
      expect(this.proxy).to.not.be.calledWith(this.cloned.method3, this.target);
    });
  });

  // Can be re-enabled when cypress-io/cypress#6382 is resolved
  it.skip('should allow regular expressions to be provided', function () {
    cy.window().then(win => {
      win.jQuery.proxyAll(this.target, /method[1-2]/);

      expect(this.proxy).to.be.called;

      expect(this.proxy).to.be.calledWith(this.cloned.method1, this.target);
      expect(this.proxy).to.be.calledWith(this.cloned.method2, this.target);
      expect(this.proxy).to.not.be.calledWith(this.cloned.method3, this.target);
    });
  });

  it('should skip properties that are not functions', function () {
    cy.window().then(win => {
      win.jQuery.proxyAll(this.target, 'prop1');
      expect(this.proxy).to.not.be.called;
    })
  });

  it('should not bind function more than once', function () {
    cy.window().then(win => {
      win.jQuery.proxyAll(this.target, 'method1');
      win.jQuery.proxyAll(this.target, 'method1');

      expect(this.proxy).to.be.calledOnce;
    });
  });

  it('should not bind function more than once if the method name is passed twice', function () {
    cy.window().then(win => {
      win.jQuery.proxyAll(this.target, 'method1', 'method1');

      expect(this.proxy).to.calledOnce;
    });
  });

  it('should return the first argument', function () {
    cy.window().then(win => {
      assert.equal(win.jQuery.proxyAll(this.target), this.target);
    });
  });
});
