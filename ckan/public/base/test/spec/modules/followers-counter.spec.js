/*globals describe beforeEach afterEach it assert sinon ckan jQuery */
describe('ckan.module.FollowersCounterModule()', function() {
  var FollowersCounterModule = ckan.module.registry['followers-counter'];

  beforeEach(function() {
    this.initialCounter = 10;
    this.el = jQuery('<dd><span>' + this.initialCounter + '</span></dd>');
    this.sandbox = ckan.sandbox();
    this.module = new FollowersCounterModule(this.el, {}, this.sandbox);
  });

  afterEach(function() {
    this.module.teardown();
  });

  describe('.initialize()', function() {
    it('should bind callback methods to the module', function() {
      var target = sinon.stub(jQuery, 'proxyAll');

      this.module.initialize();

      assert.called(target);
      assert.calledWith(target, this.module, /_on/);

      target.restore();
    });

    it('should set this.counterVal to the current counter value in the DOM converted to number', function() {
      this.module.initialize();

      assert.equal(this.module.counterVal, this.initialCounter);
    });

    it('should set this.objId to the one on this.options.id', function() {
      this.module.options = {id: 'some-id'};
      this.module.initialize();

      assert.equal(this.module.objId, this.module.options.id);
    });

    it('should subscribe to the "follow-follow-some-id" event', function() {
      var target = sinon.stub(this.sandbox, 'subscribe');

      this.module.options = {id: 'some-id'};
      this.module.initialize();

      assert.called(target);
      assert.calledWith(target, 'follow-follow-some-id', this.module._onFollow);

      target.restore();
    });

    it('should subscribe to the "follow-unfollow-some-id" event', function() {
      var target = sinon.stub(this.sandbox, 'subscribe');

      this.module.options = {id: 'some-id'};
      this.module.initialize();

      assert.called(target);
      assert.calledWith(target, 'follow-unfollow-some-id', this.module._onUnfollow);

      target.restore();
    });
  });

  describe('.teardown()', function() {
    it('should unsubscribe to the "follow-follow-some-id" event', function() {
      var target = sinon.stub(this.sandbox, 'unsubscribe');

      this.module.options = {id: 'some-id'};
      this.module.initialize();
      this.module.teardown();

      assert.called(target);
      assert.calledWith(target, 'follow-follow-some-id', this.module._onFollow);

      target.restore();
    });

    it('should unsubscribe to the "follow-unfollow-some-id" event', function() {
      var target = sinon.stub(this.sandbox, 'unsubscribe');

      this.module.options = {id: 'some-id'};
      this.module.initialize();
      this.module.teardown();

      assert.called(target);
      assert.calledWith(target, 'follow-unfollow-some-id', this.module._onUnfollow);

      target.restore();
    });
  });

  describe('._onFollow', function() {
    it('should call _onFollow on "follow-follow-some-id" event', function() {
      var target = sinon.stub(this.module, '_onFollow');

      this.module.options = {id: 'some-id'};
      this.module.initialize();

      this.sandbox.publish('follow-follow-some-id');

      assert.called(target);
    });

    it('should increment this.counterVal on calling _onFollow', function() {
      this.module.initialize();
      this.module._onFollow();

      assert.equal(this.module.counterVal, ++this.initialCounter);
    });

    it('should increment the counter value in the DOM on calling _onFollow', function() {
      var counterVal;

      this.module.initialize();
      this.module._onFollow();

      counterVal = this.module.counterEl.text();
      counterVal = parseInt(counterVal, 10);

      assert.equal(counterVal, ++this.initialCounter);
    });
  });

  describe('._onUnfollow', function() {
    it('should call _onUnfollow on "follow-unfollow-some-id" event', function() {
      var target = sinon.stub(this.module, '_onUnfollow');

      this.module.options = {id: 'some-id'};
      this.module.initialize();

      this.sandbox.publish('follow-unfollow-some-id');

      assert.called(target);
    });

    it('should decrement this.counterVal on calling _onUnfollow', function() {
      this.module.initialize();
      this.module._onUnfollow();

      assert.equal(this.module.counterVal, --this.initialCounter);
    });

    it('should decrement the counter value in the DOM on calling _onUnfollow', function() {
      var counterVal;

      this.module.initialize();
      this.module._onUnfollow();

      counterVal = this.module.counterEl.text();
      counterVal = parseInt(counterVal, 10);

      assert.equal(counterVal, --this.initialCounter);
    });
  });
});
