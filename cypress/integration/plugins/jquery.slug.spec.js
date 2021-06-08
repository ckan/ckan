describe('jQuery.fn.slug()', function () {
  beforeEach(function () {
    cy.visit('/')
    cy.window().then(win => {
      this.input = win.jQuery('<input />').slug();
      win.jQuery('<div id="fixture">').appendTo(win.document.body)
      win.jQuery('#fixture').append(this.input);
    });
  });

  it('should slugify and append the pressed key', function () {
    cy.window().then(win => {
      let e = win.jQuery.Event('keypress', {charCode: 97 /* a */});
      this.input.trigger(e);

      assert.equal(this.input.val(), 'a', 'append an "a"');

      e = win.jQuery.Event('keypress', {charCode: 38 /* & */});
      this.input.trigger(e);

      assert.equal(this.input.val(), 'a-', 'append an "-"');
    });
  });

  it('should do nothing if a non character key is pressed', function () {
    cy.window().then(win => {
      let e = win.jQuery.Event('keypress', {charCode: 0});
      this.input.val('some other string').trigger(e);

      assert.equal(this.input.val(), 'some other string');
    })
  });

  it('should slugify the input contents on "blur" and "change" events', function () {
    cy.window().then(win => {
      this.input.val('apples & pears').trigger(win.jQuery.Event('blur'));
      assert.equal(this.input.val(), 'apples-pears', 'on blur');

      this.input.val('apples & pears').trigger(win.jQuery.Event('change'));
      assert.equal(this.input.val(), 'apples-pears', 'on change');
    });
  });
});
