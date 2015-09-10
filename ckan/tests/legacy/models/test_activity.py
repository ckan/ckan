import ckan.model as model

Activity = model.Activity
ActivityDetail = model.ActivityDetail


class TestActivityDetail(object):
    def test_by_activity_id(self):
        activity = Activity('user-id', 'object-id',
                            'revision-id', 'activity-type')
        activity.save()
        activity_detail = ActivityDetail(activity.id, 'object-id',
                                         'object-type', 'activity-type')
        activity_detail.save()
        activities = ActivityDetail.by_activity_id(activity.id)
        assert activities == [activity_detail], activity_detail
