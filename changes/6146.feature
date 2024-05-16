Make snippets faster by treating them as `with` and `include` tags instead of
rendering them recursively.

Snippets without parameters will now be cached by jinja2 (this is the default
behavior of {% include without context %}) If you use snippets without
parameters that include dynamic content add any parameter to prevent
caching.
