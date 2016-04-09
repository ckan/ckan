import ckan.lib.base as base

render = base.render


class DashboardController(base.BaseController):

    def main(self):
        return 'Main Dashboard'
