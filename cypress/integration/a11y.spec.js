describe("Runs a11y check on pages.", () => {

  before(() => {
    cy.visit('/');
    cy.injectAxe();
  })

  it('Has no a11y violations on front page.', () => {
    cy.checkA11y();
  })
});
