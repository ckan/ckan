describe('ckan.toast()', { testIsolation: false }, function () {

  before(() => {
    cy.visit('/');
  });

  beforeEach(function () {
    cy.window().then(win => {
      // Remove any existing toast containers for clean state
      win.document.querySelectorAll('.toast-container').forEach(el => el.parentNode.remove());
    });
  });

  it('should display a toast with required message', function () {
    cy.window().then(win => {
      win.ckan.toast({ message: 'Test Toast Message' });
      const toastEl = win.document.querySelector('.toast');
      expect(toastEl).to.exist;
      expect(toastEl.querySelector('.toast-body').textContent).to.include('Test Toast Message');
    });
  });

  it('should apply correct style class based on type', function () {
    cy.window().then(win => {
      win.ckan.toast({ message: 'Success Toast', type: 'success' });
      const header = win.document.querySelector('.toast-header');
      expect(header.classList.contains('bg-success')).to.be.true;
    });
  });

  it('should display title, subtitle and icon when provided', function () {
    cy.window().then(win => {
      win.ckan.toast({
        message: 'Body Content',
        title: 'Toast Title',
        subtitle: 'Now',
        icon: '<i class="test-icon"></i>'
      });

      const toastEl = win.document.querySelector('.toast');
      expect(toastEl.querySelector('strong').textContent).to.include('Toast Title');
      expect(toastEl.querySelector('small').textContent).to.include('Now');
      expect(toastEl.querySelector('.test-icon')).to.exist;
    });
  });

  it('should position the toast in the correct container', function () {
    cy.window().then(win => {
      win.ckan.toast({ message: 'Position Test', position: 'top-center' });
      const container = win.document.getElementById('toast-container-top-center');
      expect(container).to.exist;
      expect(container.querySelector('.toast')).to.exist;
    });
  });

  it('should remove existing toasts when stacking is disabled', function () {
    cy.window().then(win => {
      win.ckan.toast({ message: 'First Toast', stacking: false });
      win.ckan.toast({ message: 'Second Toast', stacking: false });
      const container = win.document.querySelector('.toast-container');
      expect(container.querySelectorAll('.toast').length).to.equal(1);
    });
  });

  it('should add a progress bar if showProgress is true', function () {
    cy.window().then(win => {
      win.ckan.toast({ message: 'Progress Toast', showProgress: true, delay: 5000 });
      const progressBar = win.document.querySelector('.progress-bar-timer');
      expect(progressBar).to.exist;
      expect(progressBar.style.animation).to.include('reverseProgress');
    });
  });

  it('shouldn\'t add a progress bar if showProgress is false', function () {
    cy.window().then(win => {
      win.ckan.toast({ message: 'Progress Toast', showProgress: false, delay: 5000 });
      cy.get('.progress-bar-timer').should('not.exist');
    });
  });

  it('shouldn\'t add a progress bar if delay is 0', function () {
    cy.window().then(win => {
      win.ckan.toast({ message: 'Progress Toast', delay: 0 });
      cy.get('.progress-bar-timer').should('not.exist');
    });
  });

  it('should add itself to the ckan.sandbox()', function () {
    cy.window().then(win => {
      expect(win.ckan.sandbox().toast).to.equal(win.ckan.toast);
    });
  });

  it('should not create a toast if message is missing', function () {
    cy.window().then(win => {
      cy.spy(win.console, 'error').as('consoleError');
      win.ckan.toast({});
    });

    cy.get('@consoleError').should('have.been.calledWithMatch', /Missing required 'message' option/);
  });
});
