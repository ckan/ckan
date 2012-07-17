/*globals describe beforeEach afterEach it assert sinon ckan jQuery */
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
      function success() {}
      function error() {}

      var target = this.client.getStorageAuth('filename', success, error);

      assert.called(jQuery.ajax);
      assert.calledWith(jQuery.ajax, {
        url: '/api/storage/auth/form/filename',
        success: success,
        error: error
      });
    });
  });

  describe('.getStorageMetadata()', function () {
    beforeEach(function () {
      this.fakePromise = sinon.mock(jQuery.Deferred());
      sinon.stub(jQuery, 'ajax').returns(this.fakePromise);
    });

    afterEach(function () {
      jQuery.ajax.restore();
    });

    it('should return a jQuery promise', function () {
      var target = this.client.getStorageMetadata('filename');
      assert.equal(target, this.fakePromise);
    });

    it('should call request a new auth token', function () {
      function success() {}
      function error() {}

      var target = this.client.getStorageMetadata('filename', success, error);

      assert.called(jQuery.ajax);
      assert.calledWith(jQuery.ajax, {
        url: '/api/storage/metadata/filename',
        success: success,
        error: error
      });
    });

    it('should throw an error if no filename is provided', function () {
      var client = this.client;
      assert.throws(function () {
        client.getStorageMetadata();
      });
    });
  });

  describe('.convertStorageMetadataToResource(meta)', function () {
    beforeEach(function () {
      this.meta = {
        "_checksum": "md5:527c97d2aa3ed1b40aea4b7ddf98692e",
        "_content_length": 122632,
        "_creation_date": "2012-07-17T14:35:35",
        "_label": "2012-07-17T13:35:35.540Z/cat.jpg",
        "_last_modified": "2012-07-17T14:35:35",
        "_location": "http://example.com/storage/f/2012-07-17T13%3A35%3A35.540Z/cat.jpg",
        "filename-original": "cat.jpg",
        "key": "2012-07-17T13:35:35.540Z/cat.jpg",
        "uploaded-by": "user"
      };
    });

    it('should return a representation for a resource', function () {
      var target = this.client.convertStorageMetadataToResource(this.meta);

      assert.deepEqual(target, {
        url: 'http://example.com/storage/f/2012-07-17T13%3A35%3A35.540Z/cat.jpg',
        key: '2012-07-17T13:35:35.540Z/cat.jpg',
        name: 'cat.jpg',
        size: 122632,
        created: "2012-07-17T14:35:35",
        last_modified: "2012-07-17T14:35:35",
        format: 'jpg',
        mimetype: null,
        resource_type: 'file.upload', // Is this standard?
        owner: 'user',
        hash: 'md5:527c97d2aa3ed1b40aea4b7ddf98692e',
        cache_url: 'http://example.com/storage/f/2012-07-17T13%3A35%3A35.540Z/cat.jpg',
        cache_url_updated: '2012-07-17T14:35:35'
      });
    });

    it('should provide a full url', function () {
      ckan.SITE_ROOT = 'http://example.com';

      this.meta._location = "/storage/f/2012-07-17T13%3A35%3A35.540Z/cat.jpg";
      var target = this.client.convertStorageMetadataToResource(this.meta);
      assert.equal(target.url, 'http://example.com/storage/f/2012-07-17T13%3A35%3A35.540Z/cat.jpg');
    });

    it('should not include microseconds or timezone in timestamps', function () {
      ckan.SITE_ROOT = 'http://example.com';

      var target = this.client.convertStorageMetadataToResource(this.meta);
      assert.ok(!(/\.\d\d\d/).test(target.last_modified), 'no microseconds');
      assert.ok(!(/((\+|\-)\d{4}|Z)$/).test(target.last_modified), 'no timezone');
    });

    it('should use the mime type for the format if found', function () {
      this.meta._format = 'image/jpeg';
      var target = this.client.convertStorageMetadataToResource(this.meta);

      assert.equal(target.format, 'image/jpeg', 'format');
      assert.equal(target.mimetype, 'image/jpeg', 'mimetype');
    });
  });
});
