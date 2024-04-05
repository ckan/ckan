describe('jQuery.date', function () {
  beforeEach(function () {
    this.now = new Date();
    this.now.setTime(0);

    cy.clock(this.now.getTime());
    cy.visit('/')
  });


  describe('jQuery.date.format()', function () {
    it('should format the date based on the string provided', function () {
      cy.window().then(win => {
        let target = win.jQuery.date.format('yyyy-MM-dd', this.now);
        assert.equal(target, '1970-01-01');
      })
    });

    it('should use the current time if none provided', function () {
      cy.window().then(win => {
        let target = win.jQuery.date.format('yyyy/MM/dd');
        assert.equal(target, '1970/01/01');
      })
    });
  });

  describe('jQuery.date.toISOString()', function () {
    it('should output an ISO8601 compatible string', function () {
      cy.window().then(win => {
        let target = win.jQuery.date.toISOString(this.now);
        assert.equal(target, '1970-01-01T00:00:00.000Z');
      })
    });

    it('should use the current time if none provided', function () {
      cy.window().then(win => {
        let target = win.jQuery.date.toISOString();
        assert.equal(target, '1970-01-01T00:00:00.000Z');
      });
    })
  });
});
