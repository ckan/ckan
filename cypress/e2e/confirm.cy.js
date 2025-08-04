describe('ckan.confirm()', { testIsolation: false }, function () {

    before(() => {
        cy.visit('/');
    });

    beforeEach(function () {
        cy.window().then(win => {
            // Clean up existing modals or backdrops if left from previous tests
            win.document.querySelectorAll('.modal, .modal-backdrop').forEach(el => el.remove());
            win.document.body.classList.remove('modal-open');
        });
    });

    it('should create and show the confirmation modal', function () {
        cy.window().then(win => {
            win.ckan.confirm({
                message: 'Test confirmation',
                title: 'Test Title',
            });

            const modalSelector = '#ckan-confirm-modal';
            cy.get(modalSelector).should('exist');
            cy.get(modalSelector).should('be.visible');
            cy.get(modalSelector).contains('Test confirmation');
            cy.get(modalSelector).contains('Test Title');
        });
    });

    it('should trigger onConfirm callback when confirmed', function () {
        cy.window().then(win => {
            let confirmed = false;

            win.ckan.confirm({
                message: 'Confirm this action',
                onConfirm: () => { confirmed = true; }
            });

            cy.get('#ckan-confirm-yes').click().then(() => {
                expect(confirmed).to.be.true;
            });
        });
    });

    it('should trigger onCancel callback when cancelled via button', function () {
        cy.window().then(win => {
            let cancelled = false;

            win.ckan.confirm({
                message: 'Cancel this action',
                onCancel: () => { cancelled = true; }
            });

            cy.get('#ckan-confirm-cancel').click().then(() => {
                expect(cancelled).to.be.true;
            });
        });
    });

    it('should trigger onCancel callback when closed via close button', function () {
        cy.window().then(win => {
            let cancelled = false;

            win.ckan.confirm({
                message: 'Close the modal',
                onCancel: () => { cancelled = true; }
            });

            cy.get('#ckan-confirm-modal .btn-close').click().then(() => {
                expect(cancelled).to.be.true;
            });
        });
    });

    it('should apply correct styles based on type', function () {
        cy.window().then(win => {
            win.ckan.confirm({
                message: 'Dangerous action',
                type: 'danger'
            });

            cy.get('#ckan-confirm-modal .modal-header').should('have.class', 'bg-danger');
        });
    });

    it('should prevent multiple modals from stacking', function () {
        cy.window().then(win => {
            win.ckan.confirm({ message: 'First modal' });
            win.ckan.confirm({ message: 'Second modal' });

            // Only one modal should exist
            cy.get('#ckan-confirm-modal').should('exist');
        });
    });

    it('should add itself to ckan.sandbox()', function () {
        cy.window().then(win => {
            expect(win.ckan.sandbox().confirm).to.equal(win.ckan.confirm);
        });
    });

    it('should center the modal when centered=true', function () {
        cy.window().then(win => {
            win.ckan.confirm({
                message: 'Centered modal',
                centered: true
            });

            cy.get('#ckan-confirm-modal .modal-dialog').should('have.class', 'modal-dialog-centered');
        });
    });

    it('should not center the modal when centered=false', function () {
        cy.window().then(win => {
            win.ckan.confirm({
                message: 'Non-centered modal',
                centered: false
            });

            cy.get('#ckan-confirm-modal .modal-dialog').should('not.have.class', 'modal-dialog-centered');
        });
    });

    it('should make the modal scrollable when scrollable=true', function () {
        cy.window().then(win => {
            win.ckan.confirm({
                message: 'Scrollable modal',
                scrollable: true
            });

            cy.get('#ckan-confirm-modal .modal-dialog').should('have.class', 'modal-dialog-scrollable');
        });
    });

    it('should not make the modal scrollable when scrollable=false', function () {
        cy.window().then(win => {
            win.ckan.confirm({
                message: 'Non-scrollable modal',
                scrollable: false
            });

            cy.get('#ckan-confirm-modal .modal-dialog').should('not.have.class', 'modal-dialog-scrollable');
        });
    });

    it('should make the modal fullscreen when fullscreen=true', function () {
        cy.window().then(win => {
            win.ckan.confirm({
                message: 'Fullscreen modal',
                fullscreen: true
            });

            cy.get('#ckan-confirm-modal .modal-dialog').should('have.class', 'modal-fullscreen');
        });
    });

    it('should not make the modal fullscreen when fullscreen=false', function () {
        cy.window().then(win => {
            win.ckan.confirm({
                message: 'Not fullscreen modal',
                fullscreen: false
            });

            cy.get('#ckan-confirm-modal .modal-dialog').should('not.have.class', 'modal-fullscreen');
        });
    });

    it('backdrop is static by default', function () {
        cy.window().then(win => {
            win.ckan.confirm({ message: 'Backdrop modal' });
        });

        cy.get('.modal-backdrop').should('exist');
    });

    it('should not show backdrop when backdrop=false', function () {
        cy.window().then(win => {
            win.ckan.confirm({
                message: 'No backdrop modal',
                backdrop: false
            });
        });

        cy.get('.modal-backdrop').should('not.exist');
    });
});
