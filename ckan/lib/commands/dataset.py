from ckan.lib.commands import CkanCommand


class DatasetCmd(CkanCommand):
    '''Manage datasets

    Usage:
      dataset DATASET_NAME|ID            - shows dataset properties
      dataset show DATASET_NAME|ID       - shows dataset properties
      dataset list                       - lists datasets
      dataset delete [DATASET_NAME|ID]   - changes dataset state to 'deleted'
      dataset purge [DATASET_NAME|ID]    - removes dataset from db entirely
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 3
    min_args = 0

    def command(self):
        self._load_config()

        if not self.args:
            print self.usage
        else:
            cmd = self.args[0]
            if cmd == 'delete':
                self.delete(self.args[1])
            elif cmd == 'purge':
                self.purge(self.args[1])
            elif cmd == 'list':
                self.list()
            elif cmd == 'show':
                self.show(self.args[1])
            else:
                self.show(self.args[0])

    def list(self):
        import ckan.model as model
        print 'Datasets:'
        datasets = model.Session.query(model.Package)
        print 'count = %i' % datasets.count()
        for dataset in datasets:
            state = ('(%s)' % dataset.state) if dataset.state != 'active' \
                else ''
            print '%s %s %s' % (dataset.id, dataset.name, state)

    def _get_dataset(self, dataset_ref):
        import ckan.model as model
        dataset = model.Package.get(unicode(dataset_ref))
        assert dataset, 'Could not find dataset matching reference: %r' % \
            dataset_ref
        return dataset

    def show(self, dataset_ref):
        import pprint
        dataset = self._get_dataset(dataset_ref)
        pprint.pprint(dataset.as_dict())

    def delete(self, dataset_ref):
        import ckan.model as model
        dataset = self._get_dataset(dataset_ref)
        old_state = dataset.state

        model.repo.new_revision()
        dataset.delete()
        model.repo.commit_and_remove()
        dataset = self._get_dataset(dataset_ref)
        print '%s %s -> %s' % (dataset.name, old_state, dataset.state)

    def purge(self, dataset_ref):
        import ckan.model as model
        dataset = self._get_dataset(dataset_ref)
        name = dataset.name

        model.repo.new_revision()
        dataset.purge()
        model.repo.commit_and_remove()
        print '%s purged' % name
