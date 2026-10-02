/*globals describe beforeEach it assert */
describe('ckan.modules.AutocompleteModule() with select2 tags', function () {
  beforeEach(() => {
    cy.intercept('GET', '**/api/2/util/tag/autocomplete*', {ResultSet: {Result: [{Name: 'zebra'}]}});
    cy.visit('/');
    cy.window().then(win => {
      win.jQuery('<input id="field-tags" data-module="autocomplete" data-module-tags="">')
        .attr('data-module-source', '/api/2/util/tag/autocomplete?incomplete=?')
        .appendTo(win.document.body);
      win.ckan.module.initializeElement(win.document.getElementById('field-tags'));
    });
  });

  function tagsShouldBe(expected) {
    cy.get('#field-tags').invoke('val').should(value => {
      assert.sameMembers(value.split(','), expected);
    });
  }

  it('keeps the last typed tag when the field loses focus', function () {
    cy.get('.select2-search__field').type('delta, epsilon, zeta').blur();
    tagsShouldBe(['delta', 'epsilon', 'zeta']);
  });

  it('keeps the last pasted tag when the field loses focus', function () {
    cy.get('.select2-search__field').invoke('val', 'delta, epsilon, zeta').trigger('input').blur();
    tagsShouldBe(['delta', 'epsilon', 'zeta']);
  });

  it('adds only the clicked suggestion, not the text typed so far', function () {
    cy.get('.select2-search__field').type('zeb');
    cy.contains('.select2-results__option', /^zebra$/).click();
    tagsShouldBe(['zebra']);
  });
});
