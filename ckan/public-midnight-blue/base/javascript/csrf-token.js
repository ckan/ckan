(function (ckan) {
  /* This script collects csrf token for xhr requests, also set meta tags if not found */
  function getCsrfMetaToken() {
    var csrfFieldMeta = document.querySelector('meta[name="csrf_field_name"]');
    if (!csrfFieldMeta) return null;

    var csrfField = csrfFieldMeta.getAttribute('content');
    var csrfTokenMeta = document.querySelector('meta[name="' + csrfField + '"]');
    if (!csrfTokenMeta) return null;

    return {name: csrfField, token: csrfTokenMeta.getAttribute('content')};
  }

  function fetchAndSetCsrfMetaTag() {
    return new Promise(function (resolve, reject) {
      var existing = getCsrfMetaToken();
      if (existing) return resolve(existing);

      var xhr = new XMLHttpRequest();
      xhr.open('GET', '/csrf-input');
      xhr.setRequestHeader('Accept', 'application/json');
      xhr.onreadystatechange = function () {
        if (xhr.readyState === 4) {
          if (xhr.status === 200) {
            var data = JSON.parse(xhr.responseText);

            var head = document.head;

            var csrfFieldMeta = document.querySelector('meta[name="csrf_field_name"]');
            if (!csrfFieldMeta) {
              var metaField = document.createElement('meta');
              metaField.name = 'csrf_field_name';
              metaField.content = data.name;
              head.appendChild(metaField);
            }

            var metaToken = document.createElement('meta');
            metaToken.name = data.name;
            metaToken.content = data.value;
            head.appendChild(metaToken);

            resolve({name: data.name, token: data.value});
          } else {
            reject(new Error('Failed to fetch CSRF data: ' + xhr.status));
          }
        }
      };
      xhr.send();
    });
  }

  ckan.fetchCsrfToken = fetchAndSetCsrfMetaTag;

})(this.ckan);
