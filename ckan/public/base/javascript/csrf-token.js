(function (ckan) {
  /* This script collects csrf token for xhr requests, also set meta tags if not found
   */

  let csrfPromise = null;

  function getCsrfMetaToken() {
    let csrfFieldMeta = document.querySelector('meta[name="csrf_field_name"]');
    let csrfHeaderMeta = document.querySelector('meta[name="csrf_header_name"]');
    if (!csrfFieldMeta || !csrfHeaderMeta) return null;

    let csrfField = csrfFieldMeta.getAttribute('content');
    let csrfHeader = csrfHeaderMeta.getAttribute('content');

    let csrfTokenMeta = document.querySelector('meta[name="' + csrfField + '"]');
    if (!csrfTokenMeta) {
      return null;
    }
    let token = csrfTokenMeta.getAttribute('content');
    return {name: csrfField, header: csrfHeader, token: token};
  }

  function fetchAndSetCsrfMetaTag() {
    if (csrfPromise) return csrfPromise;

    csrfPromise = new Promise(function (resolve, reject) {
      var existing = getCsrfMetaToken();
      if (existing)  {
        return resolve(existing);
      }

      // If the meta tag is not found, we need to fetch it from the server
      var xhr = new XMLHttpRequest();
      xhr.open('GET', '/csrf-input');
      xhr.setRequestHeader('Accept', 'application/json');
      xhr.onreadystatechange = function () {
        if (xhr.readyState === 4) {
          if (xhr.status === 200) {
            let data = JSON.parse(xhr.responseText);
            let head = document.head;

            let metaToken = document.createElement('meta');
            metaToken.name = data.name;
            metaToken.content = data.token;
            head.appendChild(metaToken);

            resolve({name: data.name,  header: data.header, token: data.token});
          } else {
            reject(new Error('Failed to fetch CSRF data: ' + xhr.status));
          }
        }
      };
      xhr.send();
    });

    return csrfPromise;
  }

  function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS)$/.test(method));
  }

  ckan.fetchCsrfToken = fetchAndSetCsrfMetaTag;
  ckan.csrfSafeMethod = csrfSafeMethod;

})(this.ckan);
