/*globals describe beforeEach afterEach it assert sinon ckan jQuery */
describe('ckan.notify()', function () {
  beforeEach(function () {
    this.element = jQuery('<div />');
    this.fixture.append(this.element);

    ckan.notify.el = this.element;
  });

  it('should append a notification to the element', function () {
    ckan.notify('test');
    assert.equal(this.element.children().length, 1, 'should be one child');
    ckan.notify('test');
    assert.equal(this.element.children().length, 2, 'should be two children');
  });

  it('should append a notification title', function () {
    ckan.notify('test');
    assert.equal(this.element.find('strong').text(), 'test');
  });

  it('should append a notification body', function () {
    ckan.notify('test', 'this is a message');
    assert.equal(this.element.find('span').text(), 'this is a message');
  });

  it('should escape all content', function () {
    ckan.notify('<script>', '<script>');
    assert.equal(this.element.find('strong').html(), '&lt;script&gt;');
    assert.equal(this.element.find('span').html(), '&lt;script&gt;');
  });

  it('should default the class to "alert-error"', function () {
    ckan.notify('test');
    assert.ok(this.element.find('.alert').hasClass('alert-error'));
  });

  it('should allow a type to be provided', function () {
    ckan.notify('test', '', 'info');
    assert.ok(this.element.find('.alert').hasClass('alert-info'));
  });

  it('should add itself to the ckan.sandbox()', function () {
    assert.equal(ckan.sandbox().notify, ckan.notify);
  });
});
