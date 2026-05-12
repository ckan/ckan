/*globals describe beforeEach afterEach it assert sinon ckan jQuery */
describe('ckan.Client()', {testIsolation: false}, function () {
  before(() => {
    cy.visit('/');
  });

  beforeEach(function () {
    cy.window().then(win => {
      cy.wrap(win.ckan.Client).as('Client');
      win.client = new win.ckan.Client();
    })

  });

  it('should add a new instance to each client', function () {
    cy.window().then(win => {
      let target = win.ckan.sandbox().client;

      expect(target).to.be.instanceOf(this.Client);
    })


  });

  it('should set the .endpoint property to options.endpoint', function () {
    cy.window().then(win => {
      let client = new this.Client({endpoint: 'http://example.com'});
      expect(client.endpoint).to.be.equal('http://example.com');
    })
  });

  it('should default the endpoint to a blank string', function () {
    cy.window().then(win => {
      expect(win.client.endpoint).to.be.equal('')
    })
  });

  describe('.url(path)', {testIsolation: false}, function () {
    beforeEach(function () {
      cy.window().then(win => {
        win.client.endpoint = 'http://api.example.com';
      })
    });

    it('should return the path with the endpoint prepended', function () {
      cy.window().then(win => {
        expect(win.client.url('/api/endpoint')).to.be.equal('http://api.example.com/api/endpoint');
      })

    });

    it('should normalise preceding slashes in the path', function () {
      cy.window().then(win => {
        expect(win.client.url('api/endpoint')).to.be.equal('http://api.example.com/api/endpoint');
      })
    });

    it('should return the string if it already has a protocol', function () {
      cy.window().then(win => {
        expect(win.client.url('http://example.com/my/endpoint')).to.be.equal( 'http://example.com/my/endpoint');
      })
    });
  });

  describe('.getLocaleData(locale, success, error)', {testIsolation: false}, function () {
    beforeEach(function () {
      cy.window().then(win => {
        win.fakePromise = cy.stub(win.jQuery.Deferred());
        win.fakePromise.then.returns(win.fakePromise);
        cy.stub(win.jQuery, 'getJSON').returns(win.fakePromise);
      })
    });

    it('should return a jQuery promise', function () {
      cy.window().then(win => {
        let target = win.client.getLocaleData('en');
        assert.ok(target === win.fakePromise, 'target === this.fakePromise');
      })
    });

    it('should request the locale provided', function () {
      cy.window().then(win => {
        let target = win.client.getLocaleData('en');
        expect(win.jQuery.getJSON).to.be.called;
        expect(win.jQuery.getJSON).to.be.calledWith( '/api/i18n/en');
      })
    });
  });

  describe('.getCompletions(url, options, success, error)', {testIsolation: false}, function () {
    beforeEach(function () {
      cy.window().then(win => {
        win.fakePiped  = cy.stub(win.jQuery.Deferred());
        win.fakePiped.then.returns(win.fakePiped);
        win.fakePiped.promise.returns(win.fakePiped);

        win.fakePromise = cy.stub(win.jQuery.Deferred());
        win.fakePromise.pipe.returns(win.fakePiped);

        cy.stub(win.jQuery, 'ajax').returns(win.fakePromise);
      })
    });

    it('should return a jQuery promise', function () {
      cy.window().then(win => {
        let target = win.client.getCompletions('url');
        assert.ok(target === win.fakePiped, 'target === this.fakePiped');
      })
    });

    it('should make an ajax request for the url provided', function () {
      cy.window().then(win => {
        function success() {}
        function error() {}

        let target = win.client.getCompletions('url', success, error);

        expect(win.jQuery.ajax).to.be.called;
        expect(win.jQuery.ajax).to.be.calledWith( {url: '/url'});

        expect(win.fakePiped.then).to.be.called;
        expect(win.fakePiped.then).to.be.calledWith(success, error);
      });
    });

    it('should pipe the result through .parseCompletions()', function () {
      cy.window().then(win => {
        let target = win.client.getCompletions('url');

        expect(win.fakePromise.pipe).to.be.called;
        expect(win.fakePromise.pipe).to.be.calledWith(win.client.parseCompletions);
      })
    });

    it('should allow a custom format option to be provided', function () {
      cy.window().then(win => {
        function format() {}

        let target = win.client.getCompletions('url', {format: format});

        expect(win.fakePromise.pipe).to.be.called;
        expect(win.fakePromise.pipe).to.be.calledWith(format);
      })

    });

  });

  describe('.parseCompletions(data, options)', {testIsolation: false}, function () {
    it('should return a string of tags for a ResultSet collection', function () {
      let data = {
        ResultSet: {
          Result: [
            {"Name": "1 percent"}, {"Name": "18thc"}, {"Name": "19thcentury"}
          ]
        }
      };

      cy.window().then(win =>{
        let target = win.client.parseCompletions(data, {});

        expect(target).to.be.deep.equal( ["1 percent", "18thc", "19thcentury"]);
      })

    });

    it('should return a string of formats for a ResultSet collection', function () {
      let data = {
        ResultSet: {
          Result: [
            {"Format": "json"}, {"Format": "csv"}, {"Format": "text"}
          ]
        }
      };

      cy.window().then(win => {
        let target = win.client.parseCompletions(data, {});

        expect(target).to.be.deep.equal( ["json", "csv", "text"]);
      })

    });

    it('should strip out duplicates with a case insensitive comparison', function () {
      let data = {
        ResultSet: {
          Result: [
            {"Name": " Test"}, {"Name": "test"}, {"Name": "TEST"}
          ]
        }
      };

      cy.window().then(win => {
        let target = win.client.parseCompletions(data, {});

        expect(target).to.be.deep.equal(["Test"]);
      })
    });

    it('should return an array of objects if options.objects is true', function () {
      let data = {
        ResultSet: {
          Result: [
            {"Format": "json"}, {"Format": "csv"}, {"Format": "text"}
          ]
        }
      };

      cy.window().then(win => {
        let target = win.client.parseCompletions(data, {objects: true});

        expect(target).to.be.deep.equal( [
          {id: "json", text: "json"},
          {id: "csv", text: "csv"},
          {id: "text", text: "text"}
        ]);
      })
    });

    it('should call .parsePackageCompletions() id data is a string', function () {
      let data = 'Name|id';
      cy.window().then(win => {
        let target = cy.stub(win.client, 'parsePackageCompletions');

        win.client.parseCompletions(data, {objects: true});

        expect(target).to.be.called;
        expect(target).to.be.calledWith(data);
      })

    });
  });

  describe('.parseCompletionsForPlugin(data)', {testIsolation: false}, function () {
    it('should return a string of tags for a ResultSet collection', function () {
      let data = {
        ResultSet: {
          Result: [
            {"Name": "1 percent"}, {"Name": "18thc"}, {"Name": "19thcentury"}
          ]
        }
      };

      cy.window().then(win => {
        let target = win.client.parseCompletionsForPlugin(data);

        expect(target).to.be.deep.equal( {
          results: [
            {id: "1 percent", text: "1 percent"},
            {id: "18thc", text:  "18thc"},
            {id: "19thcentury", text: "19thcentury"}
          ]
        });
      })

    });
  });

  describe('.parsePackageCompletions(string, options)', {testIsolation: false}, function () {
    it('should parse the package completions string', function () {
      let data = 'Package 1|package-1\nPackage 2|package-2\nPackage 3|package-3\n';
      cy.window().then(win => {
        let target = win.client.parsePackageCompletions(data);

        expect(target).to.be.deep.equal( ['package-1', 'package-2', 'package-3']);
      })
    });

    it('should return an object if options.object is true', function () {
      let data = 'Package 1|package-1\nPackage 2|package-2\nPackage 3|package-3\n';
      cy.window().then(win => {
        let target = win.client.parsePackageCompletions(data, {objects: true});

        expect(target).to.be.deep.equal( [
          {id: 'package-1', text: 'Package 1'},
          {id: 'package-2', text: 'Package 2'},
          {id: 'package-3', text: 'Package 3'}
        ]);
      })
    });
  });

});
