try:
    import cProfile as profile
except ImportError:
    import profile
import functools
import pstats

from flask import current_app
from flask_debugtoolbar.panels import DebugPanel
from flask_debugtoolbar.utils import format_fname


class ProfilerDebugPanel(DebugPanel):
    """
    Panel that displays the time a response took with cProfile output.
    """
    name = 'Profiler'

    user_activate = True

    def __init__(self, jinja_env, context={}):
        DebugPanel.__init__(self, jinja_env, context=context)
        if current_app.config.get('DEBUG_TB_PROFILER_ENABLED'):
            self.is_active = True

    def has_content(self):
        return bool(self.profiler)

    def process_request(self, request):
        if not self.is_active:
            return

        self.profiler = profile.Profile()
        self.stats = None

    def process_view(self, request, view_func, view_kwargs):
        if self.is_active:
            func = functools.partial(self.profiler.runcall, view_func)
            functools.update_wrapper(func, view_func)
            return func

    def process_response(self, request, response):
        if not self.is_active:
            return False

        if self.profiler is not None:
            self.profiler.disable()
            try:
                stats = pstats.Stats(self.profiler)
            except TypeError:
                self.is_active = False
                return False
            function_calls = []
            for func in stats.sort_stats(1).fcn_list:
                current = {}
                info = stats.stats[func]

                # Number of calls
                if info[0] != info[1]:
                    current['ncalls'] = '%d/%d' % (info[1], info[0])
                else:
                    current['ncalls'] = info[1]

                # Total time
                current['tottime'] = info[2] * 1000

                # Quotient of total time divided by number of calls
                if info[1]:
                    current['percall'] = info[2] * 1000 / info[1]
                else:
                    current['percall'] = 0

                # Cumulative time
                current['cumtime'] = info[3] * 1000

                # Quotient of the cumulative time divded by the number of
                # primitive calls.
                if info[0]:
                    current['percall_cum'] = info[3] * 1000 / info[0]
                else:
                    current['percall_cum'] = 0

                # Filename
                filename = pstats.func_std_string(func)
                current['filename_long'] = filename
                current['filename'] = format_fname(filename)
                function_calls.append(current)

            self.stats = stats
            self.function_calls = function_calls
            # destroy the profiler just in case
        return response

    def title(self):
        if not self.is_active:
            return "Profiler not active"
        return 'View: %.2fms' % (float(self.stats.total_tt)*1000,)

    def nav_title(self):
        return 'Profiler'

    def nav_subtitle(self):
        if not self.is_active:
            return "in-active"
        return 'View: %.2fms' % (float(self.stats.total_tt)*1000,)

    def url(self):
        return ''

    def content(self):
        if not self.is_active:
            return "The profiler is not activated, activate it to use it"

        context = {
            'stats': self.stats,
            'function_calls': self.function_calls,
        }
        return self.render('panels/profiler.html', context)
