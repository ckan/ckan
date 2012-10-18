/* -*- Mode: Java; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set shiftwidth=2 tabstop=2 autoindent cindent expandtab: */
/* Copyright 2012 Mozilla Foundation
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/*

How to update the pdf.js in CKAN
================================

- replace pdf.js file
- remove the kDefaultURL from the viwer.js
- move all content from
    `document.addEventListener('DOMContentLoaded', function webViewerLoad(evt){...})
    to the function `loadPdfJsView` in the viewer.js
- upgrade the viewer.css
- remove the `position: absolute;` from the `#toolbarViewerLeft` and `#toolbarViewerRight`
    since it causes issues in webkit
- upgarde the html, don't forget to keep the `data-module`
- try to work out the remaining issues (Sorry, it's not that easy).

*/

'use strict';

var kDefaultScale = 'auto';
var kDefaultScaleDelta = 1.1;
var kUnknownScale = 0;
var kCacheSize = 20;
var kCssUnits = 96.0 / 72.0;
var kScrollbarPadding = 40;
var kMinScale = 0.25;
var kMaxScale = 4.0;
var kImageDirectory = './images/';
var kSettingsMemory = 20;
var RenderingStates = {
  INITIAL: 0,
  RUNNING: 1,
  PAUSED: 2,
  FINISHED: 3
};

var mozL10n = document.mozL10n || document.webL10n;

function getFileName(url) {
  var anchor = url.indexOf('#');
  var query = url.indexOf('?');
  var end = Math.min(
    anchor > 0 ? anchor : url.length,
    query > 0 ? query : url.length);
  return url.substring(url.lastIndexOf('/', end) + 1, end);
}

function scrollIntoView(element, spot) {
  var parent = element.offsetParent, offsetY = element.offsetTop;
  while (parent.clientHeight == parent.scrollHeight) {
    offsetY += parent.offsetTop;
    parent = parent.offsetParent;
    if (!parent)
      return; // no need to scroll
  }
  if (spot)
    offsetY += spot.top;
  parent.scrollTop = offsetY;
}

var Cache = function cacheCache(size) {
  var data = [];
  this.push = function cachePush(view) {
    var i = data.indexOf(view);
    if (i >= 0)
      data.splice(i);
    data.push(view);
    if (data.length > size)
      data.shift().destroy();
  };
};

var ProgressBar = (function ProgressBarClosure() {

  function clamp(v, min, max) {
    return Math.min(Math.max(v, min), max);
  }

  function ProgressBar(id, opts) {

    // Fetch the sub-elements for later
    this.div = document.querySelector(id + ' .progress');

    // Get options, with sensible defaults
    this.height = opts.height || 100;
    this.width = opts.width || 100;
    this.units = opts.units || '%';

    // Initialize heights
    this.div.style.height = this.height + this.units;
  }

  ProgressBar.prototype = {

    updateBar: function ProgressBar_updateBar() {
      if (this._indeterminate) {
        this.div.classList.add('indeterminate');
        return;
      }

      var progressSize = this.width * this._percent / 100;

      if (this._percent > 95)
        this.div.classList.add('full');
      else
        this.div.classList.remove('full');
      this.div.classList.remove('indeterminate');

      this.div.style.width = progressSize + this.units;
    },

    get percent() {
      return this._percent;
    },

    set percent(val) {
      this._indeterminate = isNaN(val);
      this._percent = clamp(val, 0, 100);
      this.updateBar();
    }
  };

  return ProgressBar;
})();


// Settings Manager - This is a utility for saving settings
// First we see if localStorage is available
// If not, we use FUEL in FF
// Use asyncStorage for B2G
var Settings = (function SettingsClosure() {
  var isLocalStorageEnabled = (function localStorageEnabledTest() {
    // Feature test as per http://diveintohtml5.info/storage.html
    // The additional localStorage call is to get around a FF quirk, see
    // bug #495747 in bugzilla
    try {
      return 'localStorage' in window && window['localStorage'] !== null &&
          localStorage;
    } catch (e) {
      return false;
    }
  })();

  function Settings(fingerprint) {
    this.fingerprint = fingerprint;
    this.initializedPromise = new PDFJS.Promise();

    var resolvePromise = (function settingsResolvePromise(db) {
      this.initialize(db || '{}');
      this.initializedPromise.resolve();
    }).bind(this);



    if (isLocalStorageEnabled)
      resolvePromise(localStorage.getItem('database'));
  }

  Settings.prototype = {
    initialize: function settingsInitialize(database) {
      database = JSON.parse(database);
      if (!('files' in database))
        database.files = [];
      if (database.files.length >= kSettingsMemory)
        database.files.shift();
      var index;
      for (var i = 0, length = database.files.length; i < length; i++) {
        var branch = database.files[i];
        if (branch.fingerprint == this.fingerprint) {
          index = i;
          break;
        }
      }
      if (typeof index != 'number')
        index = database.files.push({fingerprint: this.fingerprint}) - 1;
      this.file = database.files[index];
      this.database = database;
    },

    set: function settingsSet(name, val) {
      if (!this.initializedPromise.isResolved)
        return;

      var file = this.file;
      file[name] = val;
      var database = JSON.stringify(this.database);
      if (isLocalStorageEnabled)
        localStorage.setItem('database', database);
    },

    get: function settingsGet(name, defaultValue) {
      if (!this.initializedPromise.isResolved)
        return defaultValue;

      return this.file[name] || defaultValue;
    }
  };

  return Settings;
})();

var cache = new Cache(kCacheSize);
var currentPageNumber = 1;

