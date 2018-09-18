# encoding: utf-8


def skip_based_on_legacy_engine_version(op, filename):
    conf = op.get_context().config
    version = conf.get_main_option(u'sqlalchemy_migrate_version')
    if version:
        return int(version) >= int(filename.split(u'_', 1)[0])
