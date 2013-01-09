/*globals describe beforeEach afterEach it assert sinon ckan jQuery */
describe('ckan.module.ConfirmActionModule()', function () {
  var ConfirmActionModule = ckan.module.registry['confirm-action'];

  beforeEach(function () {
    jQuery.fn.modal = sinon.spy();

    this.el = document.createElement('button');
    this.sandbox = ckan.sandbox();
    this.sandbox.body = this.fixture;
    this.module = new ConfirmActionModule(this.el, {}, this.sandbox);
  });

  afterEach(function () {
    this.module.teardown();
  });

  describe('.initialize()', function () {
    it('should watch for clicks on the module element', function () {
      var target = sinon.stub(this.module.el, 'on');
      this.module.initialize();
      assert.called(target);
      assert.calledWith(target, 'click', this.module._onClick);
    });
  });

  describe('.confirm()', function () {
    it('should append the modal to the document body', function () {
      this.module.confirm();
      assert.equal(this.fixture.children().length, 1);
      assert.equal(this.fixture.find('.modal').length, 1);
    });

    it('should show the modal dialog', function () {
      this.module.confirm();
      assert.called(jQuery.fn.modal);
      assert.calledWith(jQuery.fn.modal, 'show');
    });
  });

  describe('.performAction()', function () {
    it('should submit the action');
  });

  describe('.createModal()', function () {
    it('should create the modal element', function () {
      var target = this.module.createModal();

      assert.ok(target.hasClass('modal'));
    });

    it('should set the module.modal property', function () {
      var target = this.module.createModal();

      assert.ok(target === this.module.modal);
    });

    it('should bind the success/cancel listeners', function () {
      var target = sinon.stub(jQuery.fn, 'on');

      this.module.createModal();

      // Not an ideal check as this implementation could be done in many ways.
      assert.calledTwice(target);
      assert.calledWith(target, 'click', '.btn-primary', this.module._onConfirmSuccess);
      assert.calledWith(target, 'click', '.btn-cancel', this.module._onConfirmCancel);

      target.restore();
    });

    it('should initialise the modal plugin', function () {
      this.module.createModal();
      assert.called(jQuery.fn.modal);
      assert.calledWith(jQuery.fn.modal, {show: false});
    });

    it('should insert the localized strings', function () {
      var target = this.module.createModal();
      var i18n = this.module.options.i18n;

      assert.equal(target.find('h3').text(), i18n.heading.fetch());
      assert.equal(target.find('.modal-body').text(), i18n.content.fetch());
      assert.equal(target.find('.btn-primary').text(), i18n.confirm.fetch());
      assert.equal(target.find('.btn-cancel').text(), i18n.cancel.fetch());
    });
  });

  describe('._onClick()', function () {
    it('should prevent the default action', function () {
      var target = {preventDefault: sinon.spy()};
      this.module._onClick(target);

      assert.called(target.preventDefault);
    });

    it('should display the confirmation dialog', function () {
      var target = sinon.stub(this.module, 'confirm');
      this.module._onClick({preventDefault: sinon.spy()});
      assert.called(target);
    });
  });

  describe('._onConfirmSuccess()', function () {
    it('should perform the action', function () {
      var target = sinon.stub(this.module, 'performAction');
      this.module._onConfirmSuccess(jQuery.Event('click'));
      assert.called(target);
    });
  });

  describe('._onConfirmCancel()', function () {
    it('should hide the modal', function () {
      this.module.modal = jQuery('<div/>');
      this.module._onConfirmCancel(jQuery.Event('click'));

      assert.called(jQuery.fn.modal);
      assert.calledWith(jQuery.fn.modal, 'hide');
    });
  });

});