var PDFView = {
  pages: [],
  thumbnails: [],
  currentScale: kUnknownScale,
  currentScaleValue: null,
  initialBookmark: document.location.hash.substring(1),
  startedTextExtraction: false,
  pageText: [],
  container: null,
  thumbnailContainer: null,
  initialized: false,
  fellback: false,
  pdfDocument: null,
  sidebarOpen: false,
  pageViewScroll: null,
  thumbnailViewScroll: null,
  isFullscreen: false,
  previousScale: null,
  pageRotation: 0,
  lastScroll: 0,

  // called once when the document is loaded
  initialize: function pdfViewInitialize() {
    var self = this;
    var container = this.container = document.getElementById('viewerContainer');
    this.pageViewScroll = {};
    this.watchScroll(container, this.pageViewScroll, updateViewarea);

    var thumbnailContainer = this.thumbnailContainer =
                             document.getElementById('thumbnailView');
    this.thumbnailViewScroll = {};
    this.watchScroll(thumbnailContainer, this.thumbnailViewScroll,
                     this.renderHighestPriority.bind(this));

    this.initialized = true;
    container.addEventListener('scroll', function() {
      self.lastScroll = Date.now();
    }, false);
  },

  // Helper function to keep track whether a div was scrolled up or down and
  // then call a callback.
  watchScroll: function pdfViewWatchScroll(viewAreaElement, state, callback) {
    state.down = true;
    state.lastY = viewAreaElement.scrollTop;
    viewAreaElement.addEventListener('scroll', function webViewerScroll(evt) {
      var currentY = viewAreaElement.scrollTop;
      var lastY = state.lastY;
      if (currentY > lastY)
        state.down = true;
      else if (currentY < lastY)
        state.down = false;
      // else do nothing and use previous value
      state.lastY = currentY;
      callback();
    }, true);
  },

  setScale: function pdfViewSetScale(val, resetAutoSettings, noScroll) {
    if (val == this.currentScale)
      return;

    var pages = this.pages;
    for (var i = 0; i < pages.length; i++)
      pages[i].update(val * kCssUnits);

    if (!noScroll && this.currentScale != val)
      this.pages[this.page - 1].scrollIntoView();
    this.currentScale = val;

    var event = document.createEvent('UIEvents');
    event.initUIEvent('scalechange', false, false, window, 0);
    event.scale = val;
    event.resetAutoSettings = resetAutoSettings;
    window.dispatchEvent(event);
  },

  parseScale: function pdfViewParseScale(value, resetAutoSettings, noScroll) {
    if ('custom' == value)
      return;

    var scale = parseFloat(value);
    this.currentScaleValue = value;
    if (scale) {
      this.setScale(scale, true, noScroll);
      return;
    }

    var container = this.container;
    var currentPage = this.pages[this.page - 1];

    var pageWidthScale = (container.clientWidth - kScrollbarPadding) /
                          currentPage.width * currentPage.scale / kCssUnits;
    var pageHeightScale = (container.clientHeight - kScrollbarPadding) /
                           currentPage.height * currentPage.scale / kCssUnits;
    switch (value) {
      case 'page-actual':
        scale = 1;
        break;
      case 'page-width':
        scale = pageWidthScale;
        break;
      case 'page-height':
        scale = pageHeightScale;
        break;
      case 'page-fit':
        scale = Math.min(pageWidthScale, pageHeightScale);
        break;
      case 'auto':
        scale = Math.min(1.0, pageWidthScale);
        break;
    }
    this.setScale(scale, resetAutoSettings, noScroll);

    selectScaleOption(value);
  },

  zoomIn: function pdfViewZoomIn() {
    var newScale = (this.currentScale * kDefaultScaleDelta).toFixed(2);
    newScale = Math.min(kMaxScale, newScale);
    this.parseScale(newScale, true);
  },

  zoomOut: function pdfViewZoomOut() {
    var newScale = (this.currentScale / kDefaultScaleDelta).toFixed(2);
    newScale = Math.max(kMinScale, newScale);
    this.parseScale(newScale, true);
  },

  set page(val) {
    var pages = this.pages;
    var input = document.getElementById('pageNumber');
    var event = document.createEvent('UIEvents');
    event.initUIEvent('pagechange', false, false, window, 0);

    if (!(0 < val && val <= pages.length)) {
      event.pageNumber = this.page;
      window.dispatchEvent(event);
      return;
    }

    pages[val - 1].updateStats();
    currentPageNumber = val;
    event.pageNumber = val;
    window.dispatchEvent(event);

    // checking if the this.page was called from the updateViewarea function:
    // avoiding the creation of two "set page" method (internal and public)
    if (updateViewarea.inProgress)
      return;

    // Avoid scrolling the first page during loading
    if (this.loading && val == 1)
      return;

    pages[val - 1].scrollIntoView();
  },

  get page() {
    return currentPageNumber;
  },

  get supportsPrinting() {
    var canvas = document.createElement('canvas');
    var value = 'mozPrintCallback' in canvas;
    // shadow
    Object.defineProperty(this, 'supportsPrinting', { value: value,
                                                      enumerable: true,
                                                      configurable: true,
                                                      writable: false });
    return value;
  },

  get supportsFullscreen() {
    var doc = document.documentElement;
    var support = doc.requestFullscreen || doc.mozRequestFullScreen ||
                  doc.webkitRequestFullScreen;
    Object.defineProperty(this, 'supportsFullScreen', { value: support,
                                                        enumerable: true,
                                                        configurable: true,
                                                        writable: false });
    return support;
  },

  initPassiveLoading: function pdfViewInitPassiveLoading() {
    if (!PDFView.loadingBar) {
      PDFView.loadingBar = new ProgressBar('#loadingBar', {});
    }

    window.addEventListener('message', function window_message(e) {
      var args = e.data;

      if (typeof args !== 'object' || !('pdfjsLoadAction' in args))
        return;
      switch (args.pdfjsLoadAction) {
        case 'progress':
          PDFView.progress(args.loaded / args.total);
          break;
        case 'complete':
          if (!args.data) {
            PDFView.error(mozL10n.get('loading_error', null,
                          'An error occurred while loading the PDF.'), e);
            break;
          }
          PDFView.open(args.data, 0);
          break;
      }
    });
    FirefoxCom.requestSync('initPassiveLoading', null);
  },

  setTitleUsingUrl: function pdfViewSetTitleUsingUrl(url) {
    this.url = url;
    try {
      document.title = decodeURIComponent(getFileName(url)) || url;
    } catch (e) {
      // decodeURIComponent may throw URIError,
      // fall back to using the unprocessed url in that case
      document.title = url;
    }
  },

  open: function pdfViewOpen(url, scale, password) {
    var parameters = {password: password};
    if (typeof url === 'string') { // URL
      this.setTitleUsingUrl(url);
      parameters.url = url;
    } else if (url && 'byteLength' in url) { // ArrayBuffer
      parameters.data = url;
    }

    if (!PDFView.loadingBar) {
      PDFView.loadingBar = new ProgressBar('#loadingBar', {});
    }

    this.pdfDocument = null;
    var self = this;
    self.loading = true;
    PDFJS.getDocument(parameters).then(
      function getDocumentCallback(pdfDocument) {
        self.load(pdfDocument, scale);
        self.loading = false;
      },
      function getDocumentError(message, exception) {
        if (exception && exception.name === 'PasswordException') {
          if (exception.code === 'needpassword') {
            var promptString = mozL10n.get('request_password', null,
                                      'PDF is protected by a password:');
            password = prompt(promptString);
            if (password && password.length > 0) {
              return PDFView.open(url, scale, password);
            }
          }
        }

        var loadingIndicator = document.getElementById('loading');
        loadingIndicator.textContent = mozL10n.get('loading_error_indicator',
          null, 'Error');
        var moreInfo = {
          message: message
        };
        self.error(mozL10n.get('loading_error', null,
          'An error occurred while loading the PDF.'), moreInfo);
        self.loading = false;
      },
      function getDocumentProgress(progressData) {
        self.progress(progressData.loaded / progressData.total);
      }
    );
  },

  download: function pdfViewDownload() {
    function noData() {
      FirefoxCom.request('download', { originalUrl: url });
    }
    var url = this.url.split('#')[0];
    url += '#pdfjs.action=download';
    window.open(url, '_parent');
  },

  fallback: function pdfViewFallback() {
    return;
  },

  navigateTo: function pdfViewNavigateTo(dest) {
    if (typeof dest === 'string')
      dest = this.destinations[dest];
    if (!(dest instanceof Array))
      return; // invalid destination
    // dest array looks like that: <page-ref> </XYZ|FitXXX> <args..>
    var destRef = dest[0];
    var pageNumber = destRef instanceof Object ?
      this.pagesRefMap[destRef.num + ' ' + destRef.gen + ' R'] : (destRef + 1);
    if (pageNumber > this.pages.length)
      pageNumber = this.pages.length;
    if (pageNumber) {
      this.page = pageNumber;
      var currentPage = this.pages[pageNumber - 1];
      currentPage.scrollIntoView(dest);
    }
  },

  getDestinationHash: function pdfViewGetDestinationHash(dest) {
    if (typeof dest === 'string')
      return PDFView.getAnchorUrl('#' + escape(dest));
    if (dest instanceof Array) {
      var destRef = dest[0]; // see navigateTo method for dest format
      var pageNumber = destRef instanceof Object ?
        this.pagesRefMap[destRef.num + ' ' + destRef.gen + ' R'] :
        (destRef + 1);
      if (pageNumber) {
        var pdfOpenParams = PDFView.getAnchorUrl('#page=' + pageNumber);
        var destKind = dest[1];
        if (typeof destKind === 'object' && 'name' in destKind &&
            destKind.name == 'XYZ') {
          var scale = (dest[4] || this.currentScale);
          pdfOpenParams += '&zoom=' + (scale * 100);
          if (dest[2] || dest[3]) {
            pdfOpenParams += ',' + (dest[2] || 0) + ',' + (dest[3] || 0);
          }
        }
        return pdfOpenParams;
      }
    }
    return '';
  },

  /**
   * For the firefox extension we prefix the full url on anchor links so they
   * don't come up as resource:// urls and so open in new tab/window works.
   * @param {String} anchor The anchor hash include the #.
   */
  getAnchorUrl: function getAnchorUrl(anchor) {
    return anchor;
  },

  /**
   * Show the error box.
   * @param {String} message A message that is human readable.
   * @param {Object} moreInfo (optional) Further information about the error
   *                            that is more technical.  Should have a 'message'
   *                            and optionally a 'stack' property.
   */
  error: function pdfViewError(message, moreInfo) {
    var moreInfoText = mozL10n.get('error_build', {build: PDFJS.build},
      'PDF.JS Build: {{build}}') + '\n';
    if (moreInfo) {
      moreInfoText +=
        mozL10n.get('error_message', {message: moreInfo.message},
        'Message: {{message}}');
      if (moreInfo.stack) {
        moreInfoText += '\n' +
          mozL10n.get('error_stack', {stack: moreInfo.stack},
          'Stack: {{stack}}');
      } else {
        if (moreInfo.filename) {
          moreInfoText += '\n' +
            mozL10n.get('error_file', {file: moreInfo.filename},
            'File: {{file}}');
        }
        if (moreInfo.lineNumber) {
          moreInfoText += '\n' +
            mozL10n.get('error_line', {line: moreInfo.lineNumber},
            'Line: {{line}}');
        }
      }
    }

    var loadingBox = document.getElementById('loadingBox');
    loadingBox.setAttribute('hidden', 'true');

    var errorWrapper = document.getElementById('errorWrapper');
    errorWrapper.removeAttribute('hidden');

    var errorMessage = document.getElementById('errorMessage');
    errorMessage.textContent = message;

    var closeButton = document.getElementById('errorClose');
    closeButton.onclick = function() {
      errorWrapper.setAttribute('hidden', 'true');
    };

    var errorMoreInfo = document.getElementById('errorMoreInfo');
    var moreInfoButton = document.getElementById('errorShowMore');
    var lessInfoButton = document.getElementById('errorShowLess');
    moreInfoButton.onclick = function() {
      errorMoreInfo.removeAttribute('hidden');
      moreInfoButton.setAttribute('hidden', 'true');
      lessInfoButton.removeAttribute('hidden');
    };
    lessInfoButton.onclick = function() {
      errorMoreInfo.setAttribute('hidden', 'true');
      moreInfoButton.removeAttribute('hidden');
      lessInfoButton.setAttribute('hidden', 'true');
    };
    moreInfoButton.removeAttribute('hidden');
    lessInfoButton.setAttribute('hidden', 'true');
    errorMoreInfo.value = moreInfoText;

    errorMoreInfo.rows = moreInfoText.split('\n').length - 1;
  },

  progress: function pdfViewProgress(level) {
    var percent = Math.round(level * 100);
    PDFView.loadingBar.percent = percent;
  },

  load: function pdfViewLoad(pdfDocument, scale) {
    function bindOnAfterDraw(pageView, thumbnailView) {
      // when page is painted, using the image as thumbnail base
      pageView.onAfterDraw = function pdfViewLoadOnAfterDraw() {
        thumbnailView.setImage(pageView.canvas);
      };
    }

    this.pdfDocument = pdfDocument;

    var errorWrapper = document.getElementById('errorWrapper');
    errorWrapper.setAttribute('hidden', 'true');

    var loadingBox = document.getElementById('loadingBox');
    loadingBox.setAttribute('hidden', 'true');
    var loadingIndicator = document.getElementById('loading');
    loadingIndicator.textContent = '';

    var thumbsView = document.getElementById('thumbnailView');
    thumbsView.parentNode.scrollTop = 0;

    while (thumbsView.hasChildNodes())
      thumbsView.removeChild(thumbsView.lastChild);

    if ('_loadingInterval' in thumbsView)
      clearInterval(thumbsView._loadingInterval);

    var container = document.getElementById('viewer');
    while (container.hasChildNodes())
      container.removeChild(container.lastChild);

    var pagesCount = pdfDocument.numPages;
    var id = pdfDocument.fingerprint;
    document.getElementById('numPages').textContent =
      mozL10n.get('page_of', {pageCount: pagesCount}, 'of {{pageCount}}');
    document.getElementById('pageNumber').max = pagesCount;
    PDFView.documentFingerprint = id;
    var store = PDFView.store = new Settings(id);
    var storePromise = store.initializedPromise;

    this.pageRotation = 0;

    var pages = this.pages = [];
    this.pageText = [];
    this.startedTextExtraction = false;
    var pagesRefMap = {};
    var thumbnails = this.thumbnails = [];
    var pagePromises = [];
    for (var i = 1; i <= pagesCount; i++)
      pagePromises.push(pdfDocument.getPage(i));
    var self = this;
    var pagesPromise = PDFJS.Promise.all(pagePromises);
    pagesPromise.then(function(promisedPages) {
      for (var i = 1; i <= pagesCount; i++) {
        var page = promisedPages[i - 1];
        var pageView = new PageView(container, page, i, scale,
                                    page.stats, self.navigateTo.bind(self));
        var thumbnailView = new ThumbnailView(thumbsView, page, i);
        bindOnAfterDraw(pageView, thumbnailView);

        pages.push(pageView);
        thumbnails.push(thumbnailView);
        var pageRef = page.ref;
        pagesRefMap[pageRef.num + ' ' + pageRef.gen + ' R'] = i;
      }

      self.pagesRefMap = pagesRefMap;
    });

    var destinationsPromise = pdfDocument.getDestinations();
    destinationsPromise.then(function(destinations) {
      self.destinations = destinations;
    });

    // outline and initial view depends on destinations and pagesRefMap
    var promises = [pagesPromise, destinationsPromise, storePromise];
    PDFJS.Promise.all(promises).then(function() {
      pdfDocument.getOutline().then(function(outline) {
        self.outline = new DocumentOutlineView(outline);
      });

      var storedHash = null;
      if (store.get('exists', false)) {
        var page = store.get('page', '1');
        var zoom = store.get('zoom', PDFView.currentScale);
        var left = store.get('scrollLeft', '0');
        var top = store.get('scrollTop', '0');

        storedHash = 'page=' + page + '&zoom=' + zoom + ',' + left + ',' + top;
      }

      self.setInitialView(storedHash, scale);
    });

    pdfDocument.getMetadata().then(function(data) {
      var info = data.info, metadata = data.metadata;
      self.documentInfo = info;
      self.metadata = metadata;

      var pdfTitle;
      if (metadata) {
        if (metadata.has('dc:title'))
          pdfTitle = metadata.get('dc:title');
      }

      if (!pdfTitle && info && info['Title'])
        pdfTitle = info['Title'];

      if (pdfTitle)
        document.title = pdfTitle + ' - ' + document.title;
    });
  },

  setInitialView: function pdfViewSetInitialView(storedHash, scale) {
    // Reset the current scale, as otherwise the page's scale might not get
    // updated if the zoom level stayed the same.
    this.currentScale = 0;
    this.currentScaleValue = null;
    if (this.initialBookmark) {
      this.setHash(this.initialBookmark);
      this.initialBookmark = null;
    }
    else if (storedHash)
      this.setHash(storedHash);
    else if (scale) {
      this.parseScale(scale, true);
      this.page = 1;
    }

    if (PDFView.currentScale === kUnknownScale) {
      // Scale was not initialized: invalid bookmark or scale was not specified.
      // Setting the default one.
      this.parseScale(kDefaultScale, true);
    }
  },

  renderHighestPriority: function pdfViewRenderHighestPriority() {
    // Pages have a higher priority than thumbnails, so check them first.
    var visiblePages = this.getVisiblePages();
    var pageView = this.getHighestPriority(visiblePages, this.pages,
                                           this.pageViewScroll.down);
    if (pageView) {
      this.renderView(pageView, 'page');
      return;
    }
    // No pages needed rendering so check thumbnails.
    if (this.sidebarOpen) {
      var visibleThumbs = this.getVisibleThumbs();
      var thumbView = this.getHighestPriority(visibleThumbs,
                                              this.thumbnails,
                                              this.thumbnailViewScroll.down);
      if (thumbView)
        this.renderView(thumbView, 'thumbnail');
    }
  },

  getHighestPriority: function pdfViewGetHighestPriority(visible, views,
                                                         scrolledDown) {
    // The state has changed figure out which page has the highest priority to
    // render next (if any).
    // Priority:
    // 1 visible pages
    // 2 if last scrolled down page after the visible pages
    // 2 if last scrolled up page before the visible pages
    var visibleViews = visible.views;

    var numVisible = visibleViews.length;
    if (numVisible === 0) {
      return false;
    }
    for (var i = 0; i < numVisible; ++i) {
      var view = visibleViews[i].view;
      if (!this.isViewFinished(view))
        return view;
    }

    // All the visible views have rendered, try to render next/previous pages.
    if (scrolledDown) {
      var nextPageIndex = visible.last.id;
      // ID's start at 1 so no need to add 1.
      if (views[nextPageIndex] && !this.isViewFinished(views[nextPageIndex]))
        return views[nextPageIndex];
    } else {
      var previousPageIndex = visible.first.id - 2;
      if (views[previousPageIndex] &&
          !this.isViewFinished(views[previousPageIndex]))
        return views[previousPageIndex];
    }
    // Everything that needs to be rendered has been.
    return false;
  },

  isViewFinished: function pdfViewNeedsRendering(view) {
    return view.renderingState === RenderingStates.FINISHED;
  },

  // Render a page or thumbnail view. This calls the appropriate function based
  // on the views state. If the view is already rendered it will return false.
  renderView: function pdfViewRender(view, type) {
    var state = view.renderingState;
    switch (state) {
      case RenderingStates.FINISHED:
        return false;
      case RenderingStates.PAUSED:
        PDFView.highestPriorityPage = type + view.id;
        view.resume();
        break;
      case RenderingStates.RUNNING:
        PDFView.highestPriorityPage = type + view.id;
        break;
      case RenderingStates.INITIAL:
        PDFView.highestPriorityPage = type + view.id;
        view.draw(this.renderHighestPriority.bind(this));
        break;
    }
    return true;
  },

  search: function pdfViewStartSearch() {
    // Limit this function to run every <SEARCH_TIMEOUT>ms.
    var SEARCH_TIMEOUT = 250;
    var lastSearch = this.lastSearch;
    var now = Date.now();
    if (lastSearch && (now - lastSearch) < SEARCH_TIMEOUT) {
      if (!this.searchTimer) {
        this.searchTimer = setTimeout(function resumeSearch() {
            PDFView.search();
          },
          SEARCH_TIMEOUT - (now - lastSearch)
        );
      }
      return;
    }
    this.searchTimer = null;
    this.lastSearch = now;

    function bindLink(link, pageNumber) {
      link.href = '#' + pageNumber;
      link.onclick = function searchBindLink() {
        PDFView.page = pageNumber;
        return false;
      };
    }

    var searchResults = document.getElementById('searchResults');

    var searchTermsInput = document.getElementById('searchTermsInput');
    searchResults.removeAttribute('hidden');
    searchResults.textContent = '';

    var terms = searchTermsInput.value;

    if (!terms)
      return;

    // simple search: removing spaces and hyphens, then scanning every
    terms = terms.replace(/\s-/g, '').toLowerCase();
    var index = PDFView.pageText;
    var pageFound = false;
    for (var i = 0, ii = index.length; i < ii; i++) {
      var pageText = index[i].replace(/\s-/g, '').toLowerCase();
      var j = pageText.indexOf(terms);
      if (j < 0)
        continue;

      var pageNumber = i + 1;
      var textSample = index[i].substr(j, 50);
      var link = document.createElement('a');
      bindLink(link, pageNumber);
      link.textContent = 'Page ' + pageNumber + ': ' + textSample;
      searchResults.appendChild(link);

      pageFound = true;
    }
    if (!pageFound) {
      searchResults.textContent = '';
      var noResults = document.createElement('div');
      noResults.classList.add('noResults');
      noResults.textContent = mozL10n.get('search_terms_not_found', null,
                                              '(Not found)');
      searchResults.appendChild(noResults);
    }
  },

  setHash: function pdfViewSetHash(hash) {
    if (!hash)
      return;

    if (hash.indexOf('=') >= 0) {
      var params = PDFView.parseQueryString(hash);
      // borrowing syntax from "Parameters for Opening PDF Files"
      if ('nameddest' in params) {
        PDFView.navigateTo(params.nameddest);
        return;
      }
      if ('page' in params) {
        var pageNumber = (params.page | 0) || 1;
        if ('zoom' in params) {
          var zoomArgs = params.zoom.split(','); // scale,left,top
          // building destination array

          // If the zoom value, it has to get divided by 100. If it is a string,
          // it should stay as it is.
          var zoomArg = zoomArgs[0];
          var zoomArgNumber = parseFloat(zoomArg);
          if (zoomArgNumber)
            zoomArg = zoomArgNumber / 100;

          var dest = [null, {name: 'XYZ'}, (zoomArgs[1] | 0),
            (zoomArgs[2] | 0), zoomArg];
          var currentPage = this.pages[pageNumber - 1];
          currentPage.scrollIntoView(dest);
        } else {
          this.page = pageNumber; // simple page
        }
      }
    } else if (/^\d+$/.test(hash)) // page number
      this.page = hash;
    else // named destination
      PDFView.navigateTo(unescape(hash));
  },

  switchSidebarView: function pdfViewSwitchSidebarView(view) {
    var thumbsView = document.getElementById('thumbnailView');
    var outlineView = document.getElementById('outlineView');
    var searchView = document.getElementById('searchView');

    var thumbsButton = document.getElementById('viewThumbnail');
    var outlineButton = document.getElementById('viewOutline');
    var searchButton = document.getElementById('viewSearch');

    switch (view) {
      case 'thumbs':
        thumbsButton.classList.add('toggled');
        outlineButton.classList.remove('toggled');
        searchButton.classList.remove('toggled');
        thumbsView.classList.remove('hidden');
        outlineView.classList.add('hidden');
        searchView.classList.add('hidden');

        PDFView.renderHighestPriority();
        break;

      case 'outline':
        thumbsButton.classList.remove('toggled');
        outlineButton.classList.add('toggled');
        searchButton.classList.remove('toggled');
        thumbsView.classList.add('hidden');
        outlineView.classList.remove('hidden');
        searchView.classList.add('hidden');

        if (outlineButton.getAttribute('disabled'))
          return;
        break;

      case 'search':
        thumbsButton.classList.remove('toggled');
        outlineButton.classList.remove('toggled');
        searchButton.classList.add('toggled');
        thumbsView.classList.add('hidden');
        outlineView.classList.add('hidden');
        searchView.classList.remove('hidden');

        var searchTermsInput = document.getElementById('searchTermsInput');
        searchTermsInput.focus();
        // Start text extraction as soon as the search gets displayed.
        this.extractText();
        break;
    }
  },

  extractText: function() {
    if (this.startedTextExtraction)
      return;
    this.startedTextExtraction = true;
    var self = this;
    function extractPageText(pageIndex) {
      self.pages[pageIndex].pdfPage.getTextContent().then(
        function textContentResolved(textContent) {
          self.pageText[pageIndex] = textContent.join('');
          self.search();
          if ((pageIndex + 1) < self.pages.length)
            extractPageText(pageIndex + 1);
        }
      );
    }
    extractPageText(0);
  },

  getVisiblePages: function pdfViewGetVisiblePages() {
    return this.getVisibleElements(this.container,
                                   this.pages, true);
  },

  getVisibleThumbs: function pdfViewGetVisibleThumbs() {
    return this.getVisibleElements(this.thumbnailContainer,
                                   this.thumbnails);
  },

  // Generic helper to find out what elements are visible within a scroll pane.
  getVisibleElements: function pdfViewGetVisibleElements(
      scrollEl, views, sortByVisibility) {
    var currentHeight = 0, view;
    var top = scrollEl.scrollTop;

    for (var i = 1, ii = views.length; i <= ii; ++i) {
      view = views[i - 1];
      currentHeight = view.el.offsetTop;
      if (currentHeight + view.el.clientHeight > top)
        break;
      currentHeight += view.el.clientHeight;
    }

    var visible = [];

    // Algorithm broken in fullscreen mode
    if (this.isFullscreen) {
      var currentPage = this.pages[this.page - 1];
      visible.push({
        id: currentPage.id,
        view: currentPage
      });

      return { first: currentPage, last: currentPage, views: visible};
    }

    var bottom = top + scrollEl.clientHeight;
    var nextHeight, hidden, percent, viewHeight;
    for (; i <= ii && currentHeight < bottom; ++i) {
      view = views[i - 1];
      viewHeight = view.el.clientHeight;
      currentHeight = view.el.offsetTop;
      nextHeight = currentHeight + viewHeight;
      hidden = Math.max(0, top - currentHeight) +
               Math.max(0, nextHeight - bottom);
      percent = Math.floor((viewHeight - hidden) * 100.0 / viewHeight);
      visible.push({ id: view.id, y: currentHeight,
                     view: view, percent: percent });
      currentHeight = nextHeight;
    }

    var first = visible[0];
    var last = visible[visible.length - 1];

    if (sortByVisibility) {
      visible.sort(function(a, b) {
        var pc = a.percent - b.percent;
        if (Math.abs(pc) > 0.001)
          return -pc;

        return a.id - b.id; // ensure stability
      });
    }

    return {first: first, last: last, views: visible};
  },

  // Helper function to parse query string (e.g. ?param1=value&parm2=...).
  parseQueryString: function pdfViewParseQueryString(query) {
    var parts = query.split('&');
    var params = {};
    for (var i = 0, ii = parts.length; i < parts.length; ++i) {
      var param = parts[i].split('=');
      var key = param[0];
      var value = param.length > 1 ? param[1] : null;
      params[unescape(key)] = unescape(value);
    }
    return params;
  },

  beforePrint: function pdfViewSetupBeforePrint() {
    if (!this.supportsPrinting) {
      var printMessage = mozL10n.get('printing_not_supported', null,
          'Warning: Printing is not fully supported by this browser.');
      this.error(printMessage);
      return;
    }
    var body = document.querySelector('body');
    body.setAttribute('data-mozPrintCallback', true);
    for (var i = 0, ii = this.pages.length; i < ii; ++i) {
      this.pages[i].beforePrint();
    }
  },

  afterPrint: function pdfViewSetupAfterPrint() {
    var div = document.getElementById('printContainer');
    while (div.hasChildNodes())
      div.removeChild(div.lastChild);
  },

  fullscreen: function pdfViewFullscreen() {
    var isFullscreen = document.fullscreenElement || document.mozFullScreen ||
        document.webkitIsFullScreen;

    if (isFullscreen) {
      return false;
    }

    var wrapper = document.getElementById('viewerContainer');
    if (document.documentElement.requestFullscreen) {
      wrapper.requestFullscreen();
    } else if (document.documentElement.mozRequestFullScreen) {
      wrapper.mozRequestFullScreen();
    } else if (document.documentElement.webkitRequestFullScreen) {
      wrapper.webkitRequestFullScreen(Element.ALLOW_KEYBOARD_INPUT);
    } else {
      return false;
    }

    this.isFullscreen = true;
    var currentPage = this.pages[this.page - 1];
    this.previousScale = this.currentScaleValue;
    this.parseScale('page-fit', true);

    // Wait for fullscreen to take effect
    setTimeout(function() {
      currentPage.scrollIntoView();
    }, 0);

    return true;
  },

  exitFullscreen: function pdfViewExitFullscreen() {
    this.isFullscreen = false;
    this.parseScale(this.previousScale);
    this.page = this.page;
  },

  rotatePages: function pdfViewPageRotation(delta) {

    this.pageRotation = (this.pageRotation + 360 + delta) % 360;

    for (var i = 0, l = this.pages.length; i < l; i++) {
      var page = this.pages[i];
      page.update(page.scale, this.pageRotation);
    }

    for (var i = 0, l = this.thumbnails.length; i < l; i++) {
      var thumb = this.thumbnails[i];
      thumb.updateRotation(this.pageRotation);
    }

    var currentPage = this.pages[this.page - 1];

    this.parseScale(this.currentScaleValue, true);

    this.renderHighestPriority();

    // Wait for fullscreen to take effect
    setTimeout(function() {
      currentPage.scrollIntoView();
    }, 0);
  }
};

