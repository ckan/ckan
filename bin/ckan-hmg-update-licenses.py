import os

import loadconfig
path = os.path.abspath('development.ini')
loadconfig.load_config(path)

import ckan.model as model

non_compliant_crown = model.License.by_name(u'Non-OKD Compliant::Crown Copyright').id
compliant_crown = model.License.by_name(u'OKD Compliant::UK Crown Copyright with data.gov.uk rights').id
click_use = model.License.by_name(u'OKD Compliant::UK Click Use PSI').id
hesa = model.License.by_name(u'OKD Compliant::Higher Education Statistics Agency Copyright with data.gov.uk rights').id
assert non_compliant_crown
assert compliant_crown
assert click_use
assert hesa

q_packages = model.Session.query(model.Package)

changes = {}
def made_change(description, package_name):
    if not changes.has_key(description):
        changes[description] = []
    changes[description].append(package_name)

def new_revision():
    rev = model.repo.new_revision() 
    rev.author = 'license-updater'
    rev.message = u'Update of licenses to OKD compliant'
new_revision()

pkg_names = [pkg.name for pkg in q_packages.all()]
for i, pkg_name in enumerate(pkg_names):
    pkg = model.Package.by_name(pkg_name)
    assert pkg
    if pkg.author_email and 'hesa.ac.uk' in pkg.author_email:
        pkg.license = model.Session.query(model.License).get(hesa)
        made_change('HESA license', pkg.name)
    elif pkg.license.id == non_compliant_crown:
        pkg.license = model.Session.query(model.License).get(compliant_crown)
        made_change('Crown Copyright -> Crown Copyright OKD compliant', pkg.name)
    elif pkg.license.id == click_use:
        pkg.license = model.Session.query(model.License).get(compliant_crown)
        made_change('Click Use -> Crown Copyright OKD compliant', pkg.name)
    else:
        made_change('No change - left as license %s' % pkg.license, pkg.name)
    model.Session.flush()

    if i+1 % 100 == 0:
        model.repo.commit_and_remove()
        new_revision()

model.repo.commit_and_remove()

for description, packages in changes.items():
    print 'CHANGE: %s (%i)' % (description, len(packages))
