describe('ckan.module.FollowersCounterModule()', function() {
  before(() => {
    cy.visit('/');
    cy.window().then(win => {
      cy.wrap(win.ckan.module.registry['followers-counter']).as('FollowersCounterModule');
      win.jQuery('<div id="fixture">').appendTo(win.document.body)
    });
  });

  beforeEach(function() {
    cy.window().then(win => {
      let initialCounter = 10;
      this.el = win.jQuery('<dd><span>' + initialCounter + '</span></dd>');
      this.sandbox = win.ckan.sandbox();
      this.module = new this.FollowersCounterModule(this.el, {}, this.sandbox);
      this.module.options.num_followers = initialCounter;
    })
  });

  afterEach(function() {
    this.module.teardown();
  });

  describe('.initialize()', function() {
    it('should bind callback methods to the module', function() {
      cy.window().then(win => {
        let target = cy.stub(win.jQuery, 'proxyAll');

        this.module.initialize();

        expect(target).to.be.called;
        expect(target).to.be.calledWith(this.module, /_on/);

        target.restore();
      });
    });

    it('should subscribe to the "follow-follow-some-id" event', function() {
      let target = cy.stub(this.sandbox, 'subscribe');

      this.module.options = {id: 'some-id'};
      this.module.initialize();

      expect(target).to.be.called;
      expect(target).to.be.calledWith('follow-follow-some-id', this.module._onFollow);

      target.restore();
    });

    it('should subscribe to the "follow-unfollow-some-id" event', function() {
      let target = cy.stub(this.sandbox, 'subscribe');

      this.module.options = {id: 'some-id'};
      this.module.initialize();

      expect(target).to.be.called;
      expect(target).to.be.calledWith('follow-unfollow-some-id', this.module._onUnfollow);

      target.restore();
    });
  });

  describe('.teardown()', function() {
    it('should unsubscribe to the "follow-follow-some-id" event', function() {
      let target = cy.stub(this.sandbox, 'unsubscribe');

      this.module.options = {id: 'some-id'};
      this.module.initialize();
      this.module.teardown();

      expect(target).to.be.called;
      expect(target).to.be.calledWith('follow-follow-some-id', this.module._onFollow);

      target.restore();
    });

    it('should unsubscribe to the "follow-unfollow-some-id" event', function() {
      let target = cy.stub(this.sandbox, 'unsubscribe');

      this.module.options = {id: 'some-id'};
      this.module.initialize();
      this.module.teardown();

      expect(target).to.be.called;
      expect(target).to.be.calledWith('follow-unfollow-some-id', this.module._onUnfollow);

      target.restore();
    });
  });

  describe('._onFollow', function() {
    it('should call _onFollow on "follow-follow-some-id" event', function() {
      let target = cy.stub(this.module, '_onFollow');

      this.module.options = {id: 'some-id'};
      this.module.initialize();

      this.sandbox.publish('follow-follow-some-id');

      expect(target).to.be.called;
    });

    it('should call _updateCounter when ._onFollow is called', function() {
      let target = cy.stub(this.module, '_updateCounter');

      this.module.options = {id: 'some-id'};
      this.module.initialize();

      this.module._onFollow();

      expect(target).to.be.called;
      expect(target).to.be.calledWith({action: 'follow'});
    });
  });

  describe('._onUnfollow', function() {
    it('should call _onUnfollow on "follow-unfollow-some-id" event', function() {
      let target = cy.stub(this.module, '_onUnfollow');

      this.module.options = {id: 'some-id'};
      this.module.initialize();

      this.sandbox.publish('follow-unfollow-some-id');

      expect(target).to.be.called;
    });

    it('should call _updateCounter when ._onUnfollow is called', function() {
      let target = cy.stub(this.module, '_updateCounter');

      this.module.options = {id: 'some-id'};
      this.module.initialize();

      this.module._onUnfollow();

      expect(target).to.be.called;
      expect(target).to.be.calledWith({action: 'unfollow'});
    });
  });

  describe('._updateCounter', function() {
    it('should increment this.options.num_followers on calling _onFollow', function() {
      let initialCounter = 10;
      this.module.initialize();
      this.module._onFollow();
      assert.equal(this.module.options.num_followers, ++initialCounter);
    });

    it('should increment the counter value in the DOM on calling _onFollow', function() {
      let counterVal;
      let initialCounter = 10;
      this.module.initialize();
      this.module._onFollow();

      counterVal = this.module.counterEl.text();
      counterVal = parseInt(counterVal, 10);
      debugger
      assert.equal(counterVal, ++initialCounter);
    });

    it('should decrement this.options.num_followers on calling _onUnfollow', function() {
      let initialCounter = 10;
      this.module.initialize();
      this.module._onUnfollow();

      assert.equal(this.module.options.num_followers, --initialCounter);
    });

    it('should decrement the counter value in the DOM on calling _onUnfollow', function() {
      let initialCounter = 10;
      var counterVal;

      this.module.initialize();
      this.module._onUnfollow();

      counterVal = this.module.counterEl.text();
      counterVal = parseInt(counterVal, 10);

      assert.equal(counterVal, --initialCounter);
    });

    it('should not change the counter value in the DOM when the value is greater than 1000', function() {
      var beforeCounterVal = 1536;
      var afterCounterVal;

      this.module.options = {num_followers: beforeCounterVal};
      this.module.initialize();
      this.module.counterEl.text(this.module.options.num_followers);
      this.module._onFollow();

      afterCounterVal = this.module.counterEl.text();
      afterCounterVal = parseInt(afterCounterVal, 10);

      assert.equal(beforeCounterVal, afterCounterVal);
    });
  });
});
