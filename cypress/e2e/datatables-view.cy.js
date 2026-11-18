/* globals describe it beforeEach expect cy */

describe('datatables_view literal field names', function () {
  const fields = [
    { id: 'Latitude [degrees N]', type: 'text' },
    { id: 'Station', type: 'text' }
  ]
  let row

  beforeEach(() => {
    row = { _id: 1, 'Latitude [degrees N]': '55.25 N', Station: 'Lake Winnipeg' }
    cy.visit('/')
    cy.clearLocalStorage()
    cy.intercept('GET', '/language', { body: {} })
    cy.intercept('POST', '/ajax', (request) => {
      const params = new URLSearchParams(request.body)
      if (params.get('columns[1][search][value]') === '55') {
        request.alias = 'columnSearch'
      } else if (params.get('order[0][column]') === '1') {
        request.alias = 'columnSort'
      } else {
        request.alias = 'initialLoad'
      }
      request.reply({
        draw: Number(params.get('draw')),
        recordsTotal: 1,
        recordsFiltered: 1,
        data: [row]
      })
    })

    const scripts = [
      'ckanext/datatablesview/assets/vendor/DataTables/datatables.js',
      'ckanext/datatablesview/assets/vendor/DataTables/datatables.mark.js',
      'ckanext/datatablesview/assets/vendor/DataTables/jquery.mark.js',
      'ckanext/datatablesview/assets/vendor/DataTables/dataTables.scrollResize.js',
      'ckanext/datatablesview/assets/vendor/DataTables/datetime.js',
      'ckanext/datatablesview/assets/datatablesview.js'
    ]
    cy.wrap(scripts).each((path) => {
      cy.readFile(path).then((source) => cy.window().then((window) => {
        const script = window.document.createElement('script')
        script.textContent = source
        window.document.body.appendChild(script)
      }))
    })

    cy.window().then((window) => {
      window.gdataDict = fields
      window.gresviewId = 'datatables-view-test'
      window.document.body.classList.add('dt-view')
      const markup = `
        <div id="resize_wrapper" style="height:600px">
          <table id="dtprv" data-module="datatables_view" data-date-format="NONE"
            data-languagecode="en" data-languagefile="/language" data-state-save-flag="false"
            data-state-duration="0" data-ellipsis-length="0" data-default-view="table"
            data-responsive-flag="false" data-responsive-modal="false"
            data-page-length-choices="[10,25,50]" data-ajaxurl="/ajax"
            data-package-name="dataset" data-resource-name="resource"
            data-resource-url="/resource" data-ckanfilters="">
            <thead>
              <tr><th>_id</th><th>Latitude [degrees N]</th><th>Station</th><th id="_colspacer">colspacer</th></tr>
              <tr><th></th><th id="cdx1" class="fhead" data-type="text">Latitude [degrees N]</th>
                <th id="cdx2" class="fhead" data-type="text">Station</th><th id="_colspacerfilter"></th></tr>
            </thead><tbody></tbody>
          </table>
        </div>
        <div id="dtv-resource-info">Test resource</div>
        <form id="filtered-datatables-download"></form>`
      window.jQuery('<div id="fixture">').appendTo(window.document.body).html(markup)
      window.ckan.module.initializeElement(window.document.querySelector('#dtprv'))
    })
    cy.wait('@initialLoad')
    cy.get('#dtprv tbody tr').should('contain.text', row.Station)
  })

  it('renders bracketed values and preserves literal and ordinary column mappings', () => {
    cy.window().should((window) => {
      const table = window.jQuery('#dtprv').DataTable()
      expect(table.cell(0, 1).data()).to.equal(row[fields[0].id])
      expect(table.cell(0, 1).node().textContent.trim()).to.equal(row[fields[0].id])
      expect(table.cell(0, 2).node().textContent.trim()).to.equal(row.Station)
      expect(table.column(1).name()).to.equal(fields[0].id)
      expect(table.column(1).dataSrc()).to.be.a('function')
      expect(table.column(2).dataSrc()).to.equal('Station')
    })
  })

  it('keeps bracketed and ordinary column setters writing to their row fields', () => {
    const updatedBracketValue = '55.26 N'
    const updatedStation = 'Lake Manitoba'
    cy.window().then((window) => {
      const table = window.jQuery('#dtprv').DataTable()
      const backingRow = table.row(0).data()
      table.cell(0, 1).data(updatedBracketValue)
      table.cell(0, 2).data(updatedStation)
      expect(backingRow[fields[0].id]).to.equal(updatedBracketValue)
      expect(backingRow.Station).to.equal(updatedStation)
      expect(table.cell(0, 1).node().textContent.trim()).to.equal(updatedBracketValue)
      expect(table.cell(0, 2).node().textContent.trim()).to.equal(updatedStation)
    })
  })

  it('sends the literal bracketed name when sorting', () => {
    cy.window().then((window) => window.jQuery('#dtprv').DataTable().order([1, 'desc']).draw())
    cy.wait('@columnSort').its('request.body').should((body) => {
      const params = new URLSearchParams(body)
      expect(params.get('columns[1][name]')).to.equal(fields[0].id)
      expect(params.get('columns[2][data]')).to.equal('Station')
      expect(params.get('order[0][column]')).to.equal('1')
    })
  })

  it('sends the literal bracketed name when searching', () => {
    cy.window().then((window) => window.jQuery('#dtprv').DataTable().column(1).search('55').draw())
    cy.wait('@columnSearch').its('request.body').should((body) => {
      const params = new URLSearchParams(body)
      expect(params.get('columns[1][name]')).to.equal(fields[0].id)
      expect(params.get('columns[2][data]')).to.equal('Station')
      expect(params.get('columns[1][search][value]')).to.equal('55')
    })
  })
})
