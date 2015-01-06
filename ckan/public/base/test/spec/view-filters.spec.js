describe('ckan.views.filters', function(){
  var filters = ckan.views.filters,
      setLocationHrefSpy;

  function _currentHref() {
    return setLocationHrefSpy.args[setLocationHrefSpy.args.length-1][0];
  }

  beforeEach(function() {
    filters._initialize('');
    setLocationHrefSpy = sinon.spy();
    filters._setLocationHref = setLocationHrefSpy;
  });

  describe('#initialization', function() {
    it('should clear the filters on subsequent calls', function() {
      filters._initialize('?filters=country:Brazil');
      assert.deepEqual(['Brazil'], filters.get('country'));
      filters._initialize('');
      assert.equal(undefined, filters.get('country'));
    });

    it('should work with multiple filters', function() {
      var expectedFilters = {
        country: ['Brazil'],
        state: ['Paraiba']
      };

      filters._initialize('?filters=country:Brazil|state:Paraiba');

      assert.deepEqual(expectedFilters, filters.get());
    });

    it('should work with multiple values for the same filter', function() {
      var expectedFilters = {
        country: ['Brazil', 'Argentina'],
        state: ['Paraiba']
      };

      filters._initialize('?filters=country:Brazil|state:Paraiba|country:Argentina');

      assert.deepEqual(expectedFilters, filters.get());
    });

    it('should keep the order defined in the query string', function() {
      var expectedFiltersSorted = {
            country: ['Argentina', 'Brazil']
          },
          expectedFiltersReverse = {
            country: ['Brazil', 'Argentina']
          };

      filters._initialize('?filters=country:Argentina|country:Brazil');
      assert.deepEqual(expectedFiltersSorted, filters.get());

      filters._initialize('?filters=country:Brazil|country:Argentina');
      assert.deepEqual(expectedFiltersReverse, filters.get());
    });

    it('should work with a single numeric filter', function() {
      var expectedFilters = {
            year: ['2014']
          };

      filters._initialize('?filters=year:2014');
      assert.deepEqual(expectedFilters, filters.get());
    });

    it('should work with quoted filters', function() {
      var expectedFilters = {
            country: ['"Brazil"']
          };

      filters._initialize('?filters=country:"Brazil"');
      assert.deepEqual(expectedFilters, filters.get());
    });

    it('should work with filters with colons', function() {
      var expectedFilters = {
            time: ['11:00', '']
          };

      filters._initialize('?filters=time:11:00|time:');
      assert.deepEqual(expectedFilters, filters.get());
    });
  });

  describe('#get', function(){
    it('should return all filters if called without params', function(){
      var expectedFilters = {
        country: ['Brazil']
      };

      filters._initialize('?filters=country:Brazil');

      assert.deepEqual(expectedFilters, filters.get());
    });

    it('should return the requested filter field', function(){
      var countryFilter;

      filters._initialize('?filters=country:Brazil');

      countryFilter = filters.get('country');

      assert.equal(1, countryFilter.length);
      assert.equal('Brazil', countryFilter[0]);
    });

    it('should return an empty object if there\'re no filters', function(){
      filters._initialize('');

      assert.deepEqual({}, filters.get());
    });

    it('should return undefined if there\'s no filter with the requested field', function(){
      var cityFilter;
      filters._initialize('?filters=country:Brazil');

      cityFilter = filters.get('city');

      assert.equal(undefined, cityFilter);
    });
  });

  describe('#set', function(){
    it('should set the filters', function(){
      var expectedFilters = {
        country: 'Brazil'
      };

      filters.set('country', 'Brazil');

      assert.deepEqual(expectedFilters, filters.get());
    });

    it('should update the url', function(){
      var expectedSearch = '?filters=country%3ABrazil%7Ccountry%3AArgentina' +
                           '%7Cindicator%3Ahappiness';

      filters.set('country', ['Brazil', 'Argentina']);
      filters.set('indicator', 'happiness');

      assert.include(_currentHref(), expectedSearch);
    });
  });

  describe('#setAndRedirectTo', function(){
    it('should set the filters', function(){
      var url = 'http://www.ckan.org',
          expectedFilters = {
            country: 'Brazil'
          };

      filters.setAndRedirectTo('country', 'Brazil', 'http://www.ckan.org');

      assert.deepEqual(expectedFilters, filters.get());
    });

    it('should update the url', function(){
      var url = 'http://www.ckan.org',
          expectedSearch = '?filters=country%3ABrazil%7Ccountry%3AArgentina' +
                           '%7Cindicator%3Ahappiness';

      filters.setAndRedirectTo('country', ['Brazil', 'Argentina'], url);
      filters.setAndRedirectTo('indicator', 'happiness', url);

      assert.include(_currentHref(), expectedSearch);
    });

    it('should keep the original url\'s query params', function(){
      var url = 'http://www.ckan.org/?id=42',
          expectedSearch = '?id=42&filters=country%3ABrazil%7Ccountry%3AArgentina' +
                           '%7Cindicator%3Ahappiness';

      filters.setAndRedirectTo('country', ['Brazil', 'Argentina'], url);
      filters.setAndRedirectTo('indicator', 'happiness', url);

      assert.include(_currentHref(), expectedSearch);
    });

    it('should override the original url\'s filters', function(){
      var url = 'http://www.ckan.org/?filters=country%3AEngland%7Cyear%3A2014',
          expectedSearch = '?filters=country%3ABrazil%7Ccountry%3AArgentina' +
                           '%7Cindicator%3Ahappiness';

      filters.setAndRedirectTo('country', ['Brazil', 'Argentina'], url);
      filters.setAndRedirectTo('indicator', 'happiness', url);

      assert.include(_currentHref(), expectedSearch);
    });
  });

  describe('#unset', function(){
    it('should unset the filters', function(){
      var expectedFilters = {};
      filters.set('country', 'Brazil');

      filters.unset('country', 'Brazil');

      assert.deepEqual(expectedFilters, filters.get());
    });

    it('should unset the filters when we unset every filter activated', function(){
      var expectedFilters = {};
      filters.set('country', ['Brazil', 'Argentina']);

      filters.unset('country', ['Brazil', 'Argentina']);

      assert.deepEqual(expectedFilters, filters.get());
    });

    it('should work with arrays', function(){
      var expectedFilters = {
        country: ['Argentina']
      };
      filters.set('country', ['Brazil', 'Argentina', 'Uruguay']);

      filters.unset('country', ['Brazil', 'Uruguay']);

      assert.deepEqual(expectedFilters, filters.get());
    });

    it('should update the url', function(){
      var expectedSearch = '?filters=country%3AArgentina';
      filters.set('country', ['Brazil', 'Argentina']);

      filters.unset('country', 'Brazil');

      assert.include(_currentHref(), expectedSearch);
    });
  });
});
