describe('ckan.notify()', function () {
  before(() => {
    cy.visit('/');
    cy.window().then(win => {
      win.jQuery('<div id="fixture">').appendTo(win.document.body)
    })
  });

  beforeEach(function () {
    cy.window().then(win => {
      this.element = win.jQuery('<div />');
      win.jQuery('#fixture').append(this.element);

      win.ckan.notify.el = this.element;
    });

  });

  it('should append a notification to the element', function () {
    cy.window().then(win => {
      win.ckan.notify('test');
      assert.equal(this.element.children().length, 1, 'should be one child');
      win.ckan.notify('test');
      assert.equal(this.element.children().length, 2, 'should be two children');
    })
  });

  it('should append a notification title', function () {
    cy.window().then(win => {
      win.ckan.notify('test');
      assert.equal(this.element.find('strong').text(), 'test');
    })
  });

  it('should append a notification body', function () {
    cy.window().then(win => {
      win.ckan.notify('test', 'this is a message');
      assert.equal(this.element.find('span').text(), 'this is a message');
    })
  });

  it('should escape all content', function () {
    cy.window().then(win => {
      win.ckan.notify('<script>', '<script>');
      assert.equal(this.element.find('strong').html(), '&lt;script&gt;');
      assert.equal(this.element.find('span').html(), '&lt;script&gt;');
    })
  });

  it('should default the class to "alert-error"', function () {
    cy.window().then(win => {
      win.ckan.notify('test');
      assert.ok(this.element.find('.alert').hasClass('alert-error'));
    })
  });

  it('should allow a type to be provided', function () {
    cy.window().then(win => {
      win.ckan.notify('test', '', 'info');
      assert.ok(this.element.find('.alert').hasClass('alert-info'));
    })
  });

  it('should add itself to the ckan.sandbox()', function () {
    cy.window().then(win => {
      assert.equal(win.ckan.sandbox().notify, win.ckan.notify);
    })
  });
});
