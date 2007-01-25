/* event handling and input greying code
 *+from http://www.scottandrew.com/weblog/articles/cbs-events
 *+and http://www.pledgebank.com/pb.js                       
 */
function addEvent(obj, evType, fn) {
  if (obj.addEventListener){
    obj.addEventListener(evType, fn, true);
    return true;
  } else if (obj.attachEvent){
    var r = obj.attachEvent('on'+evType, fn);
    return r;
  } else {
    /* alert('Handler not attached'); /* for dev only! */
    return false;
  }
}

function fadein(elem) {
  id = elem.id;
  for (var ii = 0; ii < greyed.length; ii++) {
    if (greyed[ii][0] == id && greyed[ii][1] == elem.value) {
      Element.removeClassName(elem, 'greyed');
      Element.addClassName(elem, 'darkened');
      elem.value = '';
    }
  }
}

function fadeout(elem) {
  id = elem.id;
  for (var ii = 0; ii < greyed.length; ii++) {
    if (greyed[ii][0] == id && elem.value == '') {
      Element.removeClassName(elem, 'darkened');
      Element.addClassName(elem, 'greyed');
      elem.value = greyed[ii][1];
    }
  }
}

function greyOutInputs() {
  if (!document) return;
  
  if (document.getElementById) {
    for (var ii = 0; ii < greyed.length; ii++) {
      elem = document.getElementById(greyed[ii][0])
      if (elem && elem.value == '') elem.value = greyed[ii][1];
      if (elem && elem.value == greyed[ii][1]) Element.addClassName(elem, 'greyed');
    }
  }

}

/* rounded corner generation */
function rounded(selector, size) {
  var ii;
  var v = document.getElementsBySelector(selector);
  for(ii = 0; ii < v.length; ii++) {
    addTop(v[ii],size);
    addBottom(v[ii],size);
  }
}

function addTop(el, size){
  var i;
  var d = document.createElement('span');
  var cn = 'r';
  var lim = 4;
  if(size && size == 'small') { cn = 'rs'; lim = 2 }
  d.className = 'rtop';
  for(i = 1; i <= lim; i++) {
    var x = document.createElement('span');
    x.className = cn + i;
    d.appendChild(x);
  }
  el.insertBefore(d, el.firstChild);
}

function addBottom(el, size) {
  var i;
  var d = document.createElement('span');
  var cn = 'r';
  var lim = 4;
  if(size && size == 'small') { cn = 'rs'; lim = 2 }
  d.className = 'rbottom';
  for(i = lim; i > 0; i--) {
    var x = document.createElement('span');
    x.className = cn + i;
    d.appendChild(x);
  }
  el.appendChild(d, el.firstChild);
}

function doCorners() {
  var b = navigator.userAgent.toLowerCase();
  
  if(!document.getElementById || !document.createElement) {
    return(false);
  } else if ( b.indexOf('msie 5') > 0 && b.indexOf('opera') == -1 ) {
    return(false);
  } else {
    var elements = [];
    rounded('.box');
  }
}

// Window onload rounded corners event.
addEvent(window, 'load', doCorners);

function checkInputLength(length_elem, replace_elem, length) {
  var count = document.createTextNode(length_elem.value.length);
  replace_elem.replaceChild(count, replace_elem.firstChild);

  if(length_elem.value.length > length) {
    Element.addClassName(replace_elem, 'error-text');
  } else {
    Element.removeClassName(replace_elem, 'error-text');
  }
}

var rules = {
  'input' : function(element) {
    element.onfocus = function() {
      //alert('gained focus');
      fadein(this);
    };
    element.onblur = function() {
      //alert('lost focus');
      fadeout(this);
    };
  },
  '#id_description' : function(element) {
    element.onkeyup = function() {
      checkInputLength(this, document.getElementById('desc_charcount'), 255);
    };
    element.onkeydown = function() {      
      checkInputLength(this, document.getElementById('desc_charcount'), 255);
    };
  }
};
Behaviour.register(rules);

var greyed = [
  ['loginform-username', '<username>'],
  ['loginform-password', 'password'],
  ['project-search-terms', 'Search terms...'],
  ['user-search-terms', 'Search terms...']
];
addEvent(window, 'load', greyOutInputs);

function checkDescriptionLength() {
  if(document.getElementById('id_description') != null)
    checkInputLength(document.getElementById('id_description'), document.getElementById('desc_charcount'), 255);
}
addEvent(window, 'load', checkDescriptionLength);