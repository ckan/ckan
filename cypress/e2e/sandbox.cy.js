describe('ckan.sandbox()', {testIsolation: false}, function () {
  before(() => {
    cy.visit('/');
  });

  it('should create an instance of Sandbox', function () {
    cy.window().then(win => {
      let target = cy.stub(win.ckan.sandbox, 'Sandbox');
      win.ckan.sandbox();
      expect(target).to.be.called;
    })
  });

  it('should pass in sandbox.callbacks', function () {
    cy.window().then(win => {
      let target = cy.stub(win.ckan.sandbox, 'Sandbox');
      win.ckan.sandbox();
      expect(target).to.be.calledWith(win.ckan.sandbox.callbacks);
    })
  });

  describe('Sandbox()', {testIsolation: false}, function () {
    it('should call each callback provided with itself', function () {
      cy.window().then(win => {
        let callbacks = [cy.spy(), cy.spy(), cy.spy()];
        let target = new win.ckan.sandbox.Sandbox(callbacks);

        win.jQuery.each(callbacks, function () {
          expect(this).to.be.called;
          expect(this).to.be.calledWith(target);
        });
      })
    });

    describe('.ajax()', {testIsolation: false}, function () {
      it('should be an alias for the jQuery.ajax() method', function () {
        cy.window().then(win => {
          let target = new win.ckan.sandbox.Sandbox();
          assert.strictEqual(target.ajax, win.jQuery.ajax);
        })
      });
    });

    describe('.jQuery()', {testIsolation: false}, function () {
      it('should be a reference to jQuery', function () {
        cy.window().then(win => {
          let target = new win.ckan.sandbox.Sandbox();
          assert.ok(target.jQuery === win.jQuery);
        })
      });
    });

    describe('.body', {testIsolation: false}, function () {
      it('should be a jQuery wrapped body object', function () {
        cy.window().then(win => {
          let target = new win.ckan.sandbox.Sandbox();
          assert.ok(target.body instanceof win.jQuery);
          assert.ok(target.body[0] === win.document.body);
        })
      });
    });

    describe('.location', {testIsolation: false}, function () {
      it('should be a reference to window.location', function () {
        cy.window().then(win => {
          let target = new win.ckan.sandbox.Sandbox();
          assert.ok(target.location === win.location);
        })
      });
    });

    describe('.window', {testIsolation: false}, function () {
      it('should be a reference to window', function () {
        cy.window().then(win => {
          let target = new win.ckan.sandbox.Sandbox();
          assert.ok(target.window === win);
        })
      });
    });

    describe('.i18n', {testIsolation: false}, function () {
      it('should be available while being deprecated', function () {
        cy.window().then(win => {
          let target = new win.ckan.sandbox.Sandbox();
          assert.equal(target.i18n, win.ckan.i18n);
        })
      });
    });

    describe('.translate', {testIsolation: false}, function () {
      it('should be available while being deprecated', function () {
        cy.window().then(win => {
          let target = new win.ckan.sandbox.Sandbox();
          assert.equal(target.translate, win.ckan.i18n.translate);
        })
      });
    });
  });

  describe('sandbox.extend()', {testIsolation: false}, function () {
    it('should extend the Sandbox.prototype with properties', function () {
      cy.window().then(win => {
        let method = cy.spy();

        win.ckan.sandbox.extend({method: method});

        assert.equal(win.ckan.sandbox().method, method);
      })
    });
  });

  describe('sandbox.setup()', {testIsolation: false}, function () {
    it('should register a function to be called when the sandbox is initialized', function () {
      cy.window().then(win => {
        let target = cy.spy();

        win.ckan.sandbox.setup(target);
        win.ckan.sandbox();

        expect(target).to.be.called;
      })
    });

    it('should throw an error if a non function is provided', function () {
      cy.window().then(win => {
        assert.throws(function () {
          win.ckan.sandbox.setup('not a function');
        });
      })
    });
  });
});
