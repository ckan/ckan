describe('jQuery.incompleteFormWarning()', function () {
  before(function() {
    cy.visit('/');
    cy.window().then(win => {
      win.jQuery('<div id="fixture">').appendTo(win.document.body)
    })
  });

  beforeEach(function () {
    cy.window().then(win => {
      this.el = win.jQuery('<form />').appendTo(win.jQuery('#fixture'));
      this.el.on('submit', false);

      this.input1 = win.jQuery('<input name="input1" value="a" />').appendTo(this.el);
      this.input2 = win.jQuery('<input name="input2" value="b" />').appendTo(this.el);

      this.el.incompleteFormWarning('my message');

      this.on = cy.stub(win.jQuery.fn, 'on');
      this.off = cy.stub(win.jQuery.fn, 'off');
    })
  });

  it('should bind a beforeunload event when the form changes', function () {
    this.input1.val('c');
    this.el.change();

    expect(this.on).to.be.called;
  });

  it('should unbind a beforeunload event when a form returns to the original state', function () {
    this.input1.val('c');
    this.el.change();

    this.input1.val('a');
    this.el.change();

    expect(this.off).to.be.called;
  });

  it('should unbind the beforeunload event when the form is submitted', function () {
    this.el.submit();

    expect(this.off).to.be.called;
  });
});
