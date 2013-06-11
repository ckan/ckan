import nose.tools as tools

import ckan.model as model
import ckan.logic as logic


class TestMemberLogic(object):
    def test_model_name_to_class(self):
        assert logic.model_name_to_class(model, 'package') == model.Package
        tools.assert_raises(logic.ValidationError,
                            logic.model_name_to_class,
                            model,
                            'inexistent_model_name')
