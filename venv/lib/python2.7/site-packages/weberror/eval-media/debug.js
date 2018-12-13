function showFrame(anchor) {
    var tbid = anchor.getAttribute('tbid');
    var expanded = anchor.expanded;
    if (expanded) {
        hideElement(anchor.expandedElement);
        anchor.expanded = false;
        _swapImage(anchor);
        return false;
    }
    anchor.expanded = true;
    if (anchor.expandedElement) {
        showElement(anchor.expandedElement);
        _swapImage(anchor);
        $('#debug_input_'+tbid).get(0).focus();
        return false;
    }
    var url = debug_base
        + '/show_frame?tbid=' + tbid
        + '&debugcount=' + debug_count;
    callbackXHR(url, null, function (data) {
                    var el = createElement('div');
                    anchor.parentNode.insertBefore(el, anchor.nextSibling);
                    el.innerHTML = data.responseText;
                    anchor.expandedElement = el;
                    _swapImage(anchor);
                    $('#debug_input_'+tbid).focus().keydown(upArrow);
                });
    return false;
}

function _swapImage(anchor) {
    var el = anchor.getElementsByTagName('IMG')[0];
    if (anchor.expanded) {
        var img = 'minus.jpg';
    } else {
        var img = 'plus.jpg';
    }
    el.src = debug_base + '/media/' + img;
}

function showSource(anchor) {
    var location = anchor.getAttribute('location');
    showSourceCode(location);
    return false;
}

function showSourceCode(location) {
    var url = debug_base + '/source_code?location=' + encodeURIComponent(location);
    var source = document.getElementById('source_data');
    source.innerHTML = 'Loading...';
    switch_display('source_data');
    callbackXHR(url, null, function (req) {
                    source.innerHTML = req.responseText;
                    if (location.indexOf(':') > 0) {
                        var lineno = location.substring(location.indexOf(':')+1);
                        lineno = parseInt(lineno) - 10;
                        if (lineno > 1) {
                            document.location.hash = '#code-'+(lineno-10);
                        }
                    }
                });
}

function submitInput(button, tbid) {
    var input = $('#' + button.getAttribute('input-from')).get(0);
    var output = $('#' + button.getAttribute('output-to')).get(0);
    var url = debug_base
        + '/exec_input';
    var history = input.form.history;
    input.historyPosition = 0;
    if (! history) {
        history = input.form.history = [];
    }
    history.push(input.value);
    var vars = {
        tbid: tbid,
        debugcount: debug_count,
        input: input.value,
        csrf_token: csrf_token
    };
    showElement(output);
    callbackXHR(url, vars, function (data) {
        var result = data.responseText;
        output.innerHTML += result;
        input.value = '';
        input.focus();
    });
    return false;
}

function showError(msg) {
    var el = $('#error-container').get(0);
    if (el.innerHTML) {
        el.innerHTML += '<hr noshade>\n' + msg;
    } else {
        el.innerHTML = msg;
    }
    showElement($('#error-area').get(0));
}

function clearError() {
    var el = $('#error-container').get(0);
    el.innerHTML = '';
    $('#error-area').hide();
}

function upArrow(event) {
    var key = event.charCode ? event.charCode : event.keyCode;
    if (key != 38 && key != 40 && key != 63232
        && key != 63233) {
        // not an up- or down-arrow
        return true;
    }
    var dir = ((key == 38) || (key == 63232)) ? 1 : -1;
    var history = this.form.history;
    if (! history) {
        history = this.form.history = [];
    }
    var pos = this.historyPosition || 0;
    if (! pos && dir == -1) {
        return true;
    }
    if (! pos && this.value) {
        history.push(this.value);
        pos = 1;
    }
    pos += dir;
    if (history.length-pos < 0) {
        pos = 1;
    }
    if (history.length-pos > history.length-1) {
        this.value = '';
        return true;
    }
    this.historyPosition = pos;
    var line = history[history.length-pos];
    if (! line) {
        return true;
    }
    this.value = line;
}

function expandInput(button) {
    var input = button.form.elements.input;
    stdops = {
        name: 'input',
        style: 'width: 100%',
        autocomplete: 'off'
    };
    if (input.tagName == 'INPUT') {
        var newEl = createElement('textarea', stdops);
        var text = 'Contract';
    } else {
        stdops['type'] = 'text';
        var newEl = createElement('input', stdops);
        $(newEl).keydown(upArrow);
        var text = 'Expand';
    }
    newEl.value = input.value;
    newEl.id = input.id;
    swapDOM(input, newEl);
    newEl.focus();
    button.value = text;
    return false;
}

function expandLong(anchor) {
    var span = anchor;
    while (span) {
        if (span.style && span.style.display == 'none') {
            break;
        }
        span = span.nextSibling;
    }
    if (! span) {
        return false;
    }
    showElement(span);
    hideElement(anchor);
    return false;
}

function showElement(el) {
    el.style.display = '';
}

function hideElement(el) {
    el.style.display = 'none';
}

