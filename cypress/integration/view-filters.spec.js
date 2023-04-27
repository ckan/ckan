// Skip view filters tests until resource views are tested in cypress
describe.skip('ckan.views.filters', function(){
  before(() => {
    cy.visit('/');
    cy.window().then(win => {
      cy.wrap(win.ckan.views.filters).as('filters');
      let setLocationHrefSpy = null;
      cy.wrap(setLocationHrefSpy).as('setLocationHrefSpy')
    });

  });

  function _currentHref(spy) {
    return spy.args[spy.args.length-1][0];
  }

  beforeEach(function() {
    this.filters._initialize('');
    this.setLocationHrefSpy = cy.spy();
    this.filters._setLocationHref = this.setLocationHrefSpy;
  });

  describe('#initialization', function() {
    it('should clear the filters on subsequent calls', function() {
      this.filters._initialize('?filters=country:Brazil');
      assert.deepEqual(['Brazil'], this.filters.get('country'));
      this.filters._initialize('');
      assert.equal(undefined, this.filters.get('country'));
    });

    it('should work with multiple filters', function() {
      let expectedFilters = {
        country: ['Brazil'],
        state: ['Paraiba']
      };

      this.filters._initialize('?filters=country:Brazil|state:Paraiba');

      assert.deepEqual(expectedFilters, this.filters.get());
    });

    it('should work with multiple values for the same filter', function() {
      let expectedFilters = {
        country: ['Brazil', 'Argentina'],
        state: ['Paraiba']
      };

      this.filters._initialize('?filters=country:Brazil|state:Paraiba|country:Argentina');

      assert.deepEqual(expectedFilters, this.filters.get());
    });

    it('should keep the order defined in the query string', function() {
      let expectedFiltersSorted = {
            country: ['Argentina', 'Brazil']
          },
          expectedFiltersReverse = {
            country: ['Brazil', 'Argentina']
          };

      this.filters._initialize('?filters=country:Argentina|country:Brazil');
      assert.deepEqual(expectedFiltersSorted, this.filters.get());

      this.filters._initialize('?filters=country:Brazil|country:Argentina');
      assert.deepEqual(expectedFiltersReverse, this.filters.get());
    });

    it('should work with a single numeric filter', function() {
      let expectedFilters = {
            year: ['2014']
          };

      this.filters._initialize('?filters=year:2014');
      assert.deepEqual(expectedFilters, this.filters.get());
    });

    it('should work with quoted filters', function() {
      let expectedFilters = {
            country: ['"Brazil"']
          };

      this.filters._initialize('?filters=country:"Brazil"');
      assert.deepEqual(expectedFilters, this.filters.get());
    });

    it('should work with filters with colons', function() {
      let expectedFilters = {
            time: ['11:00', '']
          };

      this.filters._initialize('?filters=time:11:00|time:');
      assert.deepEqual(expectedFilters, this.filters.get());
    });

    it('should not execute javascript', function () {

      const stub = cy.stub()
      cy.on ('window:alert', stub)
      this.filters._initialize('?{alert("This should not happen.")}');
      expect(stub).not.to.be.called;
    })
  });

  describe('#get', function(){
    it('should return all filters if called without params', function(){
      let expectedFilters = {
        country: ['Brazil']
      };

      this.filters._initialize('?filters=country:Brazil');

      assert.deepEqual(expectedFilters, this.filters.get());
    });

    it('should return the requested filter field', function(){
      let countryFilter;

      this.filters._initialize('?filters=country:Brazil');

      countryFilter = this.filters.get('country');

      assert.equal(1, countryFilter.length);
      assert.equal('Brazil', countryFilter[0]);
    });

    it('should return an empty object if there\'re no filters', function(){
      this.filters._initialize('');

      assert.deepEqual({}, this.filters.get());
    });

    it('should return undefined if there\'s no filter with the requested field', function(){
      let cityFilter;
      this.filters._initialize('?filters=country:Brazil');

      cityFilter = this.filters.get('city');

      assert.equal(undefined, cityFilter);
    });
  });

  describe('#set', function(){
    it('should set the filters', function(){
      let expectedFilters = {
        country: 'Brazil'
      };

      this.filters.set('country', 'Brazil');

      assert.deepEqual(expectedFilters, this.filters.get());
    });

    it('should update the url', function(){
      let expectedSearch = '?filters=country%3ABrazil%7Ccountry%3AArgentina' +
                           '%7Cindicator%3Ahappiness';

      this.filters.set('country', ['Brazil', 'Argentina']);
      this.filters.set('indicator', 'happiness');

      assert.include(_currentHref(this.setLocationHrefSpy), expectedSearch);
    });
  });

  describe('#setAndRedirectTo', function(){
    it('should set the filters', function(){
      let url = 'http://www.ckan.org',
          expectedFilters = {
            country: 'Brazil'
          };

      this.filters.setAndRedirectTo('country', 'Brazil', 'http://www.ckan.org');

      assert.deepEqual(expectedFilters, this.filters.get());
    });

    it('should update the url', function(){
      let url = 'http://www.ckan.org',
          expectedSearch = '?filters=country%3ABrazil%7Ccountry%3AArgentina' +
                           '%7Cindicator%3Ahappiness';

      this.filters.setAndRedirectTo('country', ['Brazil', 'Argentina'], url);
      this.filters.setAndRedirectTo('indicator', 'happiness', url);

      assert.include(_currentHref(this.setLocationHrefSpy), expectedSearch);
    });

    it('should keep the original url\'s query params', function(){
      let url = 'http://www.ckan.org/?id=42',
          expectedSearch = '?id=42&filters=country%3ABrazil%7Ccountry%3AArgentina' +
                           '%7Cindicator%3Ahappiness';

      this.filters.setAndRedirectTo('country', ['Brazil', 'Argentina'], url);
      this.filters.setAndRedirectTo('indicator', 'happiness', url);

      assert.include(_currentHref(this.setLocationHrefSpy), expectedSearch);
    });

    it('should override the original url\'s filters', function(){
      let url = 'http://www.ckan.org/?filters=country%3AEngland%7Cyear%3A2014',
          expectedSearch = '?filters=country%3ABrazil%7Ccountry%3AArgentina' +
                           '%7Cindicator%3Ahappiness';

      this.filters.setAndRedirectTo('country', ['Brazil', 'Argentina'], url);
      this.filters.setAndRedirectTo('indicator', 'happiness', url);

      assert.include(_currentHref(this.setLocationHrefSpy), expectedSearch);
    });
  });

  describe('#unset', function(){
    it('should unset the filters', function(){
      let expectedFilters = {};
      this.filters.set('country', 'Brazil');

      this.filters.unset('country', 'Brazil');

      assert.deepEqual(expectedFilters, this.filters.get());
    });

    it('should unset the filters when we unset every filter activated', function(){
      let expectedFilters = {};
      this.filters.set('country', ['Brazil', 'Argentina']);

      this.filters.unset('country', ['Brazil', 'Argentina']);

      assert.deepEqual(expectedFilters, this.filters.get());
    });

    it('should work with arrays', function(){
      let expectedFilters = {
        country: ['Argentina']
      };
      this.filters.set('country', ['Brazil', 'Argentina', 'Uruguay']);

      this.filters.unset('country', ['Brazil', 'Uruguay']);

      assert.deepEqual(expectedFilters, this.filters.get());
    });

    it('should update the url', function(){
      let expectedSearch = '?filters=country%3AArgentina';
      this.filters.set('country', ['Brazil', 'Argentina']);

      this.filters.unset('country', 'Brazil');

      assert.include(_currentHref(this.setLocationHrefSpy), expectedSearch);
    });
  });
});
