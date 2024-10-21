import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.model as model

class ViewCountPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.ITemplateHelpers)

    def get_helpers(self):
        return {
            'get_view_count': self.get_view_count
        }

    def get_view_count(self, dataset_id):
        query = model.Session.execute("""
            SELECT COUNT(*)
            FROM tracking_summary
            WHERE package_id = :dataset_id
        """, {'dataset_id': dataset_id})
        
        result = query.fetchone()
        return result[0] if result else 0
