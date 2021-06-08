
describe('ckan.initialize()', function () {
  before(() => {
    cy.visit('/');
  });

  beforeEach(function () {
    cy.window().then(win => {
      win.promise = win.jQuery.Deferred();
      win.target = cy.stub(win.ckan.Client.prototype, 'getLocaleData').returns(win.promise);
    })
  });

  afterEach(function () {
    cy.window().then(win => {
      win.target.restore();
    })
  });

  it('should load the localisations for the current page', function () {
    cy.window().then(win => {
      win.ckan.initialize();
      expect(win.target).to.be.called;
    })

  });

  it('should load the localisations into the i18n library', function () {
    cy.window().then(win => {
      const target = cy.spy(win.ckan.i18n, 'load');
      const data = {lang: {}};

      win.ckan.initialize();
      win.promise.resolve(data);

      expect(target).to.be.called;
      expect(target).to.be.calledWith(data);
      target.restore();
    });

  });

  it('should initialize the module on the page', function () {
    cy.window().then(win => {
      let target = cy.stub(win.ckan.module, 'initialize');
      win.ckan.initialize();
      win.promise.resolve();

      expect(target).to.be.called;
      target.restore();
    })
  });
});

describe('ckan.url()', function () {
  beforeEach(function () {
    cy.window().then(win => {
      win.ckan.SITE_ROOT = 'http://example.com';
      win.ckan.LOCALE_ROOT = win.ckan.SITE_ROOT + '/en';
    })

  });

  it('should return the ckan.SITE_ROOT', function () {
    cy.window().then(win => {
      let target = win.ckan.url();
      expect(target).to.be.equal(win.ckan.SITE_ROOT);
    })
  });

  it('should return the ckan.LOCALE_ROOT if true is passed', function () {
    cy.window().then(win => {
      let target = win.ckan.url(true);
      expect(target).to.be.equal(win.ckan.LOCALE_ROOT);
    })

  });

  it('should append the path provided', function () {
    cy.window().then(win => {
      let target = win.ckan.url('/test.html');
      expect(target).to.be.equal(win.ckan.SITE_ROOT + '/test.html');
    })
  });

  it('should append the path to the locale provided', function () {
    cy.window().then(win => {
      let target = win.ckan.url('/test.html', true);
      expect(target).to.be.equal(win.ckan.LOCALE_ROOT + '/test.html');
    })

  });

  it('should handle missing preceding slashes', function () {
    cy.window().then(win => {
      let target = win.ckan.url('test.html');
      expect(target).to.be.equal(win.ckan.SITE_ROOT + '/test.html');
    })
  });
});
