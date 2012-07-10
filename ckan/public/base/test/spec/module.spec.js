/*globals describe beforeEach afterEach it assert sinon ckan jQuery */
describe('ckan.module()', function () {
  beforeEach(function () {
    ckan.module.registry = {};

    this.factory = function () {};
  });

  it('should add a new item to the registry', function () {
    ckan.module('name', this.factory);

    assert.equal(ckan.module.registry.name, this.factory);
  });

  it('should throw an exception if the module is already defined', function () {
    ckan.module('name', this.factory);
    assert.throws(function () {
      ckan.module('name', this.factory);
    });
  });

  it('should assign the default object to the factory function', function () {
    var defaults = {};

    ckan.module('name', this.factory, defaults);
    assert.equal(this.factory.defaults, defaults);
  });

  it('should return the ckan object', function () {
    assert.equal(ckan.module('name', this.factory), ckan);
  });

  describe('.initialize()', function () {
    beforeEach(function () {
      this.element1 = jQuery('<div data-module="test1">').appendTo(this.fixture);
      this.element2 = jQuery('<div data-module="test1">').appendTo(this.fixture);
      this.element3 = jQuery('<div data-module="test2">').appendTo(this.fixture);

      this.test1 = sinon.spy('test1');

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
      sinon.assert.called(this.target);
    });

    it('should skip modules that are not functions', function () {
      ckan.module.initialize();
      sinon.assert.calledTwice(this.target);
    });

    it('should call module.createInstance() with the element and factory', function () {
      ckan.module.initialize();
      sinon.assert.calledWith(this.target, this.test1, this.element1[0]);
      sinon.assert.calledWith(this.target, this.test1, this.element2[0]);
    });

    it('should return the module object', function () {
      assert.equal(ckan.module.initialize(), ckan.module);
    });
  });

  describe('.createInstance()', function () {
    beforeEach(function () {
      this.element = document.createElement('div');
      this.factory = sinon.spy('factory()');
      this.factory.defaults = this.defaults = {test1: 'a', test2: 'b', test3: 'c'};

      this.sandbox = {
        options: {},
        i18n: {
          translate: sinon.spy('i18n.translate()')
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

      sinon.assert.called(ckan.module.extractOptions);
      sinon.assert.calledWith(ckan.module.extractOptions, this.element);
    });

    it('should not modify the defaults object', function () {
      var clone = jQuery.extend({}, this.defaults);
      ckan.module.createInstance(this.factory, this.element);

      assert.deepEqual(this.defaults, clone);
    });

    it('should create a sandbox object', function () {
      ckan.module.createInstance(this.factory, this.element);
      sinon.assert.called(ckan.sandbox);
      sinon.assert.calledWith(ckan.sandbox, this.element);
    });

    it('should call the module factory with the sandbox, options and translate function', function () {
      ckan.module.createInstance(this.factory, this.element);

      sinon.assert.called(this.factory);
      sinon.assert.calledWith(this.factory, this.sandbox, this.sandbox.options, this.sandbox.i18n.translate);
    });

    it('should set the module factory scope to the element', function () {
      ckan.module.createInstance(this.factory, this.element);

      sinon.assert.called(this.factory);
      sinon.assert.calledOn(this.factory, this.element);
    });
  });

  describe('.extractOptions()', function () {
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