function createElement(tag, attrs /*, sub-elements...*/) {
    var el = document.createElement(tag);
    if (attrs) {
        for (var i in attrs) {
            el.setAttribute(i, attrs[i]);
        }
    }
    for (var i=2; i<arguments.length; i++) {
        var item = arguments[i];
        if (typeof item == 'string') {
            item = document.createTextNode(item);
        }
        el.appendChild(item);
    }
    return el;
}

function swapDOM(dest, src) {
    var parent = dest.parentNode;
    parent.replaceChild(src, dest);
    return src;
}


function getXMLHttpRequest() {
    /* Taken from MochiKit */
    var tryThese = [
        function () { return new XMLHttpRequest(); },
        function () { return new ActiveXObject('Msxml2.XMLHTTP'); },
        function () { return new ActiveXObject('Microsoft.XMLHTTP'); },
        function () { return new ActiveXObject('Msxml2.XMLHTTP.4.0'); }
        ];
    for (var i = 0; i < tryThese.length; i++) {
        var func = tryThese[i];
        try {
            return func();
        } catch (e) {
            // pass
        }
    }
}

function callbackXHR(url, data, callback) {
    var xhr = getXMLHttpRequest();
    xhr.onreadystatechange = function () {
        if (xhr.readyState == 4) {
            if (xhr.status == 200) {
                callback(xhr);
            } else {
                showError(xhr.responseText);
            }
        }
    };
    var method = data ? "POST" : "GET";
    xhr.open(method, url);
    if (data) {
        if (! (typeof data == 'string')) {
            var newData = '';
            for (var i in data) {
                if (newData) {
                    newData += '&';
                }
                newData += i + '=' + encodeURIComponent(data[i]);
            }
            data = newData;
        }
        xhr.setRequestHeader('content-type', 'application/x-www-form-urlencoded');
        xhr.send(data);
    } else {
        xhr.send(null);
    }
}

function switch_display(id) {
    ids = ['extra_data', 'template_data', 'traceback_data', 'source_data'];
    for (i in ids){
        part = ids[i];
        var el = document.getElementById(part);
        el.className = "hidden-data";
        var el = document.getElementById(part+'_tab');
        el.className = "not-active";
        var el = document.getElementById(part+'_link');
        el.className = "not-active";
    }
    var el = document.getElementById(id);
    el.className = "active";
    var el = document.getElementById(id+'_link');
    el.className = "active";
    var el = document.getElementById(id+'_tab');
    el.className = "active";

    return false;
}

function hide_display(id) {
    var el = document.getElementById(id);
    if (el.className == "hidden-data") {
        el.className = "";
        return true;
    } else {
        el.className = "hidden-data";
        return false;
    }
}

function show_button(toggle_id, name) {
    document.write('<a href="#' + toggle_id
        + '" onclick="javascript:hide_display(\'' + toggle_id
        + '\')" class="button">' + name + '</a><br>');
}

function switch_source(el, hide_type) {
    while (el) {
        if (el.getAttribute &&
            el.getAttribute('source-type') == hide_type) {
            break;
        }
        el = el.parentNode;
    }
    if (! el) {
        return false;
    }
    el.style.display = 'none';
    console.log('found current el', el);
    if (hide_type == 'long') {
        while (el) {
            if (el.getAttribute &&
                el.getAttribute('source-type') == 'short') {
                break;
            }
            el = el.nextSibling;
        }
        console.log('found short el', el);
    } else {
        while (el) {
            if (el.getAttribute &&
                el.getAttribute('source-type') == 'long') {
                break;
            }
            el = el.previousSibling;
        }
        console.log('found long el', el);
    }
    if (el) {
        el.style.display = '';
    }
    return false;
}

$(document).ready(function() {
    var hide_all = function() {
        $('#short_text_version, #long_text_version, #short_traceback, #full_traceback, #short_xml_version, #long_xml_version, div.feature-highlight').hide();
        $('#view_long_text, #view_short_text, #view_long_html, #view_short_html, #view_short_xml, #view_long_xml').removeClass('active');
    };
    
    if ($('#long_text_version').length == 0) {
        $('#view_long_text').hide();
    }
    if ($('#full_traceback').length == 0) {
        $('#view_long_html').hide();
    }
    
    
    $('#view_short_text').click(function() {
        hide_all();
        $('#short_text_version').show();
        $(this).addClass('active');
        return false;
    });
    $('#view_long_text').click(function() {
        hide_all();
        $('#long_text_version').show();
        $(this).addClass('active');
        return false;
    });
    $('#view_short_html').click(function() {
        hide_all();
        $('#short_traceback, div.feature-highlight').show();
        $(this).addClass('active');
        return false;
    });
    $('#view_long_html').click(function () {
        hide_all();
        $('#full_traceback, div.feature-highlight').show();
        $(this).addClass('active');
        return false;
    });
    $('#view_short_xml').click(function () {
        hide_all();
        $('#short_xml_version').show();
        $(this).addClass('active');
        return false;
    });
    $('#view_long_xml').click(function () {
        hide_all();
        $('#long_xml_version').show();
        $(this).addClass('active');
        return false;
    });
});

/* Fix case when Firebug isn't present: */
if (typeof console == 'undefined') {
    var console = {log: function (msg) {}};
}
