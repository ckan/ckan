/* global $ jQuery gdataDict gresviewId */

// global vars used for state saving/deeplinking
let gsavedPage
let gsavedPagelen
let gsavedSelected
// global var for current view mode (table/list)
let gcurrentView = 'table'
// global var for sort info
let gsortInfo = ''

const run_query = function (params, format) {
  const form = $('#filtered-datatables-download')
  const p = $('<input name="params" type="hidden"/>')
  p.attr('value', JSON.stringify(params))
  form.append(p)
  const f = $('<input name="format" type="hidden"/>')
  f.attr('value', format)
  form.append(f)
  form.submit()
}

// helper for setting expiring localstorage, ttl in secs
function setWithExpiry (key, value, ttl) {
  const now = new Date()

  // `item` is an object which contains the original value
  // as well as the time when it's supposed to expire
  const item = {
    value: value,
    expiry: now.getTime() + ( ttl * 1000 )
  }
  window.localStorage.setItem(key, JSON.stringify(item))
}

// helper for getting expiring localstorage
function getWithExpiry (key) {
  const itemStr = window.localStorage.getItem(key)
  // if the item doesn't exist, return null
  if (!itemStr) {
    return null
  }
  const item = JSON.parse(itemStr)
  const now = new Date()
  // compare the expiry time of the item with the current time
  if (now.getTime() > item.expiry) {
    // If the item is expired, delete the item from storage
    // and return null
    window.localStorage.removeItem(key)
    return null
  }
  return item.value
}

// helper for modal print
function printModal (title) {
  const contents = document.querySelector('.dtr-details').innerHTML
  const prtWindow = window.open('', '_blank')
  prtWindow.document.write('<html><body ><h1>' + title + '</h1><table><tbody>')
  prtWindow.document.write(contents)
  prtWindow.document.write('</tbody></table></html>')
  prtWindow.print()
  prtWindow.close()
}

// helper for modal clipboard copy
function copyModal (title) {
  const origHeaderText = $('#modalHeader').text()
  $('#modalHeader').text(title + ' ' + origHeaderText)
  const el = document.querySelector('.dtr-modal-content')
  const body = document.body
  let range
  let sel
  if (document.createRange && window.getSelection) {
    range = document.createRange()
    sel = window.getSelection()
    sel.removeAllRanges()
    try {
      range.selectNodeContents(el)
      sel.addRange(range)
    } catch (e) {
      range.selectNode(el)
      sel.addRange(range)
    }
  } else if (body.createTextRange) {
    range = body.createTextRange()
    range.moveToElementText(el)
    range.select()
  }
  document.execCommand('copy')
  window.getSelection().removeAllRanges()
  $('#modalHeader').text(origHeaderText)
}

// force column auto text fit adjustment to kick in
// used by "Autofit columns" button
function fitColText () {
  const dt = $('#dtprv').DataTable({ retrieve: true })
  dt.columns.adjust().draw(false)
}