var PageView = function pageView(container, pdfPage, id, scale,
                                 stats, navigateTo) {
  this.id = id;
  this.pdfPage = pdfPage;

  this.rotation = 0;
  this.scale = scale || 1.0;
  this.viewport = this.pdfPage.getViewport(this.scale, this.pdfPage.rotate);

  this.renderingState = RenderingStates.INITIAL;
  this.resume = null;

  this.textContent = null;

  var anchor = document.createElement('a');
  anchor.name = '' + this.id;

  var div = this.el = document.createElement('div');
  div.id = 'pageContainer' + this.id;
  div.className = 'page';
  div.style.width = this.viewport.width + 'px';
  div.style.height = this.viewport.height + 'px';

  container.appendChild(anchor);
  container.appendChild(div);

  this.destroy = function pageViewDestroy() {
    this.update();
    this.pdfPage.destroy();
  };

  this.update = function pageViewUpdate(scale, rotation) {
    this.renderingState = RenderingStates.INITIAL;
    this.resume = null;

    if (typeof rotation !== 'undefined') {
      this.rotation = rotation;
    }

    this.scale = scale || this.scale;

    var totalRotation = (this.rotation + this.pdfPage.rotate) % 360;
    var viewport = this.pdfPage.getViewport(this.scale, totalRotation);

    this.viewport = viewport;
    div.style.width = viewport.width + 'px';
    div.style.height = viewport.height + 'px';

    while (div.hasChildNodes())
      div.removeChild(div.lastChild);
    div.removeAttribute('data-loaded');

    delete this.canvas;

    this.loadingIconDiv = document.createElement('div');
    this.loadingIconDiv.className = 'loadingIcon';
    div.appendChild(this.loadingIconDiv);
  };

  Object.defineProperty(this, 'width', {
    get: function PageView_getWidth() {
      return this.viewport.width;
    },
    enumerable: true
  });

  Object.defineProperty(this, 'height', {
    get: function PageView_getHeight() {
      return this.viewport.height;
    },
    enumerable: true
  });

  function setupAnnotations(pdfPage, viewport) {
    function bindLink(link, dest) {
      link.href = PDFView.getDestinationHash(dest);
      link.onclick = function pageViewSetupLinksOnclick() {
        if (dest)
          PDFView.navigateTo(dest);
        return false;
      };
    }
    function createElementWithStyle(tagName, item) {
      var rect = viewport.convertToViewportRectangle(item.rect);
      rect = PDFJS.Util.normalizeRect(rect);
      var element = document.createElement(tagName);
      element.style.left = Math.floor(rect[0]) + 'px';
      element.style.top = Math.floor(rect[1]) + 'px';
      element.style.width = Math.ceil(rect[2] - rect[0]) + 'px';
      element.style.height = Math.ceil(rect[3] - rect[1]) + 'px';
      return element;
    }
    function createCommentAnnotation(type, item) {
      var container = document.createElement('section');
      container.className = 'annotComment';

      var image = createElementWithStyle('img', item);
      var type = item.type;
      var rect = viewport.convertToViewportRectangle(item.rect);
      rect = PDFJS.Util.normalizeRect(rect);
      image.src = kImageDirectory + 'annotation-' + type.toLowerCase() + '.svg';
      image.alt = mozL10n.get('text_annotation_type', {type: type},
        '[{{type}} Annotation]');
      var content = document.createElement('div');
      content.setAttribute('hidden', true);
      var title = document.createElement('h1');
      var text = document.createElement('p');
      content.style.left = Math.floor(rect[2]) + 'px';
      content.style.top = Math.floor(rect[1]) + 'px';
      title.textContent = item.title;

      if (!item.content && !item.title) {
        content.setAttribute('hidden', true);
      } else {
        var e = document.createElement('span');
        var lines = item.content.split('\n');
        for (var i = 0, ii = lines.length; i < ii; ++i) {
          var line = lines[i];
          e.appendChild(document.createTextNode(line));
          if (i < (ii - 1))
            e.appendChild(document.createElement('br'));
        }
        text.appendChild(e);
        image.addEventListener('mouseover', function annotationImageOver() {
           content.removeAttribute('hidden');
        }, false);

        image.addEventListener('mouseout', function annotationImageOut() {
           content.setAttribute('hidden', true);
        }, false);
      }

      content.appendChild(title);
      content.appendChild(text);
      container.appendChild(image);
      container.appendChild(content);

      return container;
    }

    pdfPage.getAnnotations().then(function(items) {
      for (var i = 0; i < items.length; i++) {
        var item = items[i];
        switch (item.type) {
          case 'Link':
            var link = createElementWithStyle('a', item);
            link.href = item.url || '';
            if (!item.url)
              bindLink(link, ('dest' in item) ? item.dest : null);
            div.appendChild(link);
            break;
          case 'Text':
            var comment = createCommentAnnotation(item.name, item);
            if (comment)
              div.appendChild(comment);
            break;
          case 'Widget':
            // TODO: support forms
            PDFView.fallback();
            break;
        }
      }
    });
  }

  this.getPagePoint = function pageViewGetPagePoint(x, y) {
    return this.viewport.convertToPdfPoint(x, y);
  };

  this.scrollIntoView = function pageViewScrollIntoView(dest) {
      if (!dest) {
        scrollIntoView(div);
        return;
      }

      var x = 0, y = 0;
      var width = 0, height = 0, widthScale, heightScale;
      var scale = 0;
      switch (dest[1].name) {
        case 'XYZ':
          x = dest[2];
          y = dest[3];
          scale = dest[4];
          break;
        case 'Fit':
        case 'FitB':
          scale = 'page-fit';
          break;
        case 'FitH':
        case 'FitBH':
          y = dest[2];
          scale = 'page-width';
          break;
        case 'FitV':
        case 'FitBV':
          x = dest[2];
          scale = 'page-height';
          break;
        case 'FitR':
          x = dest[2];
          y = dest[3];
          width = dest[4] - x;
          height = dest[5] - y;
          widthScale = (this.container.clientWidth - kScrollbarPadding) /
            width / kCssUnits;
          heightScale = (this.container.clientHeight - kScrollbarPadding) /
            height / kCssUnits;
          scale = Math.min(widthScale, heightScale);
          break;
        default:
          return;
      }

      if (scale && scale !== PDFView.currentScale)
        PDFView.parseScale(scale, true, true);
      else if (PDFView.currentScale === kUnknownScale)
        PDFView.parseScale(kDefaultScale, true, true);

      var boundingRect = [
        this.viewport.convertToViewportPoint(x, y),
        this.viewport.convertToViewportPoint(x + width, y + height)
      ];
      setTimeout(function pageViewScrollIntoViewRelayout() {
        // letting page to re-layout before scrolling
        var scale = PDFView.currentScale;
        var x = Math.min(boundingRect[0][0], boundingRect[1][0]);
        var y = Math.min(boundingRect[0][1], boundingRect[1][1]);
        var width = Math.abs(boundingRect[0][0] - boundingRect[1][0]);
        var height = Math.abs(boundingRect[0][1] - boundingRect[1][1]);

        scrollIntoView(div, {left: x, top: y, width: width, height: height});
      }, 0);
  };

  this.getTextContent = function pageviewGetTextContent() {
    if (!this.textContent) {
      this.textContent = this.pdfPage.getTextContent();
    }
    return this.textContent;
  };

  this.draw = function pageviewDraw(callback) {
    if (this.renderingState !== RenderingStates.INITIAL)
      error('Must be in new state before drawing');

    this.renderingState = RenderingStates.RUNNING;

    var canvas = document.createElement('canvas');
    canvas.id = 'page' + this.id;
    canvas.mozOpaque = true;
    div.appendChild(canvas);
    this.canvas = canvas;

    var textLayerDiv = null;
    if (!PDFJS.disableTextLayer) {
      textLayerDiv = document.createElement('div');
      textLayerDiv.className = 'textLayer';
      div.appendChild(textLayerDiv);
    }
    var textLayer = textLayerDiv ? new TextLayerBuilder(textLayerDiv) : null;

    var scale = this.scale, viewport = this.viewport;
    canvas.width = viewport.width;
    canvas.height = viewport.height;

    var ctx = canvas.getContext('2d');
    ctx.save();
    ctx.fillStyle = 'rgb(255, 255, 255)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.restore();

    // Rendering area

    var self = this;
    function pageViewDrawCallback(error) {
      self.renderingState = RenderingStates.FINISHED;

      if (self.loadingIconDiv) {
        div.removeChild(self.loadingIconDiv);
        delete self.loadingIconDiv;
      }

      if (error) {
        PDFView.error(mozL10n.get('rendering_error', null,
          'An error occurred while rendering the page.'), error);
      }

      self.stats = pdfPage.stats;
      self.updateStats();
      if (self.onAfterDraw)
        self.onAfterDraw();

      cache.push(self);
      callback();
    }

    var renderContext = {
      canvasContext: ctx,
      viewport: this.viewport,
      textLayer: textLayer,
      continueCallback: function pdfViewcContinueCallback(cont) {
        if (PDFView.highestPriorityPage !== 'page' + self.id) {
          self.renderingState = RenderingStates.PAUSED;
          self.resume = function resumeCallback() {
            self.renderingState = RenderingStates.RUNNING;
            cont();
          };
          return;
        }
        cont();
      }
    };
    this.pdfPage.render(renderContext).then(
      function pdfPageRenderCallback() {
        pageViewDrawCallback(null);
      },
      function pdfPageRenderError(error) {
        pageViewDrawCallback(error);
      }
    );

    if (textLayer) {
      this.getTextContent().then(
        function textContentResolved(textContent) {
          textLayer.setTextContent(textContent);
        }
      );
    }

    setupAnnotations(this.pdfPage, this.viewport);
    div.setAttribute('data-loaded', true);
  };

  this.beforePrint = function pageViewBeforePrint() {
    var pdfPage = this.pdfPage;
    var viewport = pdfPage.getViewport(1);

    var canvas = this.canvas = document.createElement('canvas');
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    canvas.style.width = viewport.width + 'pt';
    canvas.style.height = viewport.height + 'pt';

    var printContainer = document.getElementById('printContainer');
    printContainer.appendChild(canvas);

    var self = this;
    canvas.mozPrintCallback = function(obj) {
      var ctx = obj.context;
      var renderContext = {
        canvasContext: ctx,
        viewport: viewport
      };

      pdfPage.render(renderContext).then(function() {
        // Tell the printEngine that rendering this canvas/page has finished.
        obj.done();
        self.pdfPage.destroy();
      }, function(error) {
        console.error(error);
        // Tell the printEngine that rendering this canvas/page has failed.
        // This will make the print proces stop.
        if ('abort' in object)
          obj.abort();
        else
          obj.done();
        self.pdfPage.destroy();
      });
    };
  };

  this.updateStats = function pageViewUpdateStats() {
    if (PDFJS.pdfBug && Stats.enabled) {
      var stats = this.stats;
      Stats.add(this.id, stats);
    }
  };
};

