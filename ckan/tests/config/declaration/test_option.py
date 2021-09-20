from ckan.config.declaration import Option


class TestDetails:
    def test_default_value(self):
        assert Option("def").has_default()
        assert Option("").has_default()
        assert Option(None).has_default()
        assert Option(False).has_default()

        assert not Option().has_default()
