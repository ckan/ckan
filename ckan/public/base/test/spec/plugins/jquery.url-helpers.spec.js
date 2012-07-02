describe('jQuery.url', function () {
  describe('jQuery.url.escape', function () {
    it('should escape special characters', function () {
      var target = jQuery.url.escape('&<>=?#/');
      assert.equal(target, '%26%3C%3E%3D%3F%23%2F');
    });

    it('should convert spaces to + rather than %20', function () {
      var target = jQuery.url.escape(' ');
      assert.equal(target, '+');
    });
  });
});
