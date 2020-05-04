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

  before(() => {
    cy.visit('/');
    cy.injectAxe();
  })

  it('Has no a11y violations on front page.', () => {
    cy.checkA11y(null, null, terminalLog);
  })
});
