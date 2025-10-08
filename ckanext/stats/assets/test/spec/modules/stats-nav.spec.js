/*globals describe before beforeEach afterEach it assert sinon ckan jQuery */
describe('ckan.module.StatsNavModule()', function () {
  var StatsNavModule = ckan.module.registry['stats-nav'];

  beforeEach(function () {
    this.el = document.createElement('div');
    this.sandbox = ckan.sandbox();
    this.sandbox.body = this.fixture;
    this.sandbox.location = {
      href: '',
      hash: ''
    };
    this.module = new StatsNavModule(this.el, {}, this.sandbox);

    jQuery.fn.tab = sinon.stub();
  });

  afterEach(function () {
    this.module.teardown();

    delete jQuery.fn.tab;
  });

  describe('.initialize()', function () {
    it('should listen for shown events and update the location.hash', function () {
      var anchor = jQuery('<a />').attr('href', '#stats-test')[0];

      this.module.initialize();
      this.module.el.trigger({type: 'shown', target: anchor});

      assert.equal(this.sandbox.location.hash, 'test');
    });

    it('should select the tab from the location hash on init', function () {
      var anchor = jQuery('<a />').attr('href', '#stats-test').appendTo(this.el);

      this.sandbox.location.hash = '#test';
      this.module.initialize();

      assert.called(jQuery.fn.tab);
      assert.calledWith(jQuery.fn.tab, 'show');
    });
  });
});
