describe('ckan.module.BasicFormModule()', function () {
  before(() => {
    cy.visit('/');
    cy.window().then(win => {
      cy.wrap(win.ckan.module.registry['basic-form']).as('BasicFormModule');
      win.jQuery('<div id="fixture">').appendTo(win.document.body)
    })
  });

  beforeEach(function () {
    cy.window().then(win => {
      cy.stub(win.jQuery.fn, 'incompleteFormWarning');

      this.el = document.createElement('form');
      this.el.innerHTML = '<button name="save" type="submit">Save</button>'
      this.sandbox = win.ckan.sandbox();
      this.sandbox.body = win.jQuery('#fixture');
      this.sandbox.body.append(this.el)
      this.module = new this.BasicFormModule(this.el, {}, this.sandbox);
    })
  });

  afterEach(function () {
    this.module.teardown();
  });

  describe('.initialize()', function () {
    it('should attach the jQuery.fn.incompleteFormWarning() to the form', function () {
      cy.window().then(win => {
        this.module.initialize();
        expect(win.jQuery.fn.incompleteFormWarning).called;
      })
    });

    it('should disable the submit button on form submit', function(done) {
      this.module.initialize();
      this.module._onSubmit();

      setTimeout(function() {
        var buttonAttrDisabled = this.el.querySelector('button').getAttribute('disabled');

        assert.ok(buttonAttrDisabled === 'disabled')
        done();
      }.bind(this), 0);
    });
  });
});
