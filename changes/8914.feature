Navigate dataset search pages, facets and sort order without page reloads.

The `page_primary_action`, `form` and `package_search_results_list` blocks
have been moved from `templates/package/search.html` to
`templates/package/snippets/search_results.html` so that dataset search
results may be updated without rendering the whole page. Extensions that
override these blocks will need to be updated.
