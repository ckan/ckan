describe('jQuery.url', function () {
  before(function () {
    cy.visit('/')
  });

  describe('.escape()', function () {
    it('should escape special characters', function () {
      cy.window().then(win => {
        let target = win.jQuery.url.escape('&<>=?#/');
        assert.equal(target, '%26%3C%3E%3D%3F%23%2F');
      })
    });

    it('should convert spaces to + rather than %20', function () {
      cy.window().then(win => {
        let target = win.jQuery.url.escape(' ');
        assert.equal(target, '+');
      })
    });
  });

  describe('.slugify()', function () {
    it('should replace spaces with hyphens', function () {
      cy.window().then(win => {
        let target = win.jQuery.url.slugify('apples and pears');
        assert.equal(target, 'apples-and-pears');
      });
    });

    it('should lowecase all characters', function () {
      cy.window().then(win => {
        let target = win.jQuery.url.slugify('APPLES AND PEARS');
        assert.equal(target, 'apples-and-pears');
      });
    });

    it('should convert unknown characters to hyphens', function () {
      cy.window().then(win => {
        let target = win.jQuery.url.slugify('apples & pears');
        assert.equal(target, 'apples-pears');
      });
    });

    it('should nomalise hyphens', function () {
      cy.window().then(win => {
        let target = win.jQuery.url.slugify('apples---pears');
        assert.equal(target, 'apples-pears', 'remove duplicate hyphens');

        target = win.jQuery.url.slugify('--apples-pears');
        assert.equal(target, 'apples-pears', 'strip preceding hyphens');

        target = win.jQuery.url.slugify('apples-pears--');
        assert.equal(target, 'apples-pears', 'strip trailing hyphens');
      });
    });

    it('should try and asciify unicode characters', function () {
      cy.window().then(win => {
        let target = win.jQuery.url.slugify('éåøç');
        assert.equal(target, 'eaoc');
      })
    });

    it('should allow underscore characters', function() {
      cy.window().then(win => {
        let target = win.jQuery.url.slugify('apples_pears');
        assert.equal(target, 'apples_pears');
      });
    });
  });
});
