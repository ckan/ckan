/**
 * This script is used to add the CSRF token to the HTMX request headers.
 *
 * Needs to be loaded after htmx and csrf-token module
 *
 */

htmx.on('htmx:configRequest', (event) => {
  const verb = event.detail.verb.toUpperCase();
  // Only attach CSRF for unsafe methods
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(verb)) {
    ckan.fetchCsrfToken().then(csrf => {
      event.detail.headers['X-CSRFToken'] = csrf.token;
    }).catch(err => {
      console.error('Failed to fetch CSRF token for HTMX:', err);
    })
  }
});
