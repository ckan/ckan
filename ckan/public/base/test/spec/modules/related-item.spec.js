/*globals describe before beforeEach afterEach it assert sinon ckan jQuery */
describe('ckan.module.RelatedItemModule()', function () {
  var RelatedItemModule = ckan.module.registry['related-item'];

  before(function (done) {
    // Load our fixture into the this.fixture element.
    this.loadFixture('related-item.html', function (html) {
      this.template = html;
      done();
    });
  });

  beforeEach(function () {
    this.truncated = jQuery('<div/>');
    jQuery.fn.truncate = sinon.stub().returns(this.truncated);

    // Grab the loaded fixture.
    this.el = this.fixture.html(this.template).children();
    this.sandbox = ckan.sandbox();
    this.sandbox.body = this.fixture;
    this.module = new RelatedItemModule(this.el, {}, this.sandbox);
  });

  afterEach(function () {
    this.module.teardown();
    delete jQuery.fn.truncate;
  });

  describe('.initialize()', function () {
    it('should truncate the .prose element', function () {
      this.module.initialize();
      assert.called(jQuery.fn.truncate);
    });

    it('should pass the various options into the truncate plugin');

    it('should cache the collapsed height of the plugin', function () {
      this.module.initialize();
      assert.ok(this.module.collapsedHeight);
    });

    it('should listen for the "truncate" events', function () {
      var target = sinon.stub(this.truncated, 'on');
      this.module.initialize();

      assert.called(target);
      assert.calledWith(target, 'expand.truncate', this.module._onExpand);
      assert.calledWith(target, 'collapse.truncate', this.module._onCollapse);
    });
  });

  describe('._onExpand(event)', function () {
    it('should add the "expanded" class to the element', function () {
      this.module._onExpand(jQuery.Event());
      assert.isTrue(this.el.hasClass(this.module.options.expandedClass));
    });

    it('should add a bottom margin to the element', function () {
      this.module._onExpand(jQuery.Event());
      assert.ok(this.el.css('margin-bottom'));
    });

    it('should calcualte the difference between the current and cached height', function () {
      var target = sinon.stub(this.el, 'css');
      sinon.stub(this.el, 'height').returns(30);
      this.module.collapsedHeight = 10;
      this.module._onExpand(jQuery.Event());

      assert.called(target);
      assert.calledWith(target, 'margin-bottom', -20);
    });
  });

  describe('._onCollapse(event)', function () {
    it('should remove the "expanded" class from the element', function () {
      this.el.addClass(this.module.options.expandedClass);
      this.module._onCollapse(jQuery.Event());
      assert.isFalse(this.el.hasClass(this.module.options.expandedClass));
    });

    it('should remove the bottom margin from the element', function () {
      this.el.css('margin-bottom', -90);
      this.module._onCollapse(jQuery.Event());
      assert.equal(this.el.css('margin-bottom'), '0px'); 
    });
  });
});
