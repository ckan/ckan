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

      var target = function () { return {'mock': 'instance'}; };
      target.namespace = 'test';

      ckan.module.createInstance(target, this.element);

      assert.deepEqual(ckan.module.instances.test, [{'mock': 'instance'}]);
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
  });
});
