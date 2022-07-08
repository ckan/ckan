describe('Login form', () => {

    beforeEach(() => {
      cy.intercept('/user/login').as('loginUrl')
      cy.intercept('/dashboard').as('userDashboard')
     })

    it('Unauthorized to see dashboard if not logged in', () =>{
        cy.visit('/dashboard', {failOnStatusCode: false})
        cy.get('h1').contains('404 Not Found')
    })

    it('Displays login form', () => {
      cy.visit('/user/login')
      cy.get('.module-content > form').contains('Username or Email')
      cy.get('.module-content > form').contains('Password')
      cy.get('.module-content > form').contains('Remember me')
    })

    it('Displays bad input message when using wrong credentials', () => {
      cy.visit('/user/login')
      cy.get('#field-login').type('badusername')
      cy.get('#field-password').type('badpassword')
      cy.get('.form-actions > .btn').click()

      cy.wait('@loginUrl')

      cy.get('.alert').contains('Login failed. Bad username or password.')
    })

    it('Logs in with the proper credentials', () => {
      cy.visit('/user/login')
      cy.get('#field-login').type('admin')
      cy.get('#field-password').type('12345678')
      cy.get('.module-content > form').submit()

      cy.wait('@loginUrl')
      cy.wait('@userDashboard')

      cy.get('.breadcrumb > .active > a').contains('Dashboard')
      cy.url().should('include', '/dashboard')
      cy.getCookie('ckan').should('exist')
    })

    it('Logs in using the email', () => {
      cy.visit('/user/login')
      cy.get('#field-login').type('admin@ckan.org')
      cy.get('#field-password').type('12345678')
      cy.get('.module-content > form').submit()

      cy.wait('@loginUrl')
      cy.wait('@userDashboard')

      cy.get('.breadcrumb > .active > a').contains('Dashboard')
      cy.url().should('include', '/dashboard')
      cy.get('.nav')
        .should('contain.text', 'News feed')
        .should('contain.text', 'My Datasets')
        .should('contain.text', 'My Organizations')
        .should('contain.text', 'My Groups')

      cy.getCookie('ckan').should('exist')
    })

    it('Loging using a POST request', function () {
        cy.request({
          method: 'POST',
          url: '/user/login',
          form: true,
          body: {
            login: 'admin',
            password: '12345678',
          },
        })
        cy.getCookie('ckan').should('exist')
      })
    })
