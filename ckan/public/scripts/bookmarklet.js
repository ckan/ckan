function add_to_ckan() {
    f='http://ckan.net/package/new?url='+encodeURIComponent(window.location.href)+'&title='+encodeURIComponent(document.title);
    // TODO: ? name=window.location.hostname
    // insert a description if it exists
    if((n = document.getElementsByName('description')[0]) && (d = n.content)) {
        f += '&notes=' + encodeURIComponent(d);
    }
    a = function() {
        if(!window.open(f)) {
            // e.g. popups are blocked.
            location.href=f;
        }
    };
    if(/Firefox/.test(navigator.userAgent)) {
        setTimeout(a,0)
    }
    else {
        a()
    }
}
// add_to_ckan();