var ThumbnailView = function thumbnailView(container, pdfPage, id) {
  var anchor = document.createElement('a');
  anchor.href = PDFView.getAnchorUrl('#page=' + id);
  anchor.title = mozL10n.get('thumb_page_title', {page: id}, 'Page {{page}}');
  anchor.onclick = function stopNavigation() {
    PDFView.page = id;
    return false;
  };

  var rotation = 0;
  var totalRotation = (rotation + pdfPage.rotate) % 360;
  var viewport = pdfPage.getViewport(1, totalRotation);
  var pageWidth = this.width = viewport.width;
  var pageHeight = this.height = viewport.height;
  var pageRatio = pageWidth / pageHeight;
  this.id = id;

  var canvasWidth = 98;
  var canvasHeight = canvasWidth / this.width * this.height;
  var scaleX = this.scaleX = (canvasWidth / pageWidth);
  var scaleY = this.scaleY = (canvasHeight / pageHeight);

  var div = this.el = document.createElement('div');
  div.id = 'thumbnailContainer' + id;
  div.className = 'thumbnail';

  var ring = document.createElement('div');
  ring.className = 'thumbnailSelectionRing';
  ring.style.width = canvasWidth + 'px';
  ring.style.height = canvasHeight + 'px';

  div.appendChild(ring);
  anchor.appendChild(div);
  container.appendChild(anchor);

  this.hasImage = false;
  this.renderingState = RenderingStates.INITIAL;

  this.updateRotation = function(rot) {

    rotation = rot;
    totalRotation = (rotation + pdfPage.rotate) % 360;
    viewport = pdfPage.getViewport(1, totalRotation);
    pageWidth = this.width = viewport.width;
    pageHeight = this.height = viewport.height;
    pageRatio = pageWidth / pageHeight;

    canvasHeight = canvasWidth / this.width * this.height;
    scaleX = this.scaleX = (canvasWidth / pageWidth);
    scaleY = this.scaleY = (canvasHeight / pageHeight);

    div.removeAttribute('data-loaded');
    ring.textContent = '';
    ring.style.width = canvasWidth + 'px';
    ring.style.height = canvasHeight + 'px';

    this.hasImage = false;
    this.renderingState = RenderingStates.INITIAL;
    this.resume = null;
  }

  function getPageDrawContext() {
    var canvas = document.createElement('canvas');
    canvas.id = 'thumbnail' + id;
    canvas.mozOpaque = true;

    canvas.width = canvasWidth;
    canvas.height = canvasHeight;
    canvas.className = 'thumbnailImage';
    canvas.setAttribute('aria-label', mozL10n.get('thumb_page_canvas',
      {page: id}, 'Thumbnail of Page {{page}}'));

    div.setAttribute('data-loaded', true);

    ring.appendChild(canvas);

    var ctx = canvas.getContext('2d');
    ctx.save();
    ctx.fillStyle = 'rgb(255, 255, 255)';
    ctx.fillRect(0, 0, canvasWidth, canvasHeight);
    ctx.restore();
    return ctx;
  }

  this.drawingRequired = function thumbnailViewDrawingRequired() {
    return !this.hasImage;
  };

  this.draw = function thumbnailViewDraw(callback) {
    if (this.renderingState !== RenderingStates.INITIAL)
      error('Must be in new state before drawing');

    this.renderingState = RenderingStates.RUNNING;
    if (this.hasImage) {
      callback();
      return;
    }

    var self = this;
    var ctx = getPageDrawContext();
    var drawViewport = pdfPage.getViewport(scaleX, totalRotation);
    var renderContext = {
      canvasContext: ctx,
      viewport: drawViewport,
      continueCallback: function(cont) {
        if (PDFView.highestPriorityPage !== 'thumbnail' + self.id) {
          self.renderingState = RenderingStates.PAUSED;
          self.resume = function() {
            self.renderingState = RenderingStates.RUNNING;
            cont();
          };
          return;
        }
        cont();
      }
    };
    pdfPage.render(renderContext).then(
      function pdfPageRenderCallback() {
        self.renderingState = RenderingStates.FINISHED;
        callback();
      },
      function pdfPageRenderError(error) {
        self.renderingState = RenderingStates.FINISHED;
        callback();
      }
    );
    this.hasImage = true;
  };

  this.setImage = function thumbnailViewSetImage(img) {
    if (this.hasImage || !img)
      return;
    this.renderingState = RenderingStates.FINISHED;
    var ctx = getPageDrawContext();
    ctx.drawImage(img, 0, 0, img.width, img.height,
                  0, 0, ctx.canvas.width, ctx.canvas.height);

    this.hasImage = true;
  };
};

