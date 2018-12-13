function showFrame(anchor) {
    var tbid = anchor.getAttribute('tbid');
    var expanded = anchor.expanded;
    if (expanded) {
        MochiKit.DOM.hideElement(anchor.expandedElement);
        anchor.expanded = false;
        _swapImage(anchor);
        return false;
    }
    anchor.expanded = true;
    if (anchor.expandedElement) {
        MochiKit.DOM.showElement(anchor.expandedElement);
        _swapImage(anchor);
        $('debug_input_'+tbid).focus();
        return false;
    }
    var url = debug_base
        + '/show_frame?tbid=' + tbid
        + '&debugcount=' + debug_count;
    var d = MochiKit.Async.doSimpleXMLHttpRequest(url);
    d.addCallbacks(function (data) {
        var el = MochiKit.DOM.DIV({});
        anchor.parentNode.insertBefore(el, anchor.nextSibling);
        el.innerHTML = data.responseText;
        anchor.expandedElement = el;
        _swapImage(anchor);
        $('debug_input_'+tbid).focus();
    }, function (error) {
        showError(error.req.responseText);
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

function submitInput(button, tbid) {
    var input = $(button.getAttribute('input-from'));
    var output = $(button.getAttribute('output-to'));
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
        input: input.value
    };
    MochiKit.DOM.showElement(output);
    var d = MochiKit.Async.doSimpleXMLHttpRequest(url, vars);
    d.addCallbacks(function (data) {
        var result = data.responseText;
        output.innerHTML += result;
        input.value = '';
        input.focus();
    }, function (error) {
        showError(error.req.responseText);
    });
    return false;
}

function showError(msg) {
    var el = $('error-container');
    if (el.innerHTML) {
        el.innerHTML += '<hr noshade>\n' + msg;
    } else {
        el.innerHTML = msg;
    }
    MochiKit.DOM.showElement('error-area');
}

function clearError() {
    var el = $('error-container');
    el.innerHTML = '';
    MochiKit.DOM.hideElement('error-area');
}

function expandInput(button) {
    var input = button.form.elements.input;
    stdops = {
        name: 'input',
        style: 'width: 100%',
        autocomplete: 'off'
    };
    if (input.tagName == 'INPUT') {
        var newEl = MochiKit.DOM.TEXTAREA(stdops);
        var text = 'Contract';
    } else {
        stdops['type'] = 'text';
        stdops['onkeypress'] = 'upArrow(this)';
        var newEl = MochiKit.DOM.INPUT(stdops);
        var text = 'Expand';
    }
    newEl.value = input.value;
    newEl.id = input.id;
    MochiKit.DOM.swapDOM(input, newEl);
    newEl.focus();
    button.value = text;
    return false;
}

function upArrow(input, event) {
    if (window.event) {
        event = window.event;
    }
    if (event.keyCode != 38 && event.keyCode != 40) {
        // not an up- or down-arrow
        return true;
    }
    var dir = event.keyCode == 38 ? 1 : -1;
    var history = input.form.history;
    if (! history) {
        history = input.form.history = [];
    }
    var pos = input.historyPosition || 0;
    if (! pos && dir == -1) {
        return true;
    }
    if (! pos && input.value) {
        history.push(input.value);
        pos = 1;
    }
    pos += dir;
    if (history.length-pos < 0) {
        pos = 1;
    }
    if (history.length-pos > history.length-1) {
        input.value = '';
        return true;
    }
    input.historyPosition = pos;
    var line = history[history.length-pos];
    input.value = line;
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
    MochiKit.DOM.showElement(span);
    MochiKit.DOM.hideElement(anchor);
    return false;
}
