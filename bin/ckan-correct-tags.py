# Utility script to strip commas out of tag names
# (in there because of bugs in form script that did not strip commas):w

import os
# here_dir = os.path.dirname(os.path.abspath(__file__))
# conf_dir = os.path.dirname(os.path.dirname(here_dir))
conf_dir = os.path.abspath('./')
print conf_dir
conf_file = os.path.join(conf_dir, 'development.ini')
# conf_file = os.path.join(conf_dir, 'ckan.net.ini')

from paste.deploy import loadapp, CONFIG
import paste.deploy

conf = paste.deploy.appconfig('config:' + conf_file)
CONFIG.push_process_config({'app_conf': conf.local_conf,
                            'global_conf': conf.global_conf}) 

import ckan.models

def correct():
    print 'Beginning processing'
    for tag in ckan.models.Tag.select():
        print 'Processing tag: ', tag.name
        if tag.name.endswith(','):
            print 'Tag with comma found'
            correct_name = tag.name[:-1]
            print 'Correct name: ', correct_name
            # is there a tag already out there with this name?
            existing = list(ckan.models.Tag.selectBy(name=correct_name))
            if len(existing) == 0: # no -- then just rename
                print 'Renaming'
                tag.name = correct_name
            else:
                print 'Replacing'
                replacement = existing[0]
                pkgtags = ckan.models.package.PackageTag.selectBy(tag=tag)
                for pkg2tag in pkgtags:
                    # replace or delete -- should  check whether already has the
                    # link ... but will not bother as assume no-one has ever done
                    # economics and economics, for same package
                    pkg2tag.tag == replacement
                tag.purge()

def test_setup():
    tag = ckan.models.Tag(name='blah2,')
    tag2 = ckan.models.Tag(name='russian,')
    pkg = ckan.models.Package.selectBy(name='annakarenina')
    ckan.models.PackageTag(tag=tag, package=pkg)
    ckan.models.PackageTag(tag=tag2, package=pkg)

# test_setup()
correct()
