The default value of `beaker.session.type` has been upgraded to use cookie-based sessions.
This change affects all sites utilizing Beaker sessions.

The `beaker.session.samesite` configuration option has been introduced, allowing you to specify the SameSite attribute for session cookies.
This attribute determines how cookies are sent in cross-origin requests, enhancing security and privacy.

Important Note:

To ensure proper functionality when using cookie-based sessions, it is now required to set `beaker.session.validate_key` appropriately.
