describe('ckan.url()', function () {
  beforeEach(function () {
    ckan.SITE_ROOT = 'http://example.com';
    ckan.LOCALE_ROOT = ckan.SITE_ROOT + '/en';
  });

  it('should return the ckan.SITE_ROOT', function () {
    var target = ckan.url();
    assert.equal(target, ckan.SITE_ROOT);
  });

  it('should return the ckan.LOCALE_ROOT if true is passed', function () {
    var target = ckan.url(true);
    assert.equal(target, ckan.LOCALE_ROOT);
  });

  it('should append the path provided', function () {
    var target = ckan.url('/test.html');
    assert.equal(target, ckan.SITE_ROOT + '/test.html');
  });

  it('should append the path to the locale provided', function () {
    var target = ckan.url('/test.html', true);
    assert.equal(target, ckan.LOCALE_ROOT + '/test.html');
  });

  it('should handle missing preceding slashes', function () {
    var target = ckan.url('test.html');
    assert.equal(target, ckan.SITE_ROOT + '/test.html');
  });
});
