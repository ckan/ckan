/*globals describe beforeEach afterEach it assert sinon ckan jQuery */
describe('ckan.module(id, properties|callback)', function () {
  beforeEach(function () {
    ckan.module.registry = {};
    ckan.module.instances = {};
    this.factory = {};
  });

  it('should add a new item to the registry', function () {
    ckan.module('test', this.factory);

    assert.instanceOf(new ckan.module.registry.test(), ckan.module.BaseModule);
  });

  it('should allow a function to be provided', function () {
    var target = sinon.stub().returns({});
    ckan.module('test', target);

    assert.called(target);
  });

  it('should pass jQuery, i18n.translate() and i18n into the function', function () {
    var target = sinon.stub().returns({});
    ckan.module('test', target);

    assert.calledWith(target, jQuery, ckan.i18n.translate, ckan.i18n);
  });

  it('should throw an exception if the module is already defined', function () {
    ckan.module('name', this.factory);
    assert.throws(function () {
      ckan.module('name', this.factory);
    });
  });

  it('should return the ckan object', function () {
    assert.equal(ckan.module('name', this.factory), ckan);
  });

  describe('.initialize()', function () {
    beforeEach(function () {
      this.element1 = jQuery('<div data-module="test1">').appendTo(this.fixture);
      this.element2 = jQuery('<div data-module="test1">').appendTo(this.fixture);
      this.element3 = jQuery('<div data-module="test2">').appendTo(this.fixture);

      this.test1 = sinon.spy();

      // Add test1 to the registry.
      ckan.module.registry = {
        test1: this.test1
      };

      this.target = sinon.stub(ckan.module, 'createInstance');
    });

    afterEach(function () {
      this.target.restore();
    });

    it('should find all elements with the "data-module" attribute', function () {
      ckan.module.initialize();
      assert.called(this.target);
    });

    it('should skip modules that are not functions', function () {
      ckan.module.initialize();
      assert.calledTwice(this.target);
    });

    it('should call module.createInstance() with the element and factory', function () {
      ckan.module.initialize();
      assert.calledWith(this.target, this.test1, this.element1[0]);
      assert.calledWith(this.target, this.test1, this.element2[0]);
    });

    it('should return the module object', function () {
      assert.equal(ckan.module.initialize(), ckan.module);
    });

    it('should initialize more than one module sepearted by a space', function () {
      this.fixture.empty();
      this.element4 = jQuery('<div data-module="test1 test2">').appendTo(this.fixture);
      this.test2 = ckan.module.registry.test2 = sinon.spy();

      ckan.module.initialize();

      assert.calledWith(this.target, this.test1, this.element4[0]);
      assert.calledWith(this.target, this.test2, this.element4[0]);
    });

    it('should defer all published events untill all modules have loaded', function () {
      var pubsub    = ckan.pubsub;
      var callbacks = [];

      // Ensure each module is loaded. Three in total.
      ckan.module.registry = {
        test1: function () {},
        test2: function () {}
      };

      // Call a function to publish and subscribe to an event on each instance.
      this.target.restore();
      this.target = sinon.stub(ckan.module, 'createInstance', function () {
        var callback = sinon.spy();

        pubsub.publish('test');
        pubsub.subscribe('test', callback);

        callbacks.push(callback);
      });

      ckan.module.initialize();

      // Ensure that all subscriptions received all messages.
      assert.ok(callbacks.length, 'no callbacks were created');
      jQuery.each(callbacks, function () {
        assert.calledThrice(this);
      });
    });
  });

  describe('.createInstance(Module, element)', function () {
    beforeEach(function () {
      this.element = document.createElement('div');
      this.factory = ckan.module.BaseModule;
      this.factory.options = this.defaults = {test1: 'a', test2: 'b', test3: 'c'};

      this.sandbox = {
        i18n: {
          translate: sinon.spy()
        }
      };
      sinon.stub(ckan, 'sandbox').returns(this.sandbox);

      this.extractedOptions = {test1: 1, test2: 2};
      sinon.stub(ckan.module, 'extractOptions').returns(this.extractedOptions);
    });

    afterEach(function () {
      ckan.sandbox.restore();
      ckan.module.extractOptions.restore();
    });

    it('should extract the options from the element', function () {
      ckan.module.createInstance(this.factory, this.element);

      assert.called(ckan.module.extractOptions);
      assert.calledWith(ckan.module.extractOptions, this.element);
    });

    it('should not modify the defaults object', function () {
      var clone = jQuery.extend({}, this.defaults);
      ckan.module.createInstance(this.factory, this.element);

      assert.deepEqual(this.defaults, clone);
    });

    it('should create a sandbox object', function () {
      ckan.module.createInstance(this.factory, this.element);
      assert.called(ckan.sandbox);
      assert.calledWith(ckan.sandbox, this.element);
    });

    it('should initialize the module factory with the sandbox, options and translate function', function () {
      var target = sinon.spy();
      ckan.module.createInstance(target, this.element);

      assert.called(target);
      assert.calledWith(target, this.element, this.extractedOptions, this.sandbox);
    });

    it('should initialize the module as a constructor', function () {
      var target = sinon.spy();
      ckan.module.createInstance(target, this.element);

      assert.calledWithNew(target);

    });

    it('should call the .initialize() method if one exists', function () {
      var init = sinon.spy();
      var target = sinon.stub().returns({
        initialize: init
      });

      ckan.module.createInstance(target, this.element);

      assert.called(init);
    });

    it('should push the new instance into an array under ckan.module.instances', function () {
      var target = function MyModule() { return {'mock': 'instance'}; };
      target.namespace = 'test';

      ckan.module.createInstance(target, this.element);

      assert.deepEqual(ckan.module.instances.test, [{'mock': 'instance'}]);
    });

    it('should push further instances into the existing array under ckan.module.instances', function () {
      var target = function MyModule() { return {'mock': 'instance3'}; };
      target.namespace = 'test';

      ckan.module.instances.test = [{'mock': 'instance1'}, {'mock': 'instance2'}];
      ckan.module.createInstance(target, this.element);

      assert.deepEqual(ckan.module.instances.test, [
        {'mock': 'instance1'}, {'mock': 'instance2'}, {'mock': 'instance3'}
      ]);
    });

  });

  describe('.extractOptions(element)', function () {
    it('should extract the data keys from the element', function () {
      var element = jQuery('<div>', {
        'data-not-module': 'skip',
        'data-module': 'skip',
        'data-module-a': 'capture',
        'data-module-b': 'capture',
        'data-module-c': 'capture'
      })[0];

      var target = ckan.module.extractOptions(element);

      assert.deepEqual(target, {a: 'capture', b: 'capture', c: 'capture'});
    });

    it('should convert JSON contents of keys into JS primitives', function () {
      var element = jQuery('<div>', {
        'data-module-null': 'null',
        'data-module-int': '100',
        'data-module-arr': '[1, 2, 3]',
        'data-module-obj': '{"a": 1, "b":2, "c": 3}',
        'data-module-str': 'hello'
      })[0];

      var target = ckan.module.extractOptions(element);

      assert.deepEqual(target, {
        'null': null,
        'int': 100,
        'arr': [1, 2, 3],
        'obj': {"a": 1, "b": 2, "c": 3},
        'str': 'hello'
      });
    });

    it('should simply use strings for content that it cannot parse as JSON', function () {
      var element = jQuery('<div>', {
        'data-module-url': 'http://example.com/path/to.html',
        'data-module-bad': '{oh: 1, no'
      })[0];

      var target = ckan.module.extractOptions(element);

      assert.deepEqual(target, {
        'url': 'http://example.com/path/to.html',
        'bad': '{oh: 1, no'
      });
    });

    it('should convert keys with hyphens into camelCase', function () {
      var element = jQuery('<div>', {
        'data-module-long-property': 'long',
        'data-module-really-very-long-property': 'longer'
      })[0];

      var target = ckan.module.extractOptions(element);

      assert.deepEqual(target, {
        'longProperty': 'long',
        'reallyVeryLongProperty': 'longer'
      });
    });

    it('should set boolean attributes to true', function () {
      var element = jQuery('<div>', {
        'data-module-long-property': ''
      })[0];

      var target = ckan.module.extractOptions(element);

      assert.deepEqual(target, {'longProperty': true});
    });
  });

  describe('BaseModule(element, options, sandbox)', function () {
    var BaseModule = ckan.module.BaseModule;

    beforeEach(function () {
      this.el = jQuery('<div />');
      this.options = {};
      this.sandbox = ckan.sandbox();
      this.module = new BaseModule(this.el, this.options, this.sandbox);
    });

    it('should assign .el as the element option', function () {
      assert.ok(this.module.el === this.el);
    });

    it('should wrap .el in jQuery if not already wrapped', function () {
      var element = document.createElement('div');
      var target = new BaseModule(element, this.options, this.sandbox);

      assert.ok(target.el instanceof jQuery);
    });

    it('should deep extend the options object', function () {
      // Lazy check :/
      var target = sinon.stub(jQuery, 'extend');
      new BaseModule(this.el, this.options, this.sandbox);

      assert.called(target);
      assert.calledWith(target, true, {}, BaseModule.prototype.options, this.options);

      target.restore();
    });

    it('should assign the sandbox property', function () {
      assert.equal(this.module.sandbox, this.sandbox);
    });

    describe('.$(selector)', function () {
      it('should find children within the module element', function () {
        this.module.el.append(jQuery('<input /><input />'));
        assert.equal(this.module.$('input').length, 2);
      });
    });

    describe('.i18n()', function () {
      beforeEach(function () {
        this.i18n = {
          first: 'first string',
          second: {fetch: sinon.stub().returns('second string')},
          third: sinon.stub().returns('third string')
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
        assert.called(target);
        assert.calledWith(target, 1, 2, 3);
      });

      it('should pass the argments after the key into the translation function', function () {
        var target = this.module.options.i18n.third;
        this.module.i18n('third', 1, 2, 3);
        assert.called(target);
        assert.calledWith(target, 1, 2, 3);
      });
    });

    describe('.remove()', function () {
      it('should teardown the module', function () {
        var target = sinon.stub(this.module, 'teardown');

        this.module.remove();

        assert.called(target);
      });

      it('should remove the element from the page', function () {
        this.fixture.append(this.module.el);
        this.module.remove();

        assert.equal(this.fixture.children().length, 0);
      });
    });
  });
});
