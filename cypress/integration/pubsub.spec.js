describe('ckan.pubsub', function () {
  before(() => {
    cy.visit('/');
  });

  beforeEach(function () {
    cy.window().then(win => {
      win.ckan.pubsub.events = win.jQuery({});
      win.ckan.pubsub.queue = [];
    })
  });

  describe('.enqueue()', function () {
    beforeEach(function () {
      this.target = cy.spy();
    });

    it('should defer callbacks for published events until later', function () {
      cy.window().then(win => {
        win.ckan.pubsub.subscribe('change', this.target);
        win.ckan.pubsub.enqueue();
        win.ckan.pubsub.publish('change');

        expect(this.target).to.not.be.called;
      })
    });

    it('should add the published calls to the .queue', function () {
      cy.window().then(win => {
        let queue = win.ckan.pubsub.queue;

        win.ckan.pubsub.enqueue();

        win.ckan.pubsub.publish('change');
        assert.equal(queue.length, 1);

        win.ckan.pubsub.publish('change');
        assert.equal(queue.length, 2);

        win.ckan.pubsub.publish('change');
        assert.equal(queue.length, 3);
      })
    });
  });

  describe('.dequeue()', function () {
    beforeEach(function () {
      cy.window().then(win => {
        win.ckan.pubsub.queue = [
          ['change'],
          ['change', 'arg1', 'arg2'],
          ['update', 'arg1']
        ];

        this.target1 = cy.spy();
        this.target2 = cy.spy();
        this.target3 = cy.spy();

        win.ckan.pubsub.subscribe('change', this.target1);
        win.ckan.pubsub.subscribe('change', this.target2);
        win.ckan.pubsub.subscribe('update', this.target3);
      })
    });

    it('should publish all queued callbacks', function () {
      cy.window().then(win => {
        win.ckan.pubsub.dequeue();

        expect(this.target1).to.be.calledTwice;
        expect(this.target1).to.be.calledWith( 'arg1', 'arg2');

        expect(this.target2).to.be.calledTwice;
        expect(this.target2).to.be.calledWith('arg1', 'arg2');

        expect(this.target3).to.be.called;
      })
    });

    it('should set the queue to null to allow new events to be published', function () {
      cy.window().then(win => {
        win.ckan.pubsub.dequeue();
        assert.isNull(win.ckan.pubsub.queue);
      })
    });

    it('should not block new events from being published', function () {
      cy.window().then(win => {
        let pubsub = win.ckan.pubsub;

        let second = cy.spy();
        let third = cy.spy();

        pubsub.enqueue();
        pubsub.subscribe('first', function () {
          pubsub.publish('third');
        });
        pubsub.subscribe('second', second);
        pubsub.subscribe('third', third);

        pubsub.publish('first');
        pubsub.publish('second');

        pubsub.dequeue();

        expect(second).to.be.called;
        expect(third).to.be.called;
      })
    });
  });
});
