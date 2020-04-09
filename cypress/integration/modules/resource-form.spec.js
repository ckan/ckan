/*globals describe beforeEach afterEach it assert sinon ckan jQuery */
describe('ckan.modules.ResourceFormModule()', function () {
  before(() => {
    cy.visit('/');
    cy.window().then(win => {
      cy.wrap(win.ckan.module.registry['resource-form']).as('ResourceFormModule');
    });
  });

  beforeEach(function () {
    cy.window().then(win => {
      this.el = document.createElement('form');
      this.sandbox = win.ckan.sandbox();
      this.module = new this.ResourceFormModule(this.el, {}, this.sandbox);
    })
  });


  describe('.initialize()', function () {
    it('should subscribe to the "resource:uploaded" event', function () {
      let target = cy.stub(this.sandbox, 'subscribe');

      this.module.initialize();

      expect(target).to.be.called;
      expect(target).to.be.calledWith('resource:uploaded', this.module._onResourceUploaded);

      target.restore();
    });
  });

  describe('.teardown()', function () {
    it('should unsubscribe from the "resource:uploaded" event', function () {
      let target = cy.stub(this.sandbox, 'unsubscribe');

      this.module.teardown();

      expect(target).to.be.called;
      expect(target).to.be.calledWith('resource:uploaded', this.module._onResourceUploaded);

      target.restore();
    });
  });

  describe('._onResourceUploaded()', function () {
    beforeEach(function () {
      this.module.el.html([
        '<input type="text" name="text" />',
        '<input type="checkbox" name="checkbox" value="check" />',
        '<input type="radio" name="radio" value="radio1" />',
        '<input type="radio" name="radio" value="radio2" />',
        '<input type="hidden" name="hidden" />',
        '<select name="select">',
        '<option value="option1" />',
        '<option value="option2" />',
        '</select>'
      ].join(''));

      this.resource = {
        text: 'text',
        checkbox: "check",
        radio: "radio2",
        hidden: "hidden",
        select: "option1"
      };
    });

    it('should set the values on appropriate fields', function () {
      cy.window().then(win => {
        let res = this.resource;

        this.module._onResourceUploaded(res);

        win.jQuery.each(this.module.el.serializeArray(), function (idx, field) {
          assert.equal(field.value, res[field.name]);
        });
      });
    });
  });
});
