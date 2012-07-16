describe('ckan.Client()', function () {
  var Client = ckan.Client;

  beforeEach(function () {
    this.client = new Client();
  });

  it('should add a new instance to each client', function () {
    var target = ckan.sandbox().client;

    assert.instanceOf(target, Client);
  });

  describe('.getStorageAuth()', function () {
    beforeEach(function () {
      this.fakePromise = sinon.mock(jQuery.Deferred());
      sinon.stub(jQuery, 'ajax').returns(this.fakePromise);
    });

    afterEach(function () {
      jQuery.ajax.restore();
    });

    it('should return a jQuery promise', function () {
      var target = this.client.getStorageAuth('filename');
      assert.equal(target, this.fakePromise);
    });

    it('should call request a new auth token', function () {
      function success () {}
      function error() {}

      var target = this.client.getStorageAuth('filename', success, error);

      assert.called(jQuery.ajax);
      assert.calledWith(jQuery.ajax, {
        url: '/api/storage/auth/form/filename',
        success: success,
        error: error
      });
    });

    it('should throw an error if no filename is provided', function () {
      var client = this.client;
      assert.throws(function () {
        client.getStorageAuth();
      });
    });
  });
});