var DocumentOutlineView = function documentOutlineView(outline) {
  var outlineView = document.getElementById('outlineView');
  while (outlineView.firstChild)
    outlineView.removeChild(outlineView.firstChild);

  function bindItemLink(domObj, item) {
    domObj.href = PDFView.getDestinationHash(item.dest);
    domObj.onclick = function documentOutlineViewOnclick(e) {
      PDFView.navigateTo(item.dest);
      return false;
    };
  }

  if (!outline) {
    var noOutline = document.createElement('div');
    noOutline.classList.add('noOutline');
    noOutline.textContent = mozL10n.get('no_outline', null,
      'No Outline Available');
    outlineView.appendChild(noOutline);
    return;
  }

  var queue = [{parent: outlineView, items: outline}];
  while (queue.length > 0) {
    var levelData = queue.shift();
    var i, n = levelData.items.length;
    for (i = 0; i < n; i++) {
      var item = levelData.items[i];
      var div = document.createElement('div');
      div.className = 'outlineItem';
      var a = document.createElement('a');
      bindItemLink(a, item);
      a.textContent = item.title;
      div.appendChild(a);

      if (item.items.length > 0) {
        var itemsDiv = document.createElement('div');
        itemsDiv.className = 'outlineItems';
        div.appendChild(itemsDiv);
        queue.push({parent: itemsDiv, items: item.items});
      }

      levelData.parent.appendChild(div);
    }
  }
};

