/* global $ jQuery gdataDict gresviewId */

// global vars used for state saving/deeplinking
let gsavedPage
let gsavedPagelen
let gsavedSelected
// global var for current view mode (table/list)
let gcurrentView = 'table'
// global var for sort info, global so we can show it in copy/print
let gsortInfo = ''
// global vars for filter info labels
let gtableSearchText = ''
let gcolFilterText = ''

let datatable
const gisFirefox = navigator.userAgent.toLowerCase().indexOf('firefox') > -1
let gsearchMode = ''
let gstartTime = 0
let gelapsedTime

// HELPER FUNCTIONS
// helper for filtered downloads
const run_query = function (params, format) {
  const form = $('#filtered-datatables-download')
  const p = $('<input name="params" type="hidden"/>')
  p.attr('value', JSON.stringify(params))
  form.append(p)
  const f = $('<input name="format" type="hidden"/>')
  f.attr('value', format)
  form.append(f)
  form.submit()
  p.remove()
  f.remove()
}

// helper for setting expiring localstorage, ttl in secs
function setWithExpiry (key, value, ttl) {
  const now = new Date()

  // `item` is an object which contains the original value
  // as well as the time when it's supposed to expire
  const item = {
    value: value,
    expiry: ttl > 0 ? now.getTime() + (ttl * 1000) : 0
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
  let item
  try {
    item = JSON.parse(itemStr)
  } catch {
    return null
  }
  const now = new Date()
  // compare the expiry time of the item with the current time
  if (item.expiry && now.getTime() > item.expiry) {
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
  const el = document.querySelector('.dtr-details')
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
}

// force column auto width adjustment to kick in
// used by "Autofit columns" button
function fitColText () {
  const dt = $('#dtprv').DataTable({ retrieve: true })
  if (gcurrentView === 'list') {
    dt.responsive.recalc()
  }
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

// compile sort & active filters for display in print, clipboard copy & search tooltip
function filterInfo (dt, noHtml = false, justFilterInfo = false, wrapped = false) {
  let filtermsg = justFilterInfo ? '' : document.getElementById('dtprv_info').innerText

  const selinfo = document.getElementsByClassName('select-info')[0]

  if (selinfo !== undefined) {
    filtermsg = filtermsg.replace(selinfo.innerText, ', ' + selinfo.innerText)
  }

  // add active filter info to messageTop
  if (gsearchMode === 'table') {
    filtermsg = filtermsg + '<br/> <b>' + gtableSearchText + ':</b> ' + dt.search()
  } else if (gsearchMode === 'column') {
    let colsearchflag = false
    let colsearchmsg = ''
    dt.columns().every(function () {
      const colsearch = this.search()
      const colname = this.name()

      if (colsearch) {
        colsearchflag = true
        colsearchmsg = colsearchmsg + ' <b>' + colname + ':</b><br/>' + colsearch + ', '
      }
    })
    if (colsearchflag) {
      filtermsg = filtermsg + '<br/> <b>' + gcolFilterText + ': <br/></b>' + colsearchmsg.slice(0, -2)
    }
  }
  filtermsg = justFilterInfo ? filtermsg : filtermsg + '<br/>' + gsortInfo
  filtermsg = noHtml ? filtermsg.replace(/(<([^>]+)>)/ig, '') : filtermsg
  filtermsg = wrapped ? filtermsg.replace(/,/g, '\n') : filtermsg
  return filtermsg.trim()
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

  // save & deselect rows, so we copy the link, not the rows
  const selectedRows = dt.rows({ selected: true })[0]
  dt.rows().deselect()

  hiddenDiv.appendTo(dt.table().container())
  textarea[0].focus()
  textarea[0].select()

  hiddenDiv.appendTo(dt.table().container())
  textarea[0].focus()
  textarea[0].select()
  // use copy execCommand to copy link to clipboard
  const successful = document.execCommand('copy')
  hiddenDiv.remove()

  if (successful) {
    dt.buttons.info(shareText, sharemsgText, 2000)
  }
  dt.rows(selectedRows).select()
}

// helper for hiding search inputs for list/responsive mode
function hideSearchInputs (columns) {
  for (let i = 0; i < columns.length; i++) {
    if (columns[i]) {
      $('#cdx' + i).show()
    } else {
      $('#cdx' + i).hide()
    }
  }
  $('#_colspacerfilter').hide()
}

// helper for setting up filterObserver
function initFilterObserver () {
  // if no filter is active, toggle filter tooltip as required
  // this is less expensive than querying the DT api to check global filter and each column
  // separately for filter status. Here, we're checking if an open parenthesis is in the filter info,
  // which indicates that there is a filter active, regardless of language
  // (e.g. "4 of 1000 entries (filtered from...)")
  const filterObserver = new MutationObserver(function (e) {
    const infoText = document.getElementById('dtprv_info').innerText
    if (!infoText.includes('(')) {
      document.getElementById('filterinfoicon').style.visibility = 'hidden'
    } else {
      document.getElementById('filterinfoicon').style.visibility = 'visible'
    }
  })
  try {
    filterObserver.observe(document.getElementById('dtprv_info'), { characterData: true, subtree: true, childList: true })
  } catch (e) {}
}

// helper for converting links in text into clickable links
const linkify = (input) => {
  let text = input
  const linksFound = text.match(/(\b(https?)[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/ig)
  const links = []
  if (linksFound != null) {
    if (linksFound.length === 1 && input.match(/\.(jpeg|jpg|gif|png|svg|apng|webp|avif)$/)) {
      // the whole text is just one link and its a picture, create a thumbnail
      text = '<div class="thumbnail zoomthumb"><a href="' + linksFound[0] + '" target="_blank"><img src="' + linksFound[0] + '"></a></div>'
      return { text: text, links: linksFound }
    }
    for (let i = 0; i < linksFound.length; i++) {
      links.push('<a href="' + linksFound[i] + '" target="_blank">' + linksFound[i] + '</a>')
      text = text.split(linksFound[i]).map(item => { return item }).join(links[i])
    }
    return { text: text, links: linksFound }
  } else {
    return { text: input, links: [] }
  }
}

// helper to protect against uncontrolled HTML input
const esc = function (t) {
  return t
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

// MAIN
this.ckan.module('datatables_view', function (jQuery) {
  return {
    initialize: function () {
      const that = this

      // fetch parameters from template data attributes
      const dtprv = $('#dtprv')
      const resourcename = dtprv.data('resource-name')
      const languagecode = dtprv.data('languagecode')
      const languagefile = dtprv.data('languagefile')
      const statesaveflag = dtprv.data('state-save-flag')
      const stateduration = parseInt(dtprv.data('state-duration'))
      const ellipsislength = parseInt(dtprv.data('ellipsis-length'))
      const dateformat = dtprv.data('date-format').trim()
      const formatdateflag = dateformat.toUpperCase() !== 'NONE'
      const packagename = dtprv.data('package-name')
      const responsiveflag = dtprv.data('responsive-flag')
      const pagelengthchoices = dtprv.data('page-length-choices')
      const ajaxurl = dtprv.data('ajaxurl')
      const ckanfilters = dtprv.data('ckanfilters')
      const resourceurl = dtprv.data('resource-url')
      const defaultview = dtprv.data('default-view')

      // get view mode setting from localstorage (table or list/responsive])
      const lastView = getWithExpiry('lastView')
      if (!lastView) {
        if (responsiveflag) {
          gcurrentView = 'list' // aka responsive
        } else {
          gcurrentView = defaultview
        }
        setWithExpiry('lastView', gcurrentView, 0)
      } else {
        gcurrentView = lastView
      }

      // get column definitions dynamically from data dictionary,
      // init data structure with _id column definition
      const dynamicCols = [{
        data: '_id',
        searchable: false,
        type: 'num',
        className: 'dt-body-right',
        width: gcurrentView === 'table' ? '28px' : '50px'
      }]

      gdataDict.forEach((colDefn, idx) => {
        const colDict = { name: colDefn.id, data: colDefn.id, contentPadding: 'MM' }
        switch (colDefn.type) {
          case 'numeric':
            colDict.type = 'num'
            break
          case 'timestamp':
          case 'timestamptz':
            colDict.type = 'date'
            if (formatdateflag) {
              colDict.render = $.fn.dataTable.render.moment(window.moment.ISO_8601, dateformat, languagecode)
            }
            break
          default:
            colDict.type = 'html'
            if (!ellipsislength) {
              colDict.className = 'wrapcell'
            }
            colDict.render = function (data, type, row, meta) {
              // Order, search and type get the original data
              if (type !== 'display') {
                return data
              }
              if (typeof data !== 'number' && typeof data !== 'string') {
                return data
              }
              data = data.toString() // cast numbers

              const linkifiedData = linkify(data)
              // if there are no http links, see if we need to apply ellipsis truncation logic
              if (!linkifiedData.links) {
                // no links, just do simple truncation if ellipsislength is defined
                if (!ellipsislength || data.length <= ellipsislength) {
                  return data
                }
                const shortened = data.substr(0, ellipsislength - 1).trimEnd()
                return '<span class="ellipsis" title="' + esc(data) + '">' + shortened + '&#8230;</span>'
              } else {
                // there are links
                const strippedData = linkifiedData.text.replace(/(<([^>]+)>)/gi, '')
                if (!ellipsislength || strippedData.length <= ellipsislength) {
                  return linkifiedData.text
                }
                let linkpos = ellipsislength
                let lastpos = ellipsislength
                let lastlink = ''
                let addLen = 0
                // check if truncation point is in the middle of a link
                for (const aLink of linkifiedData.links) {
                  linkpos = data.indexOf(aLink)
                  if (linkpos + aLink.length >= ellipsislength) {
                    // truncation point is in the middle of a link, truncate to where the link started
                    break
                  } else {
                    addLen = addLen + lastlink.length ? (lastlink.length) + 31 : 0 // 31 is the number of other chars in the full anchor tag
                    lastpos = linkpos
                    lastlink = aLink
                  }
                }
                const shortened = linkifiedData.text.substr(0, lastpos + addLen).trimEnd()
                return '<span class="ellipsis" title="' + esc(strippedData) + '">' + shortened + '&#8230;</span>'
              }
            }
        }
        dynamicCols.push(colDict)
      })

      // labels for showing active filters in clipboard copy & print
      gtableSearchText = that._('TABLE FILTER')
      gcolFilterText = that._('COLUMN FILTER/S')

      let activelanguage = languagefile
      // en is the default language, no need to load i18n file
      if (languagefile === '/vendor/DataTables/i18n/en.json') {
        activelanguage = ''
      }

      // settings if gcurrentView === table
      let fixedColumnSetting = true
      let scrollXflag = true
      let responsiveSettings = false

      if (gcurrentView === 'list') {
        // we're in list view mode (aka responsive mode)
        // not compatible with scrollX
        fixedColumnSetting = false
        scrollXflag = false

        // create _colspacer column to ensure display of green record detail button
        dynamicCols.push({
          data: '',
          searchable: false,
          className: 'none',
          defaultContent: ''
        })

        // initialize settings for responsive mode (list view)
        responsiveSettings = {
          details: {
            display: $.fn.dataTable.Responsive.display.modal({
              header: function (row) {
                // add clipboard and print buttons to modal record display
                var data = row.data();
                return '<span style="font-size:150%;font-weight:bold;">Details:</span>&nbsp;&nbsp;<div class=" dt-buttons btn-group">' +
                  '<button id="modalcopy-button" class="btn btn-default" title="' + that._('Copy to clipboard') + '" onclick="copyModal(\'' +
                  packagename + '&mdash;' + resourcename + '\')"><i class="fa fa-copy"></i></button>' +
                  '<button id="modalprint-button" class="btn btn-default" title="' + that._('Print') + '" onclick="printModal(\'' +
                  packagename + '&mdash;' + resourcename + '\')"><i class="fa fa-print"></i></button>' +
                  '</div>&nbsp;'
              }
            }),
            // render the Record Details in a modal dialog box
            // do not render the _colspacer column, which has the 'none' class
            // the none class in responsive mode forces the _colspacer column to be hidden
            // guaranteeing the blue record details button is always displayed, even for narrow tables
            // also, when a column's content has been truncated with an ellipsis, show the untruncated content
            renderer: function (api, rowIdx, columns) {
              const data = $.map(columns, function (col, i) {
                return col.className !== ' none'
                  ? '<tr class="dt-body-right" data-dt-row="' + col.rowIndex + '" data-dt-column="' + col.columnIndex + '">' +
                    '<td>' + col.title + ':' + '</td><td>' +
                    (col.data.startsWith('<span class="ellipsis"') ? col.data.substr(30, col.data.indexOf('">') - 30) : col.data) +
                    '</td></tr>'
                  : ''
              }).join('')
              return data ? $('<table class="dtr-details" width="100%"/>').append(data) : false
            }
          }
        }
      } else {
        // we're in table view mode
        // remove _colspacer column/filter if it exists
        $('#_colspacer').remove()
        $('#_colspacerfilter').remove()
      }

      // create column filters
      $('.fhead').each(function (i) {
        const thecol = this
        const colname = thecol.textContent
        const colid = 'dtcol-' + validateId(colname) + '-' + i
        const coltype = $(thecol).data('type')
        const placeholderText = formatdateflag && coltype.substr(0, 9) === 'timestamp' ? ' placeholder="yyyy-mm-dd"' : ''
        $('<input id="' + colid + '" name="' + colid + '" autosave="' + colid + '"' +
                placeholderText +
                ' class="fhead form-control input-sm" type="search" results="10" autocomplete="on" style="width:100%"/>')
          .appendTo($(thecol).empty())
          .on('keyup search', function (event) {
            const colSelector = colname + ':name'
            // Firefox doesn't do clearing of input when ESC is pressed
            if (gisFirefox && event.keyCode === 27) {
              this.value = ''
            }
            //  only do column search on enter or clearing of input
            if (event.keyCode === 13 || (this.value === '' && datatable.column(colSelector).search() !== '')) {
              datatable
                .column(colSelector)
                .search(this.value)
                .page(0)
                .draw(false)
              gsearchMode = 'column'
            }
          })
      })

      // init the datatable
      datatable = $('#dtprv').DataTable({
        paging: true,
        serverSide: true,
        processing: false,
        stateSave: statesaveflag,
        stateDuration: stateduration,
        colReorder: {
          fixedColumnsLeft: 1
        },
        fixedColumns: fixedColumnSetting,
        autoWidth: true,
        orderCellsTop: true,
        mark: true,
        // Firefox messes up clipboard copy & deeplink share
        // with key extension clipboard support on. Turn it off
        keys: gisFirefox ? { clipboard: false } : true,
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
          timeout: 60000,
          data: function (d) {
            d.filters = ckanfilters
          }
        },
        responsive: responsiveSettings,
        scrollX: scrollXflag,
        scrollY: 400,
        scrollResize: true,
        scrollCollapse: false,
        lengthMenu: pagelengthchoices,
        dom: 'lBifrt<"resourceinfo"><"sortinfo">p',
        stateLoadParams: function (settings, data) {
          // this callback is invoked whenever state info is loaded

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
          // save view mode
          setWithExpiry('lastView', data.viewmode, 0)

          // restore values of column filters
          const api = new $.fn.dataTable.Api(settings)
          api.columns().every(function (colIdx) {
            const col = data.columns[colIdx]
            if (typeof col !== 'undefined') {
              const colSearch = col.search
              if (colSearch.search) {
                $('#cdx' + colIdx + ' input').val(colSearch.search)
              }
            }
          })
          api.draw(false)
        }, // end stateLoadParams
        stateSaveParams: function (settings, data) {
          // this callback is invoked when saving state info

          // let's also save page, pagelen and selected rows in state info
          data.page = this.api().page()
          data.pagelen = this.api().page.len()
          data.selected = this.api().rows({ selected: true })[0]
          data.viewmode = gcurrentView

          // shade the reset button darkred if there is a saved state
          const lftflag = parseInt(getWithExpiry('loadctr-' + gresviewId))
          if (lftflag < 3 || isNaN(lftflag)) {
            setWithExpiry('loadctr-' + gresviewId, isNaN(lftflag) ? 1 : lftflag + 1, stateduration)
            $('.resetButton').css('color', 'black')
          } else {
            setWithExpiry('loadctr-' + gresviewId, lftflag + 1, stateduration)
            $('.resetButton').css('color', 'darkred')
          }
        }, // end stateSaveParams
        initComplete: function (settings, json) {
          // this callback is invoked by DataTables when table is fully rendered
          const api = this.api()
          // restore some data-dependent saved states now that data is loaded
          if (typeof gsavedPage !== 'undefined') {
            api.page.len(gsavedPagelen)
            api.page(gsavedPage)
          }

          // restore selected rows from state
          if (typeof gsavedSelected !== 'undefined') {
            api.rows(gsavedSelected).select()
          }

          // add filterinfo by global search label
          $('#dtprv_filter label').before('<i id="filterinfoicon" class="fa fa-info-circle"</i>&nbsp;')

          // on mouseenter on Search info icon, update tooltip with filterinfo
          $('#filterinfoicon').mouseenter(function () {
            document.getElementById('filterinfoicon').title = filterInfo(datatable, true, true, true) +
              '\n' + (gelapsedTime / 1000).toFixed(2) + ' ' + that._('seconds') + '\n' +
              that._('Double-click to reset filters')
          })

          // on dblclick on Search info icon, clear all filters
          $('#filterinfoicon').dblclick(function () {
            datatable.search('')
              .columns().search('')
              .draw(false)
            $('th.fhead input').val('')
          })

          // add resourceinfo in footer, very useful if this view is embedded
          const resourceInfo = document.getElementById('dtv-resource-info').innerText
          $('div.resourceinfo').html('<a href="' + resourceurl + '">' +
            packagename + '&mdash;' + resourcename +
            '</a> <i class="fa fa-info-circle" title="' + resourceInfo + '"</i>')

          // if in list/responsive mode, hide search inputs for hidden columns
          if (gcurrentView === 'list') {
            hideSearchInputs(api.columns().responsiveHidden().toArray())
          }

          // only do table search on enter key, or clearing of input
          const tableSearchInput = $('#dtprv_filter label input')
          tableSearchInput.unbind()
          tableSearchInput.bind('keyup search', function (event) {
            // Firefox doesn't do clearing of input when ESC is pressed
            if (gisFirefox && event.keyCode === 27) {
              this.value = ''
            }
            if (event.keyCode === 13 || (tableSearchInput.val() === '' && datatable.search() !== '')) {
              datatable
                .search(this.value)
                .draw()
              gsearchMode = 'table'
            }
          })

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
              setWithExpiry('deeplink_firsttime', true, 4)
              setTimeout(function () {
                window.location.reload()
              }, 200)
            }
          } else {
            // otherwise, do a smartsize check to fill up screen
            // if default pagelen is too low and there is available space
            const currPageLen = api.page.len()
            if (json.recordsTotal > currPageLen) {
              const scrollBodyHeight = $('#resize_wrapper').height() - ($('.dataTables_scrollHead').height() * 2.75)
              const rowHeight = $('tbody tr').first().height()
              // find nearest pagelen to fill display
              const minPageLen = Math.floor(scrollBodyHeight / rowHeight)
              if (currPageLen < minPageLen) {
                for (const pageLen of pagelengthchoices) {
                  if (pageLen >= minPageLen) {
                    api.page.len(pageLen)
                    api.ajax.reload()
                    api.columns.adjust()
                    window.localStorage.removeItem('loadctr-' + gresviewId)
                    console.log('smart sized >' + minPageLen)
                    setTimeout(function () {
                      const api = $('#dtprv').DataTable({ retrieve: true })
                      api.draw(false)
                      fitColText()
                    }, 100)
                    break
                  }
                }
              }
            }
          }
        }, // end InitComplete
        buttons: [{
          name: 'viewToggleButton',
          text: gcurrentView === 'table' ? '<i class="fa fa-list"></i>' : '<i class="fa fa-table"></i>',
          titleAttr: that._('Table/List toggle'),
          className: 'btn-default',
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
            setWithExpiry('lastView', gcurrentView, 0)
            window.localStorage.removeItem('loadctr-' + gresviewId)
            dt.state.clear()
            window.location.reload()
          }
        }, {
          extend: 'copy',
          text: '<i class="fa fa-copy"></i>',
          titleAttr: that._('Copy to clipboard'),
          className: 'btn-default',
          title: function () {
            // remove html tags from filterInfo msg
            const filternohtml = filterInfo(datatable, true)
            return resourcename + ' - ' + filternohtml
          },
          exportOptions: {
            columns: ':visible',
            orthogonal: 'filter'
          }
        }, {
          extend: 'colvis',
          text: '<i class="fa fa-eye-slash"></i>',
          titleAttr: that._('Toggle column visibility'),
          className: 'btn-default',
          columns: 'th:gt(0):not(:contains("colspacer"))',
          collectionLayout: 'fixed',
          postfixButtons: [{
            extend: 'colvisRestore',
            text: '<i class="fa fa-undo"></i> ' + that._('Restore visibility')
          }, {
            extend: 'colvisGroup',
            text: '<i class="fa fa-eye"></i> ' + that._('Show all'),
            show: ':hidden'
          }, {
            extend: 'colvisGroup',
            text: '<i class="fa fa-eye-slash"></i> ' + that._('Show none'),
            action: function () {
              datatable.columns().every(function () {
                if (this.index()) { // always show _id col, index 0
                  this.visible(false)
                }
              })
            }
          }, {
            extend: 'colvisGroup',
            text: '<i class="fa fa-filter"></i> ' + that._('Filtered'),
            action: function () {
              datatable.columns().every(function () {
                if (this.index()) { // always show _id col, index 0
                  if (this.search()) {
                    this.visible(true)
                  } else {
                    this.visible(false)
                  }
                }
              })
            }
          }]
        }, {
          text: '<i class="fa fa-download"></i>',
          titleAttr: that._('Filtered download'),
          className: 'btn-default',
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
          name: 'resetButton',
          text: '<i class="fa fa-repeat"></i>',
          titleAttr: that._('Reset'),
          className: 'btn-default resetButton',
          action: function (e, dt, node, config) {
            dt.state.clear()
            $('.resetButton').css('color', 'black')
            window.localStorage.removeItem('loadctr-' + gresviewId)
            window.location.reload()
          }
        }, {
          extend: 'print',
          text: '<i class="fa fa-print"></i>',
          titleAttr: that._('Print'),
          className: 'btn-default',
          title: packagename + ' — ' + resourcename,
          messageTop: function () {
            return filterInfo(datatable)
          },
          messageBottom: function () {
            return filterInfo(datatable)
          },
          exportOptions: {
            columns: ':visible',
            stripHtml: false
          }
        }, {
          name: 'shareButton',
          text: '<i class="fa fa-share"></i>',
          titleAttr: that._('Share current view'),
          className: 'btn-default',
          action: function (e, dt, node, config) {
            dt.state.save()
            const sharelink = window.location.href + '?state=' + window.btoa(JSON.stringify(dt.state()))
            copyLink(dt, sharelink, that._('Share current view'), that._('Copied deeplink to clipboard'))
          }
        }]
      })

      if (!statesaveflag) {
        // "Reset" & "Share current view" buttons require state saving
        // remove those buttons if state saving is off
        datatable.button('resetButton:name').remove()
        datatable.button('shareButton:name').remove()
      }

      // EVENT HANDLERS
      // called before making AJAX request
      datatable.on('preXhr', function (e, settings, data) {
        gstartTime = window.performance.now()
      })

      // called after getting an AJAX response from CKAN
      datatable.on('xhr', function (e, settings, json, xhr) {
        gelapsedTime = window.performance.now() - gstartTime
      })

      // save state of table when row selection is changed
      datatable.on('select deselect', function () {
        datatable.state.save()
      })

      // hide search inputs as needed in responsive/list mode when resizing
      datatable.on('responsive-resize', function (e, datatable, columns) {
        hideSearchInputs(columns)
      })

      // a language file has been loaded async
      // this only happens when a non-english language is loaded
      datatable.on('i18n', function () {
        // and we need to ensure Filter Observer is in place
        setTimeout(initFilterObserver(), 100)
      })

      initFilterObserver()

      // update footer sortinfo when sorting
      datatable.on('order', function () {
        const sortOrder = datatable.order()
        if (!sortOrder.length) {
          return
        }
        gsortInfo = '<b> ' + that._('Sort') + '</b> <i id="sortinfoicon" class="fa fa-info-circle" title="' +
            that._('Press SHIFT key while clicking on\nsort control for multi-column sort') + '"</i> : '
        sortOrder.forEach((sortcol, idx) => {
          const colText = datatable.column(sortcol[0]).name()
          gsortInfo = gsortInfo + colText +
                      (sortcol[1] === 'asc'
                        ? ' <span class="fa fa-sort-amount-asc"></span> '
                        : ' <span class="fa fa-sort-amount-desc"></span> ')
        })
        $('div.sortinfo').html(gsortInfo)
      })
    }
  }
})
// END MAIN

// register column.name() DataTables API helper so we can refer to columns by name
// instead of just column index number
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
  if (!(element instanceof jQuery) || !$(element).length || !animation) return null

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

  if (techNote === 6) {
    // possible misaligned column headers, refit columns
    const api = new $.fn.dataTable.Api(settings)
    api.columns.adjust().draw(false)
  } else {
    // errors are mostly caused by invalid FTS queries. shake input
    const shakeElement = $(':focus')
    animateEl(shakeElement, 'shake')
  }
})
