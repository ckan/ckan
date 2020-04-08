// ***********************************************
// This example commands.js shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************
//
//
// -- This is a parent command --
// Cypress.Commands.add("login", (email, password) => { ... })
//
//
// -- This is a child command --
// Cypress.Commands.add("drag", { prevSubject: 'element'}, (subject, options) => { ... })
//
//
// -- This is a dual command --
// Cypress.Commands.add("dismiss", { prevSubject: 'optional'}, (subject, options) => { ... })
//
//
// -- This will overwrite an existing command --
// Cypress.Commands.overwrite("visit", (originalFn, url, options) => { ... })

/* Helper function for loading snippets from the ajax_snippets directory.
       * The filename should be provided and an optional object of query
       * string parameters. The returned snippet will be loaded into the
       * fixture and passed to any callback.
       *
       * The callback shares the same scope as the rest of the suite so you
       * can assign test variables easily. It is passed the loaded HTML string
       * and the fixture element.
       *
       * filename - The snippet filename to load.
       * params   - An optional object of query string params.
       * callback - An optional callback to call when loaded.
       *
       * Example:
       *
       *   // To simply load a fixture.
       *   beforeEach(function (done) {
       *     this.loadFixture('my-snippet', done);
       *   });
       *
       *   // To get the html itself.
       *   beforeEach(function (done) {
       *     this.loadFixture('my-snippet', function (html) {
       *       this.template = html;
       *       done();
       *     });
       *   });
       *
       */
Cypress.Commands.add('loadFixture', (filename, params, callback) => {
  let context = this;

  // Allow function to be called without params.
  if (typeof params === 'function') {
    callback = params;
    params = {};
  }

  cy.window().then(win => {
    return  (new win.ckan.Client()).getTemplate(filename, params).fail(function () {
      throw new Error('Unable to load fixture: ' + filename);
    }).pipe(function (template) {
      let fixture = win.jQuery('#fixture').html(template);
      callback && callback.call(context, template, fixture);
      return template;
    });
  })
});