// optimised CSS custom property getter/setter
var CustomStyle = (function CustomStyleClosure() {

  // As noted on: http://www.zachstronaut.com/posts/2009/02/17/
  //              animate-css-transforms-firefox-webkit.html
  // in some versions of IE9 it is critical that ms appear in this list
  // before Moz
  var prefixes = ['ms', 'Moz', 'Webkit', 'O'];
  var _cache = { };

  function CustomStyle() {
  }

  CustomStyle.getProp = function get(propName, element) {
    // check cache only when no element is given
    if (arguments.length == 1 && typeof _cache[propName] == 'string') {
      return _cache[propName];
    }

    element = element || document.documentElement;
    var style = element.style, prefixed, uPropName;

    // test standard property first
    if (typeof style[propName] == 'string') {
      return (_cache[propName] = propName);
    }

    // capitalize
    uPropName = propName.charAt(0).toUpperCase() + propName.slice(1);

    // test vendor specific properties
    for (var i = 0, l = prefixes.length; i < l; i++) {
      prefixed = prefixes[i] + uPropName;
      if (typeof style[prefixed] == 'string') {
        return (_cache[propName] = prefixed);
      }
    }

    //if all fails then set to undefined
    return (_cache[propName] = 'undefined');
  };

  CustomStyle.setProp = function set(propName, element, str) {
    var prop = this.getProp(propName);
    if (prop != 'undefined')
      element.style[prop] = str;
  };

  return CustomStyle;
})();

