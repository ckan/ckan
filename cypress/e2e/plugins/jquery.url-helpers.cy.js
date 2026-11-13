describe('jQuery.url', {testIsolation: false}, function () {
  before(function () {
    cy.visit('/')
  });

  describe('.escape()', {testIsolation: false}, function () {
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

  describe('.slugify()', {testIsolation: false}, function () {
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

    it('should normalise hyphens', function () {
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

    it('should produce the same slug for precomposed and decomposed Nordic characters', function () {
      cy.window().then(win => {
        // Precomposed å (U+00E5) vs "a" + combining ring (U+030A), as in some pasted text.
        let precomposed = win.jQuery.url.slugify('\u00E5sele');
        let decomposed = win.jQuery.url.slugify('\u0061\u030Asele');

        assert.equal(precomposed, 'asele');
        assert.equal(decomposed, 'asele');
        assert.equal(precomposed, decomposed);
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
