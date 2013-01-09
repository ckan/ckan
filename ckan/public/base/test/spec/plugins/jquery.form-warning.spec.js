describe('jQuery.incompleteFormWarning()', function () {
  beforeEach(function () {
    this.el = jQuery('<form />').appendTo(this.fixture);
    this.el.on('submit', false);

    this.input1 = jQuery('<input name="input1" value="a" />').appendTo(this.el);
    this.input2 = jQuery('<input name="input2" value="b" />').appendTo(this.el);

    this.el.incompleteFormWarning('my message');

    this.on = sinon.stub(jQuery.fn, 'on');
    this.off = sinon.stub(jQuery.fn, 'off');
  });

  afterEach(function () {
    this.on.restore();
    this.off.restore();
  });

  it('should bind a beforeunload event when the form changes', function () {
    this.input1.val('c');
    this.el.change();

    assert.called(this.on);
  });

  it('should unbind a beforeunload event when a form returns to the original state', function () {
    this.input1.val('c');
    this.el.change();

    this.input1.val('a');
    this.el.change();

    assert.called(this.off); 
  });

  it('should unbind the beforeunload event when the form is submitted', function () {
    this.el.submit();

    assert.called(this.off); 
  });
});