var TextLayerBuilder = function textLayerBuilder(textLayerDiv) {
  var textLayerFrag = document.createDocumentFragment();
  this.textLayerDiv = textLayerDiv;
  this.layoutDone = false;
  this.divContentDone = false;

  this.beginLayout = function textLayerBuilderBeginLayout() {
    this.textDivs = [];
    this.textLayerQueue = [];
  };

  this.endLayout = function textLayerBuilderEndLayout() {
    this.layoutDone = true;
    this.insertDivContent();
  },

  this.renderLayer = function textLayerBuilderRenderLayer() {
    var self = this;
    var textDivs = this.textDivs;
    var textLayerDiv = this.textLayerDiv;
    var canvas = document.createElement('canvas');
    var ctx = canvas.getContext('2d');

    // No point in rendering so many divs as it'd make the browser unusable
    // even after the divs are rendered
    if (textDivs.length > 100000)
      return;

    while (textDivs.length > 0) {
      var textDiv = textDivs.shift();
      textLayerFrag.appendChild(textDiv);

      ctx.font = textDiv.style.fontSize + ' ' + textDiv.style.fontFamily;
      var width = ctx.measureText(textDiv.textContent).width;

      if (width > 0) {
        var textScale = textDiv.dataset.canvasWidth / width;

        CustomStyle.setProp('transform' , textDiv,
          'scale(' + textScale + ', 1)');
        CustomStyle.setProp('transformOrigin' , textDiv, '0% 0%');
      }
    }

    textLayerDiv.appendChild(textLayerFrag);
  };

  this.setupRenderLayoutTimer = function textLayerSetupRenderLayoutTimer() {
    // Schedule renderLayout() if user has been scrolling, otherwise
    // run it right away
    var kRenderDelay = 200; // in ms
    var self = this;
    if (Date.now() - PDFView.lastScroll > kRenderDelay) {
      // Render right away
      this.renderLayer();
    } else {
      // Schedule
      if (this.renderTimer)
        clearTimeout(this.renderTimer);
      this.renderTimer = setTimeout(function() {
        self.setupRenderLayoutTimer();
      }, kRenderDelay);
    }
  };

  this.appendText = function textLayerBuilderAppendText(fontName, fontSize,
                                                        geom) {
    var textDiv = document.createElement('div');

    // vScale and hScale already contain the scaling to pixel units
    var fontHeight = fontSize * geom.vScale;
    textDiv.dataset.canvasWidth = geom.canvasWidth * geom.hScale;
    textDiv.dataset.fontName = fontName;

    textDiv.style.fontSize = fontHeight + 'px';
    textDiv.style.fontFamily = fontName;
    textDiv.style.left = geom.x + 'px';
    textDiv.style.top = (geom.y - fontHeight) + 'px';

    // The content of the div is set in the `setTextContent` function.

    this.textDivs.push(textDiv);
  };

  this.insertDivContent = function textLayerUpdateTextContent() {
    // Only set the content of the divs once layout has finished, the content
    // for the divs is available and content is not yet set on the divs.
    if (!this.layoutDone || this.divContentDone || !this.textContent)
      return;

    this.divContentDone = true;

    var textDivs = this.textDivs;
    var bidiTexts = this.textContent.bidiTexts;

    for (var i = 0; i < bidiTexts.length; i++) {
      var bidiText = bidiTexts[i];
      var textDiv = textDivs[i];

      textDiv.textContent = bidiText.str;
      textDiv.dir = bidiText.ltr ? 'ltr' : 'rtl';
    }

    this.setupRenderLayoutTimer();
  };

  this.setTextContent = function textLayerBuilderSetTextContent(textContent) {
    this.textContent = textContent;
    this.insertDivContent();
  };
};

function updateViewarea() {

  if (!PDFView.initialized)
    return;
  var visible = PDFView.getVisiblePages();
  var visiblePages = visible.views;

  PDFView.renderHighestPriority();

  var currentId = PDFView.page;
  var firstPage = visible.first;

  for (var i = 0, ii = visiblePages.length, stillFullyVisible = false;
       i < ii; ++i) {
    var page = visiblePages[i];

    if (page.percent < 100)
      break;

    if (page.id === PDFView.page) {
      stillFullyVisible = true;
      break;
    }
  }

  if (!stillFullyVisible) {
    currentId = visiblePages[0].id;
  }

  if (!PDFView.isFullscreen) {
    updateViewarea.inProgress = true; // used in "set page"
    PDFView.page = currentId;
    updateViewarea.inProgress = false;
  }

  var currentScale = PDFView.currentScale;
  var currentScaleValue = PDFView.currentScaleValue;
  var normalizedScaleValue = currentScaleValue == currentScale ?
    currentScale * 100 : currentScaleValue;

  var pageNumber = firstPage.id;
  var pdfOpenParams = '#page=' + pageNumber;
  pdfOpenParams += '&zoom=' + normalizedScaleValue;
  var currentPage = PDFView.pages[pageNumber - 1];
  var topLeft = currentPage.getPagePoint(PDFView.container.scrollLeft,
    (PDFView.container.scrollTop - firstPage.y));
  pdfOpenParams += ',' + Math.round(topLeft[0]) + ',' + Math.round(topLeft[1]);

  var store = PDFView.store;
  store.initializedPromise.then(function() {
    store.set('exists', true);
    store.set('page', pageNumber);
    store.set('zoom', normalizedScaleValue);
    store.set('scrollLeft', Math.round(topLeft[0]));
    store.set('scrollTop', Math.round(topLeft[1]));
  });
  var href = PDFView.getAnchorUrl(pdfOpenParams);
  document.getElementById('viewBookmark').href = href;
}

window.addEventListener('resize', function webViewerResize(evt) {
  if (PDFView.initialized &&
      (document.getElementById('pageWidthOption').selected ||
      document.getElementById('pageFitOption').selected ||
      document.getElementById('pageAutoOption').selected))
      PDFView.parseScale(document.getElementById('scaleSelect').value);
  updateViewarea();
});

window.addEventListener('hashchange', function webViewerHashchange(evt) {
  PDFView.setHash(document.location.hash.substring(1));
});

window.addEventListener('change', function webViewerChange(evt) {
  var files = evt.target.files;
  if (!files || files.length == 0)
    return;

  // Read the local file into a Uint8Array.
  var fileReader = new FileReader();
  fileReader.onload = function webViewerChangeFileReaderOnload(evt) {
    var buffer = evt.target.result;
    var uint8Array = new Uint8Array(buffer);
    PDFView.open(uint8Array, 0);
  };

  var file = files[0];
  fileReader.readAsArrayBuffer(file);
  PDFView.setTitleUsingUrl(file.name);

  // URL does not reflect proper document location - hiding some icons.
  document.getElementById('viewBookmark').setAttribute('hidden', 'true');
  document.getElementById('download').setAttribute('hidden', 'true');
}, true);

function selectScaleOption(value) {
  var options = document.getElementById('scaleSelect').options;
  var predefinedValueFound = false;
  for (var i = 0; i < options.length; i++) {
    var option = options[i];
    if (option.value != value) {
      option.selected = false;
      continue;
    }
    option.selected = true;
    predefinedValueFound = true;
  }
  return predefinedValueFound;
}

window.addEventListener('localized', function localized(evt) {
  document.getElementsByTagName('html')[0].dir = mozL10n.language.direction;
}, true);

window.addEventListener('scalechange', function scalechange(evt) {
  var customScaleOption = document.getElementById('customScaleOption');
  customScaleOption.selected = false;

  if (!evt.resetAutoSettings &&
       (document.getElementById('pageWidthOption').selected ||
        document.getElementById('pageFitOption').selected ||
        document.getElementById('pageAutoOption').selected)) {
      updateViewarea();
      return;
  }

  var predefinedValueFound = selectScaleOption('' + evt.scale);
  if (!predefinedValueFound) {
    customScaleOption.textContent = Math.round(evt.scale * 10000) / 100 + '%';
    customScaleOption.selected = true;
  }

  updateViewarea();
}, true);

