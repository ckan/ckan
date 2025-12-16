describe('ckan.module.ConfirmActionModule()', { testIsolation: false }, function () {
  before(() => {
    cy.visit('/');
    cy.window().then(win => {
      cy.wrap(win.ckan.module.registry['confirm-action']).as('ConfirmActionModule');
      win.jQuery('<div id="fixture">').appendTo(win.document.body);
    });
  });

  beforeEach(function () {
    cy.window().then(win => {
      cy.stub(win.ckan, 'confirm').as('ckanConfirm');

      this.el = win.jQuery('<button>'); // jQuery element so `.on()` works
      this.sandbox = win.ckan.sandbox();
      this.sandbox.body = win.jQuery('#fixture');

      this.module = new this.ConfirmActionModule(this.el, {}, this.sandbox);
    });
  });

  afterEach(function () {
    this.module.teardown();

    cy.get('@ckanConfirm').then(stub => stub.restore());
  });

  describe('.initialize()', function () {
    it('should bind click event to module element', function () {
      const spy = cy.spy(this.module.el, 'on');
      this.module.initialize();
      expect(spy).to.be.calledWith('click', this.module._onClick);
    });
  });

  describe('._onClick()', function () {
    it('should prevent default and call ckan.confirm()', function () {
      const fakeEvent = { preventDefault: cy.spy() };

      cy.window().then(win => {
        const performStub = cy.stub(this.module, 'performAction');

        // Trigger the click handler
        this.module._onClick(fakeEvent);

        expect(fakeEvent.preventDefault).to.be.called;

        cy.get('@ckanConfirm').then(ckanConfirm => {
          expect(ckanConfirm).to.be.calledOnce;

          const args = ckanConfirm.getCall(0).args[0];

          expect(args).to.have.property('message');

          // Simulate confirm callback
          args.onConfirm();
          expect(performStub).to.be.called;
        });
      });
    });
  });

  describe('.performAction()', function () {
    it('should trigger HTMX if hx-post/hx-get is present', function () {
      cy.window().then(win => {
        const form = win.jQuery('<form hx-post="/doit">').appendTo('body');
        this.el = win.jQuery('<button>').appendTo(form)[0];
        this.module = new this.ConfirmActionModule(this.el, {}, this.sandbox);

        cy.stub(win.htmx, 'trigger').as('htmxTrigger');
        this.module.performAction();

        cy.get('@htmxTrigger').should('be.calledWith', form[0], 'submit');
      });
    });

    it('should create and submit a form if no hx-post and withData is false', function () {
      cy.window().then(win => {
        const href = '/delete';
        this.el = win.jQuery(`<a href="${href}">`).appendTo('body')[0];
        this.module = new this.ConfirmActionModule(this.el, { withData: false }, this.sandbox);

        const stub = cy.stub(win.jQuery.fn, 'submit');
        this.module.performAction();

        expect(stub).to.be.called;
        stub.restore();
      });
    });
  });
});