// ensure element id is valid
function validateId (id) {
  id = id.toLowerCase()
  // Make alphanumeric (removes all other characters)
  id = id.replace(/[^a-z0-9_\s-]/g, '')
  // Convert whitespaces and underscore to #
  id = id.replace(/[\s_]/g, '#')
  // Convert multiple # to hyphen
  id = id.replace(/[#]+/g, '-')
  return id
}

// compile sort & active filters for display in print and clipboard copy
function filterInfo (dt, tableSearchText, colFilterText) {
  const dtinfo = document.getElementById('dtprv_info')

  let filtermsg = dtinfo.innerText
  const tablesearch = dt.search()

  // add active filter info to messageTop
  if (tablesearch) {
    filtermsg = filtermsg + ' - <b>' + tableSearchText + ':</b> ' + tablesearch
  }
  let colsearchflag = false
  let colsearchmsg = ''
  dt.columns().every(function () {
    const colsearch = this.search()
    const colname = this.name()

    if (colsearch) {
      colsearchflag = true
      colsearchmsg = colsearchmsg + ' <b>' + colname + ':</b> ' + colsearch + ', '
    }
  })
  if (colsearchflag) {
    filtermsg = filtermsg + '<br/><b>' + colFilterText + ' - </b>' + colsearchmsg.slice(0, -2)
  }
  return filtermsg + '<br/>' + gsortInfo
};

// Copy deeplink to clipboard
function copyLink (dt, deeplink, shareText, sharemsgText) {
  const hiddenDiv = $('<div/>')
    .css({
      height: 1,
      width: 1,
      overflow: 'hidden',
      position: 'fixed',
      top: 0,
      left: 0
    })

  const textarea = $('<textarea readonly/>')
    .val(deeplink)
    .appendTo(hiddenDiv)

  // use copy execCommand to copy link to clipboard
  if (document.queryCommandSupported('copy')) {
    hiddenDiv.appendTo(dt.table().container())
    textarea[0].focus()
    textarea[0].select()

    try {
      const successful = document.execCommand('copy')
      hiddenDiv.remove()

      if (successful) {
        dt.buttons.info(shareText, sharemsgText, 2000)
      }
    } catch (t) {}
  }
}

// main
this.ckan.module('datatables_view', function (jQuery) {
  return {
    initialize: function () {
      const resourcename = $('#dtprv').data('resource-name')
      const languagefile = $('#dtprv').data('languagefile')
      const statesaveflag = $('#dtprv').data('state-save-flag')
      const stateduration = parseInt($('#dtprv').data('state-duration'))
      const searchdelaysetting = parseInt($('#dtprv').data('search-delay-setting'))
      const packagename = $('#dtprv').data('package-name')
      const responsiveflag = $('#dtprv').data('responsive-flag')
      const pagelengthchoices = $('#dtprv').data('page-length-choices')
      const ajaxurl = $('#dtprv').data('ajaxurl')
      const ckanfilters = $('#dtprv').data('ckanfilters')
      const resourceurl = $('#dtprv').data('resource-url')
      const defaultview = $('dtprv').data('default-view')

      const responsiveDetails = {
        display: $.fn.dataTable.Responsive.display.modal({
          header: function (row) {
            // add clipboard and print controls to modal record display
            return '<span id ="modalHeader" style="font-size:200%;font-weight:bold;">Details:</span><div class="dt-buttons">' +
              '<button id="modalcopy-button" class="dt-button" title="Copy to clipboard" onclick="copyModal(\'' +
              packagename + '&mdash;' + resourcename + '\')"><i class="fa fa-files-o"></i></button>' +
              '<button id="modalprint-button" class="dt-button" title="Print" onclick="printModal(\'' +
              packagename + '&mdash;' + resourcename + '\')"><i class="fa fa-print"></i></button>' +
              '&nbsp;&nbsp;&nbsp;&nbsp;</div>'
          }
        }),
        renderer: function (api, rowIdx, columns) {
          const data = $.map(columns, function (col, i) {
            return col.className !== 'none' ?
                '<tr class="dt-body-right" data-dt-row="' + col.rowIndex + '" data-dt-column="' + col.columnIndex + '">' +
                '<td>' + col.title + ':' + '</td> ' +
                '<td>' + col.data + '</td>' +
                '</tr>' : ''
          }).join('')
          return data ? $('<table class="dtr-details" width="100%"/>').append(data) : false
        }
      }

      // get view mode setting from localstorage (table or list/responsive])
      const lastView = getWithExpiry('lastView')
      if (!lastView) {
        if (responsiveflag) {
          gcurrentView = 'list' // aka responsive
        } else {
          gcurrentView = defaultview
        }
        setWithExpiry('lastView', gcurrentView, stateduration)
      } else {
        gcurrentView = lastView
      }

      // get col defns dynamically from data dictionary,
      // init it with _id col defs
      const dynamicCols = [{
        data: '_id',
        searchable: false,
        type: 'num',
        responsivePriority: 1,
        className: 'dt-body-right',
        width: gcurrentView === 'table' ? '28px' : '50px'
      }]

      gdataDict.forEach((colDefn, idx) => {
        let dtType
        switch (colDefn.type) {
          case 'numeric':
            dtType = 'num'
            break
          case 'timestamp':
            dtType = 'date'
            break
          default:
            dtType = 'string'
        }
        dynamicCols.push({ data: colDefn.id, type: dtType })
      })

      // labels for showing active filters in clipboard copy & print
      const tableSearchText = this._('TABLE SEARCH')
      const colFilterText = '&nbsp;&nbsp;&nbsp;' + this._('COLUMN FILTER/S')

      // labels for Sharing current view
      const shareText = this._('Share current view')
      const sharemsgText = this._('Copied deeplink to clipboard')

      const colfitText = this._('Autofit columns')
      const sortText = this._('Sort')

      let activelanguage = languagefile
      // en is the default language, no need to load i18n file
      if (languagefile === '/vendor/DataTables/i18n/en.json') {
        activelanguage = ''
      }

      let fixedColumnSettings = { leftColumns: 1 }
      let responsiveSettings = false
      let orderCellsTopSettings = true
      let scrollXflag = true

      if (gcurrentView === 'list') {
        // responsive mode (aka list view) not compatible with scrollX & column filters
        scrollXflag = false
        fixedColumnSettings = false
        orderCellsTopSettings = false
        dynamicCols.push({
          data: '_colspacer',
          searchable: false,
          className: 'none'
        })
        responsiveSettings = {
          details: responsiveDetails
        }
      } else {
        // table view
        scrollXflag = true
        $('#_colspacer').remove()
        fixedColumnSettings = true
        orderCellsTopSettings = true
        fixedColumnSettings = { leftColumns: 1 }

        // create column filters
        $('#dtprv thead tr').clone(true).appendTo('#dtprv thead')
        $('#dtprv thead tr:eq(1) th').each(function (i) {
          const title = $(this).text()
          const colname = $(this).data('name')
          if (i > 0) {
            $(this).html('<input id="dtcol-' + validateId(title) + '-' + i +
                  '" type="search" results="5" autosave="true" style="width:100%"/>')

            $('input', this).on('keyup change search', function () {
              const dt = $('#dtprv').DataTable({ retrieve: true })
              const colSelector = colname + ':name'
              if (dt.column(colSelector).search() !== this.value) {
                dt
                  .column(colSelector)
                  .search(this.value)
                  .draw()
              }
            })
          } else {
            // for the first column (_id), no col filter, but column width refit button
            $(this).html('<button id="refit-button" title="' + colfitText +
              '" onclick="fitColText()"><i class="fa fa-text-width"></i></button>')
          }
        })
      }

      // init the datatable
      const datatable = $('#dtprv').DataTable({
        paging: true,
        serverSide: true,
        processing: true,
        stateSave: statesaveflag,
        stateDuration: stateduration,
        searchDelay: searchdelaysetting,
        colReorder: {
          fixedColumnsLeft: 1
        },
        fixedColumns: fixedColumnSettings,
        autoWidth: true,
        orderCellsTop: orderCellsTopSettings,
        mark: true,
        keys: true,
        select: {
          style: 'os',
          blurable: true
        },
        language: {
          url: activelanguage,
          paginate: {
            previous: '&lt;',
            next: '&gt;'
          }
        },
        columns: dynamicCols,
        ajax: {
          url: ajaxurl,
          type: 'POST',
          data: function (d) {
            d.filters = ckanfilters
          }
        },
        responsive: responsiveSettings,
        scrollX: scrollXflag,
        scrollY: 100,
        scrollResize: true,
        scrollCollapse: true,
        lengthMenu: pagelengthchoices,
        dom: 'lBifrtp<"resourceinfo"><"sortinfo">',
        stateLoadParams: function (settings, data) {
          // check the current url to see if we've got a state to restore from a deeplink
          const url = new URL(window.location.href)
          let state = url.searchParams.get('state')

          if (state) {
            // if so, try to base64 decode it and parse into object from a json
            try {
              state = JSON.parse(window.atob(state))
              // now iterate over the object properties and assign any that
              // exist to the current loaded state (skipping "time")
              for (const k in state) {
                if (Object.prototype.hasOwnProperty.call(state, k) && k !== 'time') {
                  data[k] = state[k]
                }
              }
            } catch (e) {
              console.error(e)
            }
          }

          // save current page
          gsavedPage = data.page
          gsavedPagelen = data.pagelen

          // save selected rows settings
          gsavedSelected = data.selected

          // restore values of column filters
          const api = new $.fn.dataTable.Api(settings)
          api.columns().every(function (colIdx) {
            const col = data.columns[colIdx]
            if (typeof col !== 'undefined') {
              const colSearch = col.search

              if (colSearch.search) {
                $("thead tr th[data-colidx='" + colIdx + "'] input").val(colSearch.search)
              }
            }
          })
          api.draw()
        },
        stateSaveParams: function (settings, data) {
          data.page = this.api().page()
          data.pagelen = this.api().page.len()
          data.selected = this.api().rows({ selected: true })[0]

          // shade the reset button darkred if there is a saved state
          const lftflag = parseInt(getWithExpiry('loadctr-' + gresviewId))
          if (lftflag < 3 || isNaN(lftflag)) {
            setWithExpiry('loadctr-' + gresviewId, isNaN(lftflag) ? 1 : lftflag + 1, stateduration)
            $('.resetButton').css('color', 'black')
          } else {
            setWithExpiry('loadctr-' + gresviewId, lftflag + 1, stateduration)
            $('.resetButton').css('color', 'darkred')
          }
        },
        initComplete: function (settings, json) {
          // restore some data-dependent saved states now
          // that data is loaded
          if (typeof gsavedPage !== 'undefined') {
            this.api().page.len(gsavedPagelen)
            this.api().page(gsavedPage)
            this.api().draw(false)
          }

          // save selected rows to state localstorage if defined
          if (typeof gsavedSelected !== 'undefined') {
            this.api().rows(gsavedSelected).select()
          }

          // add resourceinfo in footer
          // very useful if this view is embedded
          const resourceInfo = document.getElementById('dtv-resource-info').innerText
          $('div.resourceinfo').html('<a href="' + resourceurl + '">' +
            packagename + '&mdash;' + resourcename +
            '</a> <i class="fa fa-info-circle" title="' + resourceInfo + '"</i>')

          // start showing page once everything is just about rendered
          // we need to make it visible now so smartsize works if needed
          document.getElementsByClassName('dt-view')[0].style.visibility = 'visible'

          const url = new URL(window.location.href)
          const state = url.searchParams.get('state')
          // if there is a state url parm, its a deeplink share
          if (state) {
            // we need to reload to get the deeplink active
            // to init localstorage
            if (!getWithExpiry('deeplink_firsttime')) {
              setWithExpiry('deeplink_firsttime', true, stateduration)
              setTimeout(function () {
                window.location.reload()
              }, 200)
            }
          } else {
            // otherwise, do a smartsize check to fill up screen
            // if default pagelen is too low and there is available space
            const currPageLen = this.api().page.len()
            if (json.recordsTotal > currPageLen) {
              const scrollBodyHeight = $('#resize_wrapper').height() - ($('.dataTables_scrollHead').height() * 2.75)
              const rowHeight = $('tr').first().height()
              // find nearest pagelen to fill display
              const minPagelen = Math.floor(scrollBodyHeight / rowHeight)
              if (currPageLen < minPagelen) {              
                for (const pageLen of pagelengthchoices) {
                  if (pageLen >= minPagelen) {
                    setTimeout(function () {
                      const dt = $('#dtprv').DataTable()
                      dt.page.len(pageLen)
                      dt.ajax.reload()
                      if (gcurrentView === 'list') {
                        dt.responsive.rebuild()
                        dt.responsive.recalc()
                      }
                      dt.columns.adjust().draw()
                      window.localStorage.removeItem('loadctr-' + gresviewId)
                      console.log('smart sized >' + minPagelen)
                    }, 100)
                    break
                  }
                }
              }
            }
          }
        },
        buttons: [{
          text: gcurrentView === 'table' ? '<i class="fa fa-list"></i>' : '<i class="fa fa-table"></i>',
          titleAttr: this._('Table/List toggle'),
          name: 'viewToggleButton',
          action: function (e, dt, node, config) {
            if (gcurrentView === 'list') {
              dt.button('viewToggleButton:name').text('<i class="fa fa-table"></i>')
              gcurrentView = 'table'
              $('#dtprv').removeClass('dt-responsive')
            } else {
              dt.button('viewToggleButton:name').text('<i class="fa fa-list"></i>')
              gcurrentView = 'list'
              $('#dtprv').addClass('dt-responsive')
            }
            setWithExpiry('lastView', gcurrentView, stateduration)
            window.location.reload()
          }
        }, {
          extend: 'copy',
          text: '<i class="fa fa-files-o"></i>',
          titleAttr: this._('Copy to clipboard'),
          title: function () {
            // remove html tags from filterInfo msg
            const filternohtml = filterInfo(datatable, tableSearchText,
              colFilterText).replace(/(<([^>]+)>)/ig, '')
            return resourcename + ' - ' + filternohtml
          }
        }, {
          extend: 'colvis',
          text: '<i class="fa fa-eye-slash"></i>',
          titleAttr: this._('Toggle column visibility'),
          columns: ':gt(0)',
          collectionLayout: 'fixed four-column',
          postfixButtons: [{
            extend: 'colvisRestore',
            text: '<i class="fa fa-undo"></i> ' + this._('Restore visibility')
          }, {
            extend: 'colvisGroup',
            text: '<i class="fa fa-eye"></i> ' + this._('Show all'),
            show: ':hidden'
          }, {
            extend: 'colvisGroup',
            text: '<i class="fa fa-eye-slash"></i> ' + this._('Show none'),
            hide: ':visible'
          }]
        }, {
          text: '<i class="fa fa-download"></i>',
          titleAttr: this._('Filtered download'),
          autoClose: true,
          extend: 'collection',
          buttons: [{
            text: 'CSV',
            action: function (e, dt, button, config) {
              const params = datatable.ajax.params()
              params.visible = datatable.columns().visible().toArray()
              run_query(params, 'csv')
            }
          }, {
            text: 'TSV',
            action: function (e, dt, button, config) {
              const params = datatable.ajax.params()
              params.visible = datatable.columns().visible().toArray()
              run_query(params, 'tsv')
            }
          }, {
            text: 'JSON',
            action: function (e, dt, button, config) {
              const params = datatable.ajax.params()
              params.visible = datatable.columns().visible().toArray()
              run_query(params, 'json')
            }
          }, {
            text: 'XML',
            action: function (e, dt, button, config) {
              const params = datatable.ajax.params()
              params.visible = datatable.columns().visible().toArray()
              run_query(params, 'xml')
            }
          }]
        }, {
          text: '<i class="fa fa-repeat"></i>',
          titleAttr: this._('Reset'),
          className: 'resetButton',
          name: 'resetButton',
          action: function (e, dt, node, config) {
            dt.state.clear()
            $('.resetButton').css('color', 'black')
            window.localStorage.removeItem('loadctr-' + gresviewId)
            window.location.reload()
          }
        }, {
          extend: 'print',
          text: '<i class="fa fa-print"></i>',
          titleAttr: this._('Print'),
          title: packagename + ' — ' + resourcename,
          messageTop: function () {
            return filterInfo(datatable, tableSearchText, colFilterText)
          },
          messageBottom: function () {
            return filterInfo(datatable, tableSearchText, colFilterText)
          },
          exportOptions: {
            columns: ':visible'
          }
        }, {
          text: '<i class="fa fa-share"></i>',
          titleAttr: this._('Share current view'),
          name: 'shareButton',
          action: function (e, dt, node, config) {
            dt.state.save()
            const sharelink = window.location.href + '?state=' + window.btoa(JSON.stringify(dt.state()))
            copyLink(dt, sharelink, shareText, sharemsgText)
          }
        }]
      })

      if (!statesaveflag) {
        // reset and deeplink share require state saving
        // remove those buttons if state saving is off
        datatable.button('resetButton:name').remove()
        datatable.button('shareButton:name').remove()
      }

      // save state of table when row selection is changed
      datatable.on('select deselect', function () {
        datatable.state.save()
      })

      // update sortinfo div in footer
      datatable.on('order.dt', function () {
        const sortOrder = datatable.order()
        if (!sortOrder.length) {
          return
        }
        gsortInfo = '<b>' + sortText + '</b>: '
        sortOrder.forEach((sortcol, idx) => {
          const colText = $('#dtprv thead th:nth-child(' + (sortcol[0] + 1) + ')').text()
          gsortInfo = gsortInfo + colText +
                    (sortcol[1] === 'asc' ? ' <i class="fa fa-caret-up"></i> ' : ' <i class="fa fa-caret-down"></i> ')
        })
        $('div.sortinfo').html(gsortInfo)
      })
    }
  }
})
// end main

// register column.name() datatables API helper using data-attributes
// used by print to show active column filters
$.fn.dataTable.Api.registerPlural('columns().names()', 'column().name()', function (setter) {
  return this.iterator('column', function (settings, column) {
    const col = settings.aoColumns[column]

    if (setter !== undefined) {
      col.sName = setter
      return this
    } else {
      return col.sName
    }
  }, 1)
})

// shake animation
function animateEl (element, animation, complete) {
  if (!element instanceof jQuery || !$(element).length || !animation) return null

  if (element.data('animating')) {
    element.removeClass(element.data('animating')).data('animating', null)
    element.data('animationTimeout') && clearTimeout(element.data('animationTimeout'))
  }

  element.addClass('animated-' + animation).data('animating', 'animated-' + animation)
  element.data('animationTimeout', setTimeout(function () {
    element.removeClass(element.data('animating')).data('animating', null)
    complete && complete()
  }, 400))
}

// custom error handler instead of default datatable alert error
// this often happens when invalid datastore_search queries are returned
$.fn.dataTable.ext.errMode = 'none'
$('#dtprv').on('error.dt', function (e, settings, techNote, message) {
  console.log('DataTables techNote: ', techNote)
  console.log('DataTables error msg: ', message)

  // errors are mostly caused by invalid FTS queries. shake input
  const shakeElement = $(':focus')
  animateEl(shakeElement, 'shake')
})
