describe('ckan.modules.ResourceUploadFieldModule()', function () {
  before(() => {
    cy.visit('/');
    cy.window().then(win => {
      cy.wrap(win.ckan.module.registry['resource-upload-field']).as('ResourceFileUploadModule');
    });
  });

  beforeEach(function () {
    cy.window().then(win => {
      win.jQuery.fn.fileupload = cy.spy();

      this.el = win.jQuery('<form />');
      this.sandbox = win.ckan.sandbox();
      this.module = new this.ResourceFileUploadModule(this.el, {}, this.sandbox);
      this.module.initialize();
    });
  });

  describe('.initialize()', function () {
    beforeEach(function () {
      this.module = new this.ResourceFileUploadModule(this.el, {}, this.sandbox);
    });

    it('should create the #upload field', function () {
      this.module.initialize();
      assert.ok(typeof this.module.upload === 'object');
    });

    it('should append the upload field to the module element', function () {
      cy.window().then(win => {
        this.module.initialize();

        assert.ok(win.jQuery.contains(this.el[0], this.module.upload[0]));
      })
    });

    it('should call .setupFileUpload()', function () {
      let target = cy.stub(this.module, 'setupFileUpload');

      this.module.initialize();

      expect(target).to.be.called;
    });
  });

  describe('.setupFileUpload()', function () {
    it('should set the label text on the form input', function () {
      this.module.initialize();
      this.module.setupFileUpload();

      assert.equal(this.module.upload.find('label').text(), 'Upload a file');
    });

    it('should setup the file upload with relevant options', function () {
      cy.window().then(win => {
        this.module.initialize();
        this.module.setupFileUpload();

        expect(win.jQuery.fn.fileupload).to.be.called;
        expect(win.jQuery.fn.fileupload).to.be.calledWith({
          type: 'POST',
          paramName: 'file',
          forceIframeTransport: true, // Required for XDomain request.
          replaceFileInput: true,
          autoUpload: false,
          add: this.module._onUploadAdd,
          send: this.module._onUploadSend,
          done: this.module._onUploadDone,
          fail: this.module._onUploadFail,
          always: this.module._onUploadComplete
        });
      });
    });
  });

  describe('.loading(show)', function () {
    it('should add a loading class to the upload element', function () {
      this.module.loading();

      assert.ok(this.module.upload.hasClass('loading'));
    });

    it('should remove the loading class if false is passed as an argument', function () {
      this.module.upload.addClass('loading');
      this.module.loading();

      assert.ok(!this.module.upload.hasClass('loading'));
    });
  });

  describe('.authenticate(key, data)', function () {
    beforeEach(function () {
      cy.window().then(win => {
        this.fakeThen = cy.spy();
        this.fakeProxy = cy.stub(win.jQuery, 'proxy').returns('onsuccess');

        this.target = cy.stub(this.sandbox.client, 'getStorageAuth');
        this.target.returns({
          then: this.fakeThen
        });
      });
    });

    it('should request authentication for the upload', function () {
      this.module.authenticate('test', {});
      expect(this.target).to.be.called;
      expect(this.target).to.be.calledWith('test');
    });

    it('should register success and error callbacks', function () {
      this.module.authenticate('test', {});
      expect(this.fakeThen).to.be.called;
      expect(this.fakeThen).to.be.calledWith( 'onsuccess', this.module._onAuthError);
    });

    it('should save the key on the data object', function () {
      var data = {};

      this.module.authenticate('test', data);

      assert.equal(data.key, 'test');
    });
  });

  describe('.lookupMetadata(key, data)', function () {
    beforeEach(function () {
      cy.window().then(win => {
        this.fakeThen = cy.spy();
        this.fakeProxy = cy.stub(win.jQuery, 'proxy').returns('onsuccess');

        this.target = cy.stub(this.sandbox.client, 'getStorageMetadata');
        this.target.returns({
          then: this.fakeThen
        });
      })
    });

    it('should request metadata for the upload key', function () {
      this.module.lookupMetadata('test', {});
      expect(this.target).to.be.called;
      expect(this.target).to.be.calledWith( 'test');
    });

    it('should register success and error callbacks', function () {
      this.module.lookupMetadata('test', {});
      expect(this.fakeThen).to.be.called;
      expect(this.fakeThen).to.be.calledWith( 'onsuccess', this.module._onMetadataError);
    });
  });

  describe('.notify(message, type)', function () {
    it('should call the sandbox.notify() method', function () {
      let target = cy.stub(this.sandbox, 'notify');

      this.module.notify('this is an example message', 'info');

      expect(target).to.be.called;
      expect(target).to.be.calledWith( 'An Error Occurred', 'this is an example message', 'info');
    });
  });

  describe('.generateKey(file)', function () {
    it('should generate a unique filename prefixed with a timestamp', function () {
      let now = new Date();
      cy.clock(now.getTime());
      cy.visit('/');
      cy.window().then(win => {
        let date = win.jQuery.date.toISOString(now);
        let target = this.module.generateKey('this is my file.png');

        assert.equal(target, date + '/this-is-my-file.png');

      });
    });
  });

  describe('._onUploadAdd(event, data)', function () {
    beforeEach(function () {
      this.target = cy.stub(this.module, 'authenticate');
      cy.stub(this.module, 'generateKey').returns('stubbed');
    });

    it('should authenticate the upload if a file is provided', function () {
      let data = {files: [{name: 'my_file.jpg'}]};
      this.module._onUploadAdd({}, data);

      expect(this.target).to.be.called;
      expect(this.target).to.be.calledWith('stubbed', data);
    });

    it('should not authenticate the upload if no file is provided', function () {
      let data = {files: []};
      this.module._onUploadAdd({}, data);

      expect(this.target).to.not.be.called;
    });
  });

  describe('._onUploadSend()', function () {
    it('should display the loading spinner', function () {
      let target = cy.stub(this.module, 'loading');
      this.module._onUploadSend({}, {});

      expect(target).to.be.called;
    });
  });

  describe('._onUploadDone()', function () {
    it('should request the metadata for the file', function () {
      let target = cy.stub(this.module, 'lookupMetadata');
      this.module._onUploadDone({}, {result: {}});

      expect(target).to.be.called;
    });

    it('should call the fail handler if the "result" key in the data is undefined', function () {
      let target = cy.stub(this.module, '_onUploadFail');
      this.module._onUploadDone({}, {result: undefined});

      expect(target).to.be.called;
    });

    it('should call the fail handler if the "result" object has an "error" key', function () {
      let target = cy.stub(this.module, '_onUploadFail');
      this.module._onUploadDone({}, {result: {error: 'failed'}});

      expect(target).to.be.called;
    });
  });

  describe('._onUploadComplete()', function () {
    it('should hide the loading spinner', function () {
      let target = cy.stub(this.module, 'loading');
      this.module._onUploadComplete({}, {});

      expect(target).to.be.called;
      expect(target).to.be.calledWith( false);
    });
  });

  describe('._onAuthSuccess()', function () {
    beforeEach(function () {
      this.target = {
        submit: cy.spy()
      };

      this.response = {
        action: 'action',
        fields: [{name: 'name', value: 'value'}]
      };
    });

    it('should set the data url', function () {
      this.module._onAuthSuccess(this.target, this.response);

      assert.equal(this.target.url, this.response.action);
    });

    it('should set the additional form data', function () {
      this.module._onAuthSuccess(this.target, this.response);

      assert.deepEqual(this.target.formData, this.response.fields);
    });

    it('should merge the form data with the options', function () {
      this.module.options.form.params = [{name: 'option', value: 'option'}];
      this.module._onAuthSuccess(this.target, this.response);

      assert.deepEqual(this.target.formData, [{name: 'option', value: 'option'}, {name: 'name', value: 'value'}]);
    });

    it('should call data.submit()', function () {
      this.module._onAuthSuccess(this.target, this.response);
      expect(this.target.submit).to.be.called;
    });
  });

  describe('._onMetadataSuccess()', function () {
    it('should publish the "resource:uploaded" event', function () {
      let resource = {url: 'http://', name: 'My File'};
      let target = cy.stub(this.sandbox, 'publish');

      cy.stub(this.sandbox.client, 'convertStorageMetadataToResource').returns(resource);

      this.module._onMetadataSuccess();

      expect(target).to.be.called;
      expect(target).to.be.calledWith( "resource:uploaded", resource);
    });
  });
});
