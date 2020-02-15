/*globals describe beforeEach afterEach it assert sinon ckan jQuery */
describe('ckan.module(id, properties|callback)', function () {
  before(() => {
    cy.visit('/');
    cy.window().then(win => {
      win.ckan.i18n.load({
        '': {
          "domain": "ckan",
          "lang": "en",
          "plural_forms": "nplurals=2; plural=(n != 1);"
        },
        'foo': [null, 'FOO'],
        'hello %(name)s!': [null, 'HELLO %(name)s!'],
        'bar': ['bars', 'BAR', 'BARS'],
        '%(color)s shirt': [
          '%(color)s shirts',
          '%(color)s SHIRT',
          '%(color)s SHIRTS'
        ],
        '%(num)d item': ['%(num)d items', '%(num)d ITEM', '%(num)d ITEMS']
      });

    })
  });

  beforeEach(function () {
    cy.window().then(win => {
      win.ckan.module.registry = {};
      win.ckan.module.instances = {};
      cy.wrap({}).as('factory');
    })
  });

  it('should add a new item to the registry', function () {
    cy.window().then(win => {
      win.ckan.module('test', this.factory);

      assert.instanceOf(new win.ckan.module.registry.test(), win.ckan.module.BaseModule);
    })
  });

  it('should allow a function to be provided', function () {
    let target = cy.stub().returns({});
    cy.window().then(win => {
      win.ckan.module('test', target);

      expect(target).to.be.called;
    })
  });

  it('should pass jQuery, i18n.translate() and i18n into the function', function () {
    // Note: This behavior is deprecated but kept for backwards-compatibility
    let target = cy.stub().returns({});
    cy.window().then(win => {
      win.ckan.module('test', target);

      expect(target).to.be.calledWith(win.jQuery, win.ckan.i18n.translate, win.ckan.i18n);
    })
  });

  it('should throw an exception if the module is already defined', function () {
    cy.window().then(win => {
      win.ckan.module('name', this.factory);
      assert.throws(function () {
        win.ckan.module('name', this.factory);
      });
    })
  });

  it('should return the ckan object', function () {
    cy.window().then(win => {
      assert.equal(win.ckan.module('name', this.factory), win.ckan);
    })
  });

  describe('.initialize()', function () {
    before(() => {
      cy.window().then(win => {
        win.jQuery('<div id="fixture">').appendTo(win.document.body)
      })
    })
    beforeEach(function () {
      cy.window().then(win => {
        let element1 = win.jQuery('<div data-module="test1">').appendTo(win.jQuery('#fixture'));
        cy.wrap(element1).as('element1');
        let element2 = win.jQuery('<div data-module="test1">').appendTo(win.jQuery('#fixture'));
        cy.wrap(element2).as('element2');

        let element3 = win.jQuery('<div data-module="test2">').appendTo(win.jQuery('#fixture'));
        cy.wrap(element3).as('element3');

        this.test1 = cy.spy();

        // Add test1 to the registry.
        win.ckan.module.registry = {
          test1: this.test1
        };

        cy.wrap(cy.stub(win.ckan.module, 'createInstance')).as('target');
      })
    });

    afterEach(() => {
      cy.window().then(win => {
        win.jQuery('#fixture').empty();
      })
    })

    it('should find all elements with the "data-module" attribute', function () {
      cy.window().then(win => {
        win.ckan.module.initialize();
        expect(this.target).to.be.called;
      })
    });

    it('should skip modules that are not functions', function () {
      cy.window().then(win => {
        win.ckan.module.initialize();
        expect(this.target).to.be.calledTwice;
      })
    });

    it('should call module.createInstance() with the element and factory', function () {
      cy.window().then(win => {
        win.ckan.module.initialize();
        expect(this.target).to.be.calledWith(this.test1, this.element1[0]);
        expect(this.target).to.be.calledWith(this.test1, this.element2[0]);
      })
    });

    it('should return the module object', function () {
      cy.window().then(win => {
        assert.equal(win.ckan.module.initialize(), win.ckan.module);
      })
    });

    it('should initialize more than one module separated by a space', function () {
      cy.window().then(win => {
        win.jQuery('#fixture').empty();
        this.element4 = win.jQuery('<div data-module="test1 test2">').appendTo(win.jQuery('#fixture'));
        this.test2 = win.ckan.module.registry.test2 = cy.spy();

        win.ckan.module.initialize();

        expect(this.target).to.be.calledWith(this.test1, this.element4[0]);
        expect(this.target).to.be.calledWith(this.test2, this.element4[0]);
      })
    });

    it('should defer all published events untill all modules have loaded', function () {
      cy.window().then(win => {
        let pubsub = win.ckan.pubsub;
        let callbacks = [];

        // Ensure each module is loaded. Three in total.
        win.ckan.module.registry = {
          test1: function () {
          },
          test2: function () {
          }
        };

        // Call a function to publish and subscribe to an event on each instance.
        this.target.restore();
        this.target = cy.stub(win.ckan.module, 'createInstance', function () {
          let callback = cy.spy();

          pubsub.publish('test');
          pubsub.subscribe('test', callback);

          callbacks.push(callback);
        });

        win.ckan.module.initialize();

        // Ensure that all subscriptions received all messages.
        assert.ok(callbacks.length, 'no callbacks were created');
        win.jQuery.each(callbacks, function () {
          expect(this).to.be.calledThrice;
        });
      })
    });
  });

  describe('.createInstance(Module, element)', function () {
    beforeEach(function () {
      cy.window().then(win => {
        this.element = win.document.createElement('div');
        this.factory = win.ckan.module.BaseModule;
        this.factory.options = this.defaults = {test1: 'a', test2: 'b', test3: 'c'};

        this.sandbox = {
          i18n: {
            translate: cy.spy()
          }
        };
        cy.stub(win.ckan, 'sandbox').returns(this.sandbox);

        this.extractedOptions = {test1: 1, test2: 2};
        cy.stub(win.ckan.module, 'extractOptions').returns(this.extractedOptions);
      })
    });

    it('should extract the options from the element', function () {
      cy.window().then(win => {
        win.ckan.module.createInstance(this.factory, this.element);

        expect(win.ckan.module.extractOptions).to.be.called;
        expect(win.ckan.module.extractOptions).to.be.calledWith(this.element);
      })
    });

    it('should not modify the defaults object', function () {
      cy.window().then(win => {
        let clone = win.jQuery.extend({}, this.defaults);
        win.ckan.module.createInstance(this.factory, this.element);

        assert.deepEqual(this.defaults, clone);
      })
    });

    it('should create a sandbox object', function () {
      cy.window().then(win => {
        win.ckan.module.createInstance(this.factory, this.element);

        expect(win.ckan.sandbox).to.be.called;
        expect(win.ckan.sandbox).to.be.calledWith(this.element);
      })
    });

    it('should initialize the module factory with the sandbox, options and translate function', function () {
      let target = cy.spy();
      cy.window().then(win => {
        win.ckan.module.createInstance(target, this.element);

        expect(target).to.be.called;
        expect(target).to.be.calledWith(this.element, this.extractedOptions, this.sandbox);
      })
    });

    it('should initialize the module as a constructor', function () {
      let target = cy.spy();
      cy.window().then(win => {
        win.ckan.module.createInstance(target, this.element);

        expect(target).to.be.calledWithNew;
      })
    });

    it('should call the .initialize() method if one exists', function () {
      let init = cy.spy();
      let target = cy.stub().returns({
        initialize: init
      });
      cy.window().then(win => {
        win.ckan.module.createInstance(target, this.element);

        expect(init).to.be.called;
      })
    });

    it('should push the new instance into an array under ckan.module.instances', function () {
      let target = function MyModule() { return {'mock': 'instance'}; };
      target.namespace = 'test';

      cy.window().then(win => {
        win.ckan.module.createInstance(target, this.element);

        assert.deepEqual(win.ckan.module.instances.test, [{'mock': 'instance'}]);
      })
    });

    it('should push further instances into the existing array under ckan.module.instances', function () {
      let target = function MyModule() { return {'mock': 'instance3'}; };
      target.namespace = 'test';

      cy.window().then(win => {
        win.ckan.module.instances.test = [{'mock': 'instance1'}, {'mock': 'instance2'}];
        win.ckan.module.createInstance(target, this.element);

        assert.deepEqual(win.ckan.module.instances.test, [
          {'mock': 'instance1'}, {'mock': 'instance2'}, {'mock': 'instance3'}
        ]);
      })
    });

  });

  describe('.extractOptions(element)', function () {
    it('should extract the data keys from the element', function () {
      cy.window().then(win => {
        let element = win.jQuery('<div>', {
          'data-not-module': 'skip',
          'data-module': 'skip',
          'data-module-a': 'capture',
          'data-module-b': 'capture',
          'data-module-c': 'capture'
        })[0];

        let target = win.ckan.module.extractOptions(element);

        assert.deepEqual(target, {a: 'capture', b: 'capture', c: 'capture'});
      });
    });

    it('should convert JSON contents of keys into JS primitives', function () {
      cy.window().then(win => {
        let element = win.jQuery('<div>', {
          'data-module-null': 'null',
          'data-module-int': '100',
          'data-module-arr': '[1, 2, 3]',
          'data-module-obj': '{"a": 1, "b":2, "c": 3}',
          'data-module-str': 'hello'
        })[0];

        let target = win.ckan.module.extractOptions(element);

        assert.deepEqual(target, {
          'null': null,
          'int': 100,
          'arr': [1, 2, 3],
          'obj': {"a": 1, "b": 2, "c": 3},
          'str': 'hello'
        });
      });
    });

    it('should simply use strings for content that it cannot parse as JSON', function () {
      cy.window().then(win => {
        let element = win.jQuery('<div>', {
          'data-module-url': 'http://example.com/path/to.html',
          'data-module-bad': '{oh: 1, no'
        })[0];

        let target = win.ckan.module.extractOptions(element);

        assert.deepEqual(target, {
          'url': 'http://example.com/path/to.html',
          'bad': '{oh: 1, no'
        });
      })
    });

    it('should convert keys with hyphens into camelCase', function () {
      cy.window().then(win => {
        let element = win.jQuery('<div>', {
          'data-module-long-property': 'long',
          'data-module-really-very-long-property': 'longer'
        })[0];

        let target = win.ckan.module.extractOptions(element);

        assert.deepEqual(target, {
          'longProperty': 'long',
          'reallyVeryLongProperty': 'longer'
        });
      });
    });

    it('should set boolean attributes to true', function () {
      cy.window().then(win => {
        let element = win.jQuery('<div>', {
          'data-module-long-property': ''
        })[0];

        let target = win.ckan.module.extractOptions(element);

        assert.deepEqual(target, {'longProperty': true});
      });
    });
  });

  describe('BaseModule(element, options, sandbox)', function () {
    beforeEach(function () {
      cy.window().then(win => {
        this.el = win.jQuery('<div />');
        this.options = {};
        this.sandbox = win.ckan.sandbox();
        this.module = new win.ckan.module.BaseModule(this.el, this.options, this.sandbox);
      })
    });

    it('should assign .el as the element option', function () {
      assert.ok(this.module.el === this.el);
    });

    it('should wrap .el in jQuery if not already wrapped', function () {
      cy.window().then(win => {
        var element = win.document.createElement('div');
        var target = new win.ckan.module.BaseModule(element, this.options, this.sandbox);

        assert.ok(target.el instanceof win.jQuery);
      })
    });

    it('should deep extend the options object', function () {
      cy.window().then(win => {
        // Lazy check :/
        let target = cy.stub(win.jQuery, 'extend');
        new win.ckan.module.BaseModule(this.el, this.options, this.sandbox);

        expect(target).to.be.called;
        expect(target).to.be.calledWith( true, {}, win.ckan.module.BaseModule.prototype.options, this.options);

        target.restore();
      })
    });

    it('should assign the sandbox property', function () {
      assert.equal(this.module.sandbox, this.sandbox);
    });

    describe('.$(selector)', function () {
      it('should find children within the module element', function () {
        cy.window().then(win => {
          this.module.el.append(win.jQuery('<input /><input />'));
          assert.equal(this.module.$('input').length, 2);
        })
      });
    });

    describe('.i18n()', function () {
      // Note: This function is deprecated but kept for backwards-compatibility
      beforeEach(function () {
        this.i18n = {
          first: 'first string',
          second: {fetch: cy.stub().returns('second string')},
          third: cy.stub().returns('third string')
        };

        this.module.options.i18n = this.i18n;
      });

      it('should return the translation string', function () {
        var target = this.module.i18n('first');
        assert.equal(target, 'first string');
      });

      it('should call fetch on the translation string if it exists', function () {
        var target = this.module.i18n('second');
        assert.equal(target, 'second string');
      });

      it('should return just the key if no translation exists', function () {
        var target = this.module.i18n('missing');
        assert.equal(target, 'missing');
      });

      it('should call the translation function if one is provided', function () {
        var target = this.module.i18n('third');
        assert.equal(target, 'third string');
      });

      it('should pass the argments after the key into trans.fetch()', function () {
        var target = this.module.options.i18n.second.fetch;
        this.module.i18n('second', 1, 2, 3);
        expect(target).to.be.called;
        expect(target).to.be.calledWith( 1, 2, 3);
      });

      it('should pass the argments after the key into the translation function', function () {
        var target = this.module.options.i18n.third;
        this.module.i18n('third', 1, 2, 3);
        expect(target).to.be.called;
        expect(target).to.be.calledWith( 1, 2, 3);
      });
    });

    describe('._()', function () {
      it('should be a shortcut for ckan.i18n._', function () {
        /*
         * In a module, this._ is a shortcut for ckan.i18n._,
         * but it's not a direct reference.
         */
        assert.equal(this.module._('foo'), 'FOO');

      });
    });

    describe('.ngettext()', function () {
      it('should be a shortcut for ckan.i18n.ngettext', function () {
        /*
         * In a module, this.ngettext is a shortcut for ckan.i18n.ngettext,
         * but it's not a direct reference.
         */
        assert.equal(this.module.ngettext('bar', 'bars', 1), 'BAR');
        assert.equal(this.module.ngettext('bar', 'bars', 0), 'BARS');
        assert.equal(this.module.ngettext('bar', 'bars', 2), 'BARS');
      });
    });

    describe('.remove()', function () {
      it('should teardown the module', function () {
        var target = cy.stub(this.module, 'teardown');

        this.module.remove();

        expect(target).to.be.called;
      });

      it('should remove the element from the page', function () {
        cy.window().then(win => {
          win.jQuery('#fixture').append(this.module.el);
          this.module.remove();

          assert.equal(win.jQuery('#fixture').children().length, 0);
        })

      });
    });
  });
});
