Added CSRF protection that would protect all the forms against Cross-Site Request Forgery attacks.
This feature is enabled by default in CKAN core, extensions are excluded from CSRF protection till they are ready to implement the csrf_token to their forms.

To enable the CSRF protection in your extensions you would need to set:

`ckan.csrf_protection.ignore_extensions=False`

and to set csrf_token in your forms:

`{{ h.csrf_input() }}`

See the documentation at `https://docs.ckan.org/en/latest/extensions/best-practices.html` for more info.
