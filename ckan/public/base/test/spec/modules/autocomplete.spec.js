/*globals describe beforeEach afterEach it assert sinon ckan jQuery */
describe('ckan.modules.AutocompleteModule()', function () {
  var Autocomplete = ckan.module.registry['autocomplete'];

  beforeEach(function () {
    // Stub select2 plugin if loaded.
    if (jQuery.fn.select2) {
      this.select2 = sinon.stub(jQuery.fn, 'select2');
    } else {
      this.select2 = jQuery.fn.select2 = sinon.spy();
    }

    this.el = document.createElement('input');
    this.sandbox = ckan.sandbox();
    this.sandbox.body = this.fixture;
    this.module = new Autocomplete(this.el, {}, this.sandbox);
  });

  afterEach(function () {
    this.module.teardown();

    if (this.select2.restore) {
      this.select2.restore();
    } else {
      delete jQuery.fn.select2;
    }
  });

  describe('.initialize()', function () {
    it('should bind callback methods to the module', function () {
      var target = sinon.stub(jQuery, 'proxyAll');

      this.module.initialize();

      assert.called(target);
      assert.calledWith(target, this.module, /_on/, /format/);

      target.restore();
    });

    it('should setup the autocomplete plugin', function () {
      var target = sinon.stub(this.module, 'setupAutoComplete');

      this.module.initialize();

      assert.called(target);
    });
  });

  describe('.setupAutoComplete()', function () {
    it('should initialize the autocomplete plugin', function () {
      this.module.setupAutoComplete();

      assert.called(this.select2);
      assert.calledWith(this.select2, {
        tags: this.module._onQuery,
        formatResult: this.module.formatResult,
        formatNoMatches: this.module.formatNoMatches,
        formatInputTooShort: this.module.formatInputTooShort
      });
    });
  });

  describe('.getCompletions(term, fn)', function () {
    beforeEach(function () {
      this.term = 'term';
      this.module.options.source = 'http://example.com?term=?';

      this.target = sinon.stub(this.sandbox.client, 'getCompletions');
    });

    it('should get the completions from the client', function () {
      this.module.getCompletions(this.term);
      assert.called(this.target);
    });

    it('should replace the last ? in the source url with the term', function () {
      this.module.getCompletions(this.term);
      assert.calledWith(this.target, 'http://example.com?term=term');
    });

    it('should escape special characters in the term', function () {
      this.module.getCompletions('term with spaces');
      assert.calledWith(this.target, 'http://example.com?term=term%20with%20spaces');
    });

    it('should set the formatter to work with the plugin', function () {
      this.module.getCompletions(this.term);
      assert.calledWith(this.target, 'http://example.com?term=term', {
        format: this.sandbox.client.parseCompletionsForPlugin
      });
    });
  });

  describe('.lookup(term, fn)', function () {
    beforeEach(function () {
      sinon.stub(this.module, 'getCompletions');
      this.target = sinon.spy();
    });

    it('should set the _lastTerm property', function () {
      this.module.lookup('term');
      assert.equal(this.module._lastTerm, 'term');
    });

    it('should call the fn immediately if there is no term', function () {
      this.module.lookup('', this.target);
      assert.called(this.target);
      assert.calledWith(this.target, {results: []});
    });

    it('should debounce the request if there is a term');
    it('should cancel the last request');
  });

  describe('.formatResult(state)', function () {
    beforeEach(function () {
      this.module._lastTerm = 'term';
    });

    it('should return the string with the last term wrapped in bold tags', function () {
      var target = this.module.formatResult({id: 'we have termites', text: 'we have termites'});
      assert.equal(target, 'we have <b>term</b>ites');
    });

    it('should return the string with each instance of the term wrapped in bold tags', function () {
      var target = this.module.formatResult({id: 'we have a termite terminology', text: 'we have a termite terminology'});
      assert.equal(target, 'we have a <b>term</b>ite <b>term</b>inology');
    });

    it('should return the term if there is no last term saved', function () {
      delete this.module._lastTerm;
      var target = this.module.formatResult({id: 'we have a termite terminology', text: 'we have a termite terminology'});
      assert.equal(target, 'we have a termite terminology');
    });
  });

  describe('.formatNoMatches(term)', function () {
    it('should return the no matches string if there is a term', function () {
      var target = this.module.formatNoMatches('term');
      assert.equal(target, 'No matches found');
    });

    it('should return the empty string if there is no term', function () {
      var target = this.module.formatNoMatches('');
      assert.equal(target, 'Start typing…');
    });
  });

  describe('.formatInputTooShort(term, min)', function () {
    it('should return the plural input too short string', function () {
      var target = this.module.formatInputTooShort('term', 2);
      assert.equal(target, 'Input is too short, must be at least 2 characters');
    });

    it('should return the singular input too short string', function () {
      var target = this.module.formatInputTooShort('term', 1);
      assert.equal(target, 'Input is too short, must be at least one character');
    });
  });

  describe('._onQuery(options)', function () {
    it('should lookup the current term with the callback', function () {
      var target = sinon.stub(this.module, 'lookup');

      this.module._onQuery({term: 'term', callback: 'callback'});

      assert.called(target);
      assert.calledWith(target, 'term', 'callback');
    });
  });
});
