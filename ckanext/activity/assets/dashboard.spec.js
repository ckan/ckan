describe('ckan.modules.DashboardModule()', function () {
  before(() => {
    cy.visit('/');
    cy.window().then(win => {
      cy.wrap(win.ckan.module.registry['dashboard']).as('dashboard');
      win.jQuery('<div id="fixture">').appendTo(win.document.body)
      cy.loadFixture('dashboard.html').then((template) => {
        cy.wrap(template).as('template');
      });
    })
  });

  beforeEach(function () {
    cy.window().then(win => {
      win.jQuery('#fixture').html(this.template);
      this.el = document.createElement('button');
      this.sandbox = win.ckan.sandbox();
      this.sandbox.body = win.jQuery('#fixture');
      cy.wrap(this.sandbox.body).as('fixture');
      this.module = new this.dashboard(this.el, {}, this.sandbox);
    })
  });

  afterEach(function () {
    //this.fixture.empty();
  });

  describe('.initialize()', function () {
    it('should bind callback methods to the module', function () {
      cy.window().then(win => {
        let target = cy.stub(win.jQuery, 'proxyAll');

        this.module.initialize();

        expect(target).to.be.called;
        expect(target).to.be.calledWith(this.module, /_on/);

        target.restore();
      })
    })
  })

  describe('.show()', function () {
    it('should append the popover to the document body', function () {
      this.module.initialize();
      this.module.button.click();
      assert.equal(this.fixture.children().length, 1);
      assert.equal(this.fixture.find('#followee-filter').length, 1);
      assert.equal(this.fixture.find('#followee-filter .input-group input').length, 1);
    });
  })

  describe(".search", function(){
    it('should filter based on query', function() {
      this.module.initialize();
      this.module.button.click();
      cy.get('#fixture #followee-filter #followee-content').invoke('removeAttr', 'style');
      cy.get('#fixture #followee-filter .nav li').should('have.length', 3);
      cy.get('#fixture #followee-filter .input-group input.inited').type('text');
      cy.get('#fixture #followee-filter .nav li[data-search="not valid"]').should('be.visible');
      cy.get('#fixture #followee-filter .nav li[data-search="test followee"]').should('be.visible');
    })
  })
})
