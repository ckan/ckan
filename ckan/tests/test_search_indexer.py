from threading import Thread

from ckan import model

class SearchIndexManagerThread(Thread):
    '''A thread controlling the SearchIndexManager - used by tests only
    '''
    _instance = None

    @classmethod
    def start(cls):
        if not cls._instance:
            print "THREAD CREATE"
            cls._instance = SearchIndexManagerThread()
        elif not cls._instance.is_alive():
            # exception occurred
            print "THREAD RECREATE"
            cls._instance = SearchIndexManagerThread()
        if not cls._instance.is_alive():
            print "THREAD START"
            cls._instance.daemon = True # so destroyed automatically
            super(SearchIndexManagerThread, cls._instance).start() #i.e. Thread.start

    @classmethod
    def stop(cls):
        cls._instance.manager.stop()

    def run(self):
        self.manager = model.SearchIndexManager()
        self.manager.run()
