function terminalLog(violations) {
  cy.task(
    'log',
    `${violations.length} accessibility violation${
      violations.length === 1 ? '' : 's'
    } ${violations.length === 1 ? 'was' : 'were'} detected`
  )
  // pluck specific keys to keep the table readable
  const violationData = violations.map(
    ({ id, impact, description, nodes }) => ({
      id,
      impact,
      description,
      nodes: nodes.length
    })
  )

  cy.task('table', violationData)
}

describe("Runs a11y check on pages.", () => {

  it('Has no a11y violations on front page.', () => {
    cy.visit('/');
    cy.injectAxe();
    cy.checkA11y(null, null, terminalLog);
  })

  it("Has no a11y violations on dataset page.", () => {
    cy.visit('/dataset')
    cy.injectAxe();
    cy.checkA11y(null, null, terminalLog);
  })

  it("Has no a11y violations on organization page.", () => {
    cy.visit('/organization')
    cy.injectAxe();
    cy.checkA11y(null, null, terminalLog)
  })

  it("Has no a11y violations on groups page.", () => {
    cy.visit('/group')
    cy.injectAxe();
    cy.checkA11y(null, null, terminalLog)
  })

  it("Has no a11y violations on about page.", () => {
    cy.visit('/about')
    cy.injectAxe();
    cy.checkA11y(null, null, terminalLog)
  })

});
