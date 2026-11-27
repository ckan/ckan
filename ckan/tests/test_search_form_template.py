# encoding: utf-8

import ckan.lib.base as base


def test_search_form_blocks_can_be_extended(
    make_app, ckan_config, monkeypatch, tmp_path
):
    snippets = tmp_path / "snippets"
    snippets.mkdir()
    (snippets / "search_form.html").write_text(
        "{% ckan_extends %}\n"
        "{% block search_form_class %}{{ super() }} custom-search{% endblock %}\n"
    )
    monkeypatch.setitem(ckan_config, "extra_template_paths", str(tmp_path))
    app = make_app()

    with app.flask_app.test_request_context():
        html = base.render(
            "snippets/search_form.html",
            {"query": "", "count": 0, "type": "dataset"},
        )

    assert 'class="search-form custom-search"' in html