window.addEventListener('pagechange', function pagechange(evt) {
  var page = evt.pageNumber;
  if (document.getElementById('pageNumber').value != page) {
    document.getElementById('pageNumber').value = page;
    var selected = document.querySelector('.thumbnail.selected');
    if (selected)
      selected.classList.remove('selected');
    var thumbnail = document.getElementById('thumbnailContainer' + page);
    thumbnail.classList.add('selected');
    var visibleThumbs = PDFView.getVisibleThumbs();
    var numVisibleThumbs = visibleThumbs.views.length;
    // If the thumbnail isn't currently visible scroll it into view.
    if (numVisibleThumbs > 0) {
      var first = visibleThumbs.first.id;
      // Account for only one thumbnail being visible.
      var last = numVisibleThumbs > 1 ?
                  visibleThumbs.last.id : first;
      if (page <= first || page >= last)
        scrollIntoView(thumbnail);
    }

  }
  document.getElementById('previous').disabled = (page <= 1);
  document.getElementById('next').disabled = (page >= PDFView.pages.length);
}, true);

// Firefox specific event, so that we can prevent browser from zooming
window.addEventListener('DOMMouseScroll', function(evt) {
  if (evt.ctrlKey) {
    evt.preventDefault();

    var ticks = evt.detail;
    var direction = (ticks > 0) ? 'zoomOut' : 'zoomIn';
    for (var i = 0, length = Math.abs(ticks); i < length; i++)
      PDFView[direction]();
  }
}, false);

window.addEventListener('keydown', function keydown(evt) {
  var handled = false;
  var cmd = (evt.ctrlKey ? 1 : 0) |
            (evt.altKey ? 2 : 0) |
            (evt.shiftKey ? 4 : 0) |
            (evt.metaKey ? 8 : 0);

  // First, handle the key bindings that are independent whether an input
  // control is selected or not.
  if (cmd == 1 || cmd == 8) { // either CTRL or META key.
    switch (evt.keyCode) {
      case 61: // FF/Mac '='
      case 107: // FF '+' and '='
      case 187: // Chrome '+'
        PDFView.zoomIn();
        handled = true;
        break;
      case 173: // FF/Mac '-'
      case 109: // FF '-'
      case 189: // Chrome '-'
        PDFView.zoomOut();
        handled = true;
        break;
      case 48: // '0'
        PDFView.parseScale(kDefaultScale, true);
        handled = true;
        break;
    }
  }

  if (handled) {
    evt.preventDefault();
    return;
  }

  // Some shortcuts should not get handled if a control/input element
  // is selected.
  var curElement = document.activeElement;
  if (curElement && (curElement.tagName == 'INPUT' ||
                     curElement.tagName == 'SELECT')) {
    return;
  }
  var controlsElement = document.getElementById('toolbar');
  while (curElement) {
    if (curElement === controlsElement && !PDFView.isFullscreen)
      return; // ignoring if the 'toolbar' element is focused
    curElement = curElement.parentNode;
  }

  if (cmd == 0) { // no control key pressed at all.
    switch (evt.keyCode) {
      case 37: // left arrow
      case 75: // 'k'
      case 80: // 'p'
        PDFView.page--;
        handled = true;
        break;
      case 39: // right arrow
      case 74: // 'j'
      case 78: // 'n'
        PDFView.page++;
        handled = true;
        break;

      case 32: // spacebar
        if (PDFView.isFullscreen) {
          PDFView.page++;
          handled = true;
        }
        break;

      case 82: // 'r'
        PDFView.rotatePages(90);
        break;
    }
  }

  if (cmd == 4) { // shift-key
    switch (evt.keyCode) {
      case 82: // 'r'
        PDFView.rotatePages(-90);
        break;
    }
  }

  if (handled) {
    evt.preventDefault();
  }
});

window.addEventListener('beforeprint', function beforePrint(evt) {
  PDFView.beforePrint();
});

window.addEventListener('afterprint', function afterPrint(evt) {
  PDFView.afterPrint();
});

(function fullscreenClosure() {
  function fullscreenChange(e) {
    var isFullscreen = document.fullscreenElement || document.mozFullScreen ||
        document.webkitIsFullScreen;

    if (!isFullscreen) {
      PDFView.exitFullscreen();
    }
  }

  window.addEventListener('fullscreenchange', fullscreenChange, false);
  window.addEventListener('mozfullscreenchange', fullscreenChange, false);
  window.addEventListener('webkitfullscreenchange', fullscreenChange, false);
})();


var loadPdfJsView = function(params) {
  PDFView.initialize();

  var file = params.file;

  if (!window.File || !window.FileReader || !window.FileList || !window.Blob) {
    document.getElementById('openFile').setAttribute('hidden', 'true');
  } else {
    document.getElementById('fileInput').value = null;
  }

  // Special debugging flags in the hash section of the URL.
  var hash = document.location.hash.substring(1);
  var hashParams = PDFView.parseQueryString(hash);

  if ('disableWorker' in hashParams)
    PDFJS.disableWorker = (hashParams['disableWorker'] === 'true');

  var locale = navigator.language;
  if ('locale' in hashParams)
    locale = hashParams['locale'];
  mozL10n.language.code = locale;

  if ('textLayer' in hashParams) {
    switch (hashParams['textLayer']) {
      case 'off':
        PDFJS.disableTextLayer = true;
        break;
      case 'visible':
      case 'shadow':
      case 'hover':
        var viewer = document.getElementById('viewer');
        viewer.classList.add('textLayer-' + hashParams['textLayer']);
        break;
    }
  }

  if ('pdfBug' in hashParams) {
    PDFJS.pdfBug = true;
    var pdfBug = hashParams['pdfBug'];
    var enabled = pdfBug.split(',');
    PDFBug.enable(enabled);
    PDFBug.init();
  }


  if (!PDFView.supportsPrinting) {
    document.getElementById('print').classList.add('hidden');
  }

  if (!PDFView.supportsFullscreen) {
    document.getElementById('fullscreen').classList.add('hidden');
  }

  // Listen for warnings to trigger the fallback UI.  Errors should be caught
  // and call PDFView.error() so we don't need to listen for those.
  PDFJS.LogManager.addLogger({
    warn: function() {
      PDFView.fallback();
    }
  });

  var mainContainer = document.getElementById('mainContainer');
  var outerContainer = document.getElementById('outerContainer');
  mainContainer.addEventListener('transitionend', function(e) {
    if (e.target == mainContainer) {
      var event = document.createEvent('UIEvents');
      event.initUIEvent('resize', false, false, window, 0);
      window.dispatchEvent(event);
      outerContainer.classList.remove('sidebarMoving');
    }
  }, true);

  document.getElementById('sidebarToggle').addEventListener('click',
    function() {
      this.classList.toggle('toggled');
      outerContainer.classList.add('sidebarMoving');
      outerContainer.classList.toggle('sidebarOpen');
      PDFView.sidebarOpen = outerContainer.classList.contains('sidebarOpen');
      PDFView.renderHighestPriority();
    });

  document.getElementById('viewThumbnail').addEventListener('click',
    function() {
      PDFView.switchSidebarView('thumbs');
    });

  document.getElementById('viewOutline').addEventListener('click',
    function() {
      PDFView.switchSidebarView('outline');
    });

  document.getElementById('viewSearch').addEventListener('click',
    function() {
      PDFView.switchSidebarView('search');
    });

  document.getElementById('searchButton').addEventListener('click',
    function() {
      PDFView.search();
    });

  document.getElementById('previous').addEventListener('click',
    function() {
      PDFView.page--;
    });

  document.getElementById('next').addEventListener('click',
    function() {
      PDFView.page++;
    });

  document.querySelector('.zoomIn').addEventListener('click',
    function() {
      PDFView.zoomIn();
    });

  document.querySelector('.zoomOut').addEventListener('click',
    function() {
      PDFView.zoomOut();
    });

  document.getElementById('fullscreen').addEventListener('click',
    function() {
      PDFView.fullscreen();
    });

  document.getElementById('openFile').addEventListener('click',
    function() {
      document.getElementById('fileInput').click();
    });

  document.getElementById('print').addEventListener('click',
    function() {
      window.print();
    });

  document.getElementById('download').addEventListener('click',
    function() {
      PDFView.download();
    });

  document.getElementById('searchTermsInput').addEventListener('keydown',
    function(event) {
      if (event.keyCode == 13) {
        PDFView.search();
      }
    });

  document.getElementById('pageNumber').addEventListener('change',
    function() {
      PDFView.page = this.value;
    });

  document.getElementById('scaleSelect').addEventListener('change',
    function() {
      PDFView.parseScale(this.value);
    });

  document.getElementById('page_rotate_ccw').addEventListener('click',
      function() {
        PDFView.rotatePages(-90);
      });

  document.getElementById('page_rotate_cw').addEventListener('click',
      function() {
        PDFView.rotatePages(90);
      });

  PDFView.open(file, 0);
}
