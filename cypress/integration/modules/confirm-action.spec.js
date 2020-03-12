describe('ckan.module.ConfirmActionModule()', function () {
  before(() => {
    cy.visit('/');
    cy.window().then(win => {
      cy.wrap(win.ckan.module.registry['confirm-action']).as('ConfirmActionModule');
      win.jQuery('<div id="fixture">').appendTo(win.document.body)
    })
  });

  beforeEach(function () {
    cy.window().then(win => {
      win.jQuery.fn.modal = cy.spy();

      this.el = document.createElement('button');
      this.sandbox = win.ckan.sandbox();
      this.sandbox.body = win.jQuery('#fixture');
      cy.wrap(this.sandbox.body).as('fixture');
      this.module = new this.ConfirmActionModule(this.el, {}, this.sandbox);
    })
  });

  afterEach(function () {
    this.module.teardown();
  });

  describe('.initialize()', function () {
    it('should watch for clicks on the module element', function () {
      let target = cy.stub(this.module.el, 'on');
      this.module.initialize();
      expect(target).to.be.called;
      expect(target).to.be.calledWith('click', this.module._onClick);
    });
  });

  describe('.confirm()', function () {
    it('should append the modal to the document body', function () {
      this.module.confirm();
      assert.equal(this.fixture.children().length, 1);
      assert.equal(this.fixture.find('.modal').length, 1);
    });

    it('should show the modal dialog', function () {
      cy.window().then(win => {
        this.module.confirm();
        expect(win.jQuery.fn.modal).to.be.called;
        expect(win.jQuery.fn.modal).to.be.calledWith('show');
      })
    });
  });

  describe('.performAction()', function () {
    it('should submit the action');
  });

  describe('.createModal()', function () {
    it('should create the modal element', function () {
      let target = this.module.createModal();

      assert.ok(target.hasClass('modal'));
    });

    it('should set the module.modal property', function () {
      let target = this.module.createModal();

      assert.ok(target === this.module.modal);
    });

    it('should bind the success/cancel listeners', function () {
      cy.window().then(win => {
        let target = cy.stub(win.jQuery.fn, 'on');

        this.module.createModal();

        // Not an ideal check as this implementation could be done in many ways.
        expect(target).to.be.calledTwice;
        expect(target).to.be.calledWith('click', '.btn-primary', this.module._onConfirmSuccess);
        expect(target).to.be.calledWith('click', '.btn-cancel', this.module._onConfirmCancel);

        target.restore();
      })
    });

    it('should initialise the modal plugin', function () {
      cy.window().then(win => {
        this.module.createModal();
        expect(win.jQuery.fn.modal).to.be.called;
        expect(win.jQuery.fn.modal).to.be.calledWith({show: false});
      })
    });

    it('should allow to customize the content', function () {
      this.module.options.content = 'some custom content';
      let target = this.module.createModal();

      assert.equal(target.find('.modal-body').text(), 'some custom content');
    });
  });

  describe('._onClick()', function () {
    it('should prevent the default action', function () {
      let target = {preventDefault: cy.spy()};
      this.module._onClick(target);

      expect(target.preventDefault).to.be.called;
    });

    it('should display the confirmation dialog', function () {
      let target = cy.stub(this.module, 'confirm');
      this.module._onClick({preventDefault: cy.spy()});
      expect(target).to.be.called;
    });
  });

  describe('._onConfirmSuccess()', function () {
    it('should perform the action', function () {
      cy.window().then(win => {
        let target = cy.stub(this.module, 'performAction');
        this.module._onConfirmSuccess(win.jQuery.Event('click'));
        expect(target).to.be.called;
      })
    });
  });

  describe('._onConfirmCancel()', function () {
    it('should hide the modal', function () {
      cy.window().then(win => {
        this.module.modal = win.jQuery('<div/>');
        this.module._onConfirmCancel(win.jQuery.Event('click'));

        expect(win.jQuery.fn.modal).to.be.called;
        expect(win.jQuery.fn.modal).to.be.calledWith( 'hide');
      })
    });
  });

});
