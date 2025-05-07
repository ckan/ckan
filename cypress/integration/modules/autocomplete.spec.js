/*globals describe beforeEach afterEach it assert sinon ckan jQuery */
describe('ckan.modules.AutocompleteModule()', function () {
  before(() => {
    cy.visit('/');
    cy.window().then(win => {
      cy.wrap(win.ckan.module.registry['autocomplete']).as('autocomplete');
      win.jQuery('<div id="fixture">').appendTo(win.document.body)
    })
  });

  beforeEach(function () {
    cy.window().then(win => {
      //FIXME: intermittent test failures without this hack:
      if (!win) { return }
      // Stub select2 plugin if loaded.
      if (win.jQuery.fn.select2) {
        this.select2 = cy.stub(win.jQuery.fn, 'select2').returns({
          data: cy.stub().returns({
            on: cy.stub()
          })
        });
      } else {
        this.select2 = win.jQuery.fn.select2 = cy.stub().returns({
          data: cy.stub().returns({
            on: cy.stub()
          })
        });
      }

      this.el = win.document.createElement('input');
      this.sandbox = win.ckan.sandbox();
      this.sandbox.body = win.jQuery('#fixture');
      this.module = new this.autocomplete(this.el, {}, this.sandbox);
    })
  });

  afterEach(function () {
    this.module.teardown();
    //delete jQuery.fn.select2;
  });

  describe('.initialize()', function () {
    it('should bind callback methods to the module', function () {
      cy.window().then(win => {
        let target = cy.stub(win.jQuery, 'proxyAll');

        this.module.initialize();
        expect(target).to.be.called;
        expect(target).to.be.calledWith(this.module, /_on/, /format/);

        target.restore();
      });
    });

    it('should setup the autocomplete plugin', function () {
      let target = cy.stub(this.module, 'setupAutoComplete');

      this.module.initialize();

      expect(target).to.be.called;
    });
  });

  describe('.setupAutoComplete()', function () {
    it('should initialize the autocomplete plugin', function () {
      this.module.setupAutoComplete();

      expect(this.select2).to.be.called;
      expect(this.select2).to.be.calledWith({
        width: 'resolve',
        query: this.module._onQuery,
        dropdownCssClass: '',
        containerCssClass: '',
        formatResult: this.module.formatResult,
        formatNoMatches: this.module.formatNoMatches,
        formatInputTooShort: this.module.formatInputTooShort,
        createSearchChoice: this.module.formatTerm, // Not used by tags.
        initSelection: this.module.formatInitialValue,
	      tokenSeparators: [','],
        minimumInputLength: 0
      });
    });

    it('should initialize the autocomplete plugin with a tags callback if options.tags is true', function () {
      this.module.options.tags = true;
      this.module.setupAutoComplete();

      expect(this.select2).to.be.called;
      expect(this.select2).to.calledWith({
        width: 'resolve',
        tags: this.module._onQuery,
        dropdownCssClass: '',
        containerCssClass: '',
        formatResult: this.module.formatResult,
        formatNoMatches: this.module.formatNoMatches,
        formatInputTooShort: this.module.formatInputTooShort,
        initSelection: this.module.formatInitialValue,
        tokenSeparators: [','],
        minimumInputLength: 0
      });
    })
    it('should watch the keydown event on the select2 input');

    it('should allow a custom css class to be added to the dropdown', function () {
      this.module.options.dropdownClass = 'tags';
      this.module.setupAutoComplete();

      expect(this.select2).to.be.called;
      expect(this.select2).to.be.calledWith({
        width: 'resolve',
        query: this.module._onQuery,
        dropdownCssClass: 'tags',
        containerCssClass: '',
        formatResult: this.module.formatResult,
        formatNoMatches: this.module.formatNoMatches,
        formatInputTooShort: this.module.formatInputTooShort,
        createSearchChoice: this.module.formatTerm, // Not used by tags.
        initSelection: this.module.formatInitialValue,
        tokenSeparators: [','],
        minimumInputLength: 0
      });
    });

    it('should allow a custom css class to be added to the container', function () {
      this.module.options.containerClass = 'tags';
      this.module.setupAutoComplete();

      expect(this.select2).to.be.called;
      expect(this.select2).to.be.calledWith({
        width: 'resolve',
        query: this.module._onQuery,
        dropdownCssClass: '',
        containerCssClass: 'tags',
        formatResult: this.module.formatResult,
        formatNoMatches: this.module.formatNoMatches,
        formatInputTooShort: this.module.formatInputTooShort,
        createSearchChoice: this.module.formatTerm, // Not used by tags.
        initSelection: this.module.formatInitialValue,
        tokenSeparators: [','],
        minimumInputLength: 0
      });
    });

    it('should allow a changing minimumInputLength', function () {
      this.module.options.minimumInputLength = 3;
      this.module.setupAutoComplete();

      expect(this.select2).to.be.called;
      expect(this.select2).to.be.calledWith({
        width: 'resolve',
        query: this.module._onQuery,
        dropdownCssClass: '',
        containerCssClass: '',
        formatResult: this.module.formatResult,
        formatNoMatches: this.module.formatNoMatches,
        formatInputTooShort: this.module.formatInputTooShort,
        createSearchChoice: this.module.formatTerm, // Not used by tags.
        initSelection: this.module.formatInitialValue,
        tokenSeparators: [','],
        minimumInputLength: 3
      });
    });

  });

  describe('.getCompletions(term, fn)', function () {
    beforeEach(function () {
      this.term = 'term';
      this.module.options.source = 'http://example.com?term=?';

      this.target = cy.stub(this.sandbox.client, 'getCompletions');
    });

    it('should get the completions from the client', function () {
      this.module.getCompletions(this.term);
      expect(this.target).to.be.called;
    });

    it('should replace the last ? in the source url with the term', function () {
      this.module.getCompletions(this.term);
      expect(this.target).to.be.calledWith('http://example.com?term=term');
    });

    it('should escape special characters in the term', function () {
      this.module.getCompletions('term with spaces');
      expect(this.target).to.calledWith('http://example.com?term=term%20with%20spaces');
    });
  });

  describe('.lookup(term, fn)', function () {
    beforeEach(function () {
      cy.stub(this.module, 'getCompletions');
      this.target = cy.spy();
      this.module.setupAutoComplete();
    });

    it('should set the _lastTerm property', function () {
      this.module.lookup('term', this.target);
      assert.equal(this.module._lastTerm, 'term');
    });

    it('should call the fn immediately if there is no term', function () {
      this.module.lookup('', this.target);
      expect(this.target).to.be.called;
      expect(this.target).to.be.calledWith({results: []});
    });

    it('should debounce the request if there is a term');
    it('should cancel the last request');
  });

  describe('.formatResult(state)', function () {
    beforeEach(function () {
      this.module._lastTerm = 'term';
    });

    it('should return the string with the last term wrapped in bold tags', function () {
      let target = this.module.formatResult({id: 'we have termites', text: 'we have termites'});
      assert.equal(target, 'we have <b>term</b>ites');
    });

    it('should return the string with each instance of the term wrapped in bold tags', function () {
      let target = this.module.formatResult({id: 'we have a termite terminology', text: 'we have a termite terminology'});
      assert.equal(target, 'we have a <b>term</b>ite <b>term</b>inology');
    });

    it('should return the term if there is no last term saved', function () {
      delete this.module._lastTerm;
      let target = this.module.formatResult({id: 'we have a termite terminology', text: 'we have a termite terminology'});
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

  describe('.formatTerm()', function () {
    it('should return an item object with id and text properties', function () {
      assert.deepEqual(this.module.formatTerm('test'), {id: 'test', text: 'test'});
    });

    it('should trim whitespace from the value', function () {
      assert.deepEqual(this.module.formatTerm(' test  '), {id: 'test', text: 'test'});
    });

    it('should convert commas in ids into unicode characters', function () {
      assert.deepEqual(this.module.formatTerm('test, test'), {id: 'test\u002C test', text: 'test, test'});
    });
  });

  describe('.formatInitialValue(element, callback)', function () {
    beforeEach(function () {
      this.callback = cy.spy();
    });

    it('should pass an item object with id and text properties into the callback', function () {
      cy.window().then(win => {
        let target = win.jQuery('<input value="test"/>');

        this.module.formatInitialValue(target, this.callback);
        expect(this.callback).to.be.calledWith({id: 'test', text: 'test'});
      })
    });

    it('should pass an array of properties into the callback if options.tags is true', function () {
      cy.window().then(win => {
        this.module.options.tags = true;
        let target = win.jQuery('<input />', {value: "test, test"});

        this.module.formatInitialValue(target, this.callback);
        expect(this.callback).to.be.calledWith([{id: 'test', text: 'test'}, {id: 'test', text: 'test'}]);
      })
    });

    it('should return the value if no callback is provided (to support select2 v2.1)', function () {
      cy.window().then(win => {
        let target = win.jQuery('<input value="test"/>');
        // FIXME: why is this *sometimes* an array?
        let value = this.module.formatInitialValue(target)
        if (Array.isArray(value)) {
          assert.deepEqual(value, [{id: 'test', text: 'test'}])
        } else {
          assert.deepEqual(value, {id: 'test', text: 'test'})
        }
      })
    });
  });

  describe('._onQuery(options)', function () {
    it('should lookup the current term with the callback', function () {
      let target = cy.stub(this.module, 'lookup');

      this.module._onQuery({term: 'term', callback: 'callback'});

      expect(target).to.be.called;
      expect(target).to.be.calledWith('term', 'callback');
    });

    it('should do nothing if there is no options object', function () {
      let target = cy.stub(this.module, 'lookup');
      this.module._onQuery();
      expect(target).to.not.be.called;
    });
  });

  describe('._onKeydown(event)', function () {
    beforeEach(function () {
      cy.window().then(win => {
        this.keyDownEvent = win.jQuery.Event("keydown", {key: ',', which: 188});
        this.fakeEvent = {};
        this.clock = cy.clock();
        this.jQuery = cy.spy(win.jQuery.fn, 'init');
        this.Event = cy.stub(win.jQuery, 'Event').returns(this.fakeEvent);
        this.trigger = cy.stub(win.jQuery.fn, 'trigger');
      })
    });

    it('should trigger fake "return" keypress if a comma is pressed', function () {
      cy.window().then(win => {

        this.module._onKeydown(this.keyDownEvent);
        this.clock.tick(100);

        expect(this.jQuery).to.be.called;
        expect(this.Event).to.be.called;
        expect(this.trigger).to.be.called;
        expect(this.trigger).to.be.calledWith(this.fakeEvent);
      })
    });

    it('should do nothing if another key is pressed', function () {
      this.keyDownEvent.key = '╚';
      this.keyDownEvent.which = 200;

      this.module._onKeydown(this.keyDownEvent);

      this.clock.tick(100);

      expect(this.Event).to.not.be.called;
    });

    it('should do nothing if key is pressed which has the comma key-code but is not a comma', function () {
      this.keyDownEvent.key = 'ת';
      this.keyDownEvent.which = 188;

      this.module._onKeydown(this.keyDownEvent);

      this.clock.tick(100);

      expect(this.Event).to.not.be.called;
    });
  });
});
