from sqlalchemy import *
from migrate import *
import uuid


map = {
    u'OSI Approved::Mozilla Public License 1.1 (MPL)': 'mozilla1.1', 
    u'OKD Compliant::Creative Commons Attribution-ShareAlike': 'cc-by-sa', 
    u'OSI Approved::Nokia Open Source License': 'nokia', 
    u'OSI Approved::Computer Associates Trusted Open Source License 1.1': 'ca-tosl1.1', 
    u'OKD Compliant::Higher Education Statistics Agency Copyright with data.gov.uk rights': 'hesa-withrights', 
    u'OSI Approved::Lucent Public License Version 1.02': 'lucent1.02', 
    u'OSI Approved::Open Software License': 'osl-3.0', 
    u'OSI Approved::Motosoto License': 'motosoto', 
    u'OSI Approved::MIT license': 'mit-license', 
    u'OSI Approved::Mozilla Public License 1.0 (MPL)': 'mozilla', 
    u'OSI Approved::GNU General Public License v3 (GPLv3)': 'gpl-3.0', 
    u'OKD Compliant::UK Click Use PSI': 'ukclickusepsi', 
    u'OSI Approved::Eiffel Forum License': 'eiffel', 
    u'OSI Approved::Jabber Open Source License': 'jabber-osl', 
    u'OSI Approved::Open Group Test Suite License': 'opengroup', 
    u'OSI Approved::Entessa Public License': 'entessa', 
    u'OKD Compliant::Other': 'other-open', 
    u'OSI Approved::EU DataGrid Software License': 'eudatagrid', 
    u'OSI Approved::Zope Public License': 'zpl', 
    u'OSI Approved::Naumen Public License': 'naumen', 
    u'OSI Approved::wxWindows Library License': 'wxwindows', 
    u'OKD Compliant::GNU Free Documentation License (GFDL)': 'gfdl', 
    u'Non-OKD Compliant::Non-Commercial Other': 'other-nc', 
    u'OKD Compliant::Open Data Commons Public Domain Dedication and License (PDDL)': 'odc-pddl', 
    u'OSI Approved::NASA Open Source Agreement 1.3': 'nasa1.3', 
    u'OSI Approved::X.Net License': 'xnet', 
    u'OSI Approved::W3C License': 'W3C', 
    u'OSI Approved::Academic Free License': 'afl-3.0', 
    u'Non-OKD Compliant::Crown Copyright': 'ukcrown', 
    u'OSI Approved::RealNetworks Public Source License V1.0': 'real', 
    u'OSI Approved::Common Development and Distribution License': 'cddl1', 
    u'OSI Approved::Intel Open Source License': 'intel-osl', 
    u'OSI Approved::GNU General Public License (GPL)': 'gpl-2.0', 
    u'Non-OKD Compliant::Creative Commons Non-Commercial (Any)': 'cc-nc', 
    u'Non-OKD Compliant::Other': 'other-closed', 
    u'Other::License Not Specified': 'notspecified', 
    u'OSI Approved::Sybase Open Watcom Public License 1.0': 'sybase', 
    u'OSI Approved::Educational Community License': 'ecl2', 
    u'OSI Approved::Sun Industry Standards Source License (SISSL)': 'sun-issl', 
    u'OKD Compliant::Other (Public Domain)': 'other-pd', 
    u'OKD Compliant::Public Domain': 'other-pd', 
    u'OKD Compliant::Creative Commons Attribution': 'cc-by', 
    u'OSI Approved::OCLC Research Public License 2.0': 'oclc2', 
    u'OSI Approved::Artistic license': 'artistic-license-2.0', 
    u'OKD Compliant::Other (Attribution)': 'other-at', 
    u'OSI Approved::Sleepycat License': 'sleepycat', 
    u'OSI Approved::PHP License': 'php', 
    u'OKD Compliant::Creative Commons CCZero': 'cc-zero', 
    u'OSI Approved::University of Illinois/NCSA Open Source License': 'UoI-NCSA', 
    u'OSI Approved::Adaptive Public License': 'apl1.0', 
    u'OSI Approved::Ricoh Source Code Public License': 'ricohpl', 
    u'OSI Approved::Eiffel Forum License V2.0': 'ver2_eiffel', 
    u'OSI Approved::Python license (CNRI Python License)': 'pythonpl', 
    u'OSI Approved::Frameworx License': 'frameworx', 
    u'OSI Approved::IBM Public License': 'ibmpl', 
    u'OSI Approved::Fair License': 'fair', 
    u'OSI Approved::Lucent Public License (Plan9)': 'lucent-plan9', 
    u'OSI Approved::Nethack General Public License': 'nethack', 
    u'OSI Approved::Common Public License 1.0': 'cpal_1.0', 
    u'OSI Approved::Attribution Assurance Licenses': 'attribution', 
    u'OSI Approved::Reciprocal Public License': 'rpl1.5', 
    u'OSI Approved::Eclipse Public License': 'eclipse-1.0', 
    u'OSI Approved::CUA Office Public License Version 1.0': 'cuaoffice', 
    u'OSI Approved::Vovida Software License v. 1.0': 'vovidapl', 
    u'OSI Approved::Apple Public Source License': 'apsl-2.0', 
    u'OKD Compliant::UK Crown Copyright with data.gov.uk rights': 'ukcrown-withrights', 
    u'OKD Compliant::Local Authority Copyright with data.gov.uk rights': 'localauth-withrights', 
    u'OKD Compliant::Open Data Commons Open Database License (ODbL)': 'odc-odbl', 
    u'OSI Approved::New BSD license': 'bsd-license', 
    u'OSI Approved::Qt Public License (QPL)': 'qtpl', 
    u'OSI Approved::GNU Library or "Lesser" General Public License (LGPL)': 'lgpl-2.1', 
    u'OSI Approved::MITRE Collaborative Virtual Workspace License (CVW License)': 'mitre', 
    u'OSI Approved::Apache License, 2.0': 'apache2.0', 
    u'OSI Approved::Apache Software License': 'apache', 
    u'OSI Approved::Python Software Foundation License': 'PythonSoftFoundation', 
    u'OSI Approved::Sun Public License': 'sunpublic', 
    u'OSI Approved::zlib/libpng license': 'zlib-license'
}

def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    #print "Changing package license_ids to strings."

    # Get licenses, package license ids, and package revision license ids.
    old_license_titles = _get_old_license_titles(migrate_engine)
    old_package_license_ids = _get_old_package_license_ids(migrate_engine)
    old_package_revision_license_ids = _get_old_package_revision_license_ids(migrate_engine)
    _check_map_has_old_license_titles(old_license_titles, map)
    
    # Upgrade database scheme.
    drop_fk_constraint_on_package_table = "ALTER TABLE package DROP CONSTRAINT package_license_id_fkey;"
    drop_fk_constraint_on_package_revision_table = "ALTER TABLE package_revision DROP CONSTRAINT package_revision_license_id_fkey;"
    change_license_id_type_on_package_table = "ALTER TABLE package ALTER COLUMN license_id TYPE text;"
    change_license_id_type_on_package_revision_table = "ALTER TABLE package_revision ALTER COLUMN license_id TYPE text;"
    drop_licenses_table = "DROP TABLE license CASCADE;"
    
    migrate_engine.execute(drop_fk_constraint_on_package_table)
    migrate_engine.execute(drop_fk_constraint_on_package_revision_table)
    migrate_engine.execute(change_license_id_type_on_package_table)
    migrate_engine.execute(change_license_id_type_on_package_revision_table)
    migrate_engine.execute(drop_licenses_table)

    # Set package license ids, and package revision license ids.    
    new_package_license_ids = _switch_package_license_ids(
            old_package_license_ids, old_license_titles, map)
    new_package_revision_license_ids = _switch_package_license_ids(
            old_package_revision_license_ids, old_license_titles, map)
    _set_new_package_license_ids(migrate_engine, new_package_license_ids)
    _set_new_package_revision_license_ids(migrate_engine, new_package_revision_license_ids)

def downgrade(migrate_engine):
    raise NotImplementedError()

def _check_map_has_old_license_titles(old_license_titles, map):
    for title in old_license_titles.values():
        if title not in map:
            raise Exception, "The old license title '%s' wasn't found in the upgrade map. Decide which new license id should be substituted for this license and add an entry to the map (in ckan/migration/versions/018_adjust_licenses.py)." % title

def _get_old_license_titles(migrate_engine):
    "Returns a dict of old license titles, keyed by old license id."
    titles = {}
    select_licenses = "SELECT id, name FROM license;"
    q = migrate_engine.execute(select_licenses)
    for id, title in q:
        titles[id] = title
    return titles

def _get_old_package_license_ids(migrate_engine):
    "Returns a dict of old license ids, keyed by package id."
    old_ids = {}
    select_licenses = "SELECT id, license_id FROM package;"
    q = migrate_engine.execute(select_licenses)
    for id, license_id in q:
        old_ids[id] = license_id
    return old_ids

def _get_old_package_revision_license_ids(migrate_engine):
    "Returns a dict of old license ids, keyed by package_revision id."
    old_ids = {}
    select_licenses = "SELECT id, license_id FROM package_revision;"
    q = migrate_engine.execute(select_licenses)
    for id, license_id in q:
        old_ids[id] = license_id
    return old_ids

def _switch_package_license_ids(old_ids, old_license_titles, map):
    "Returns a dict of new license ids, keyed by package id."
    new_ids = {}
    for (package_id, old_license_id) in old_ids.items():
        if old_license_id != None:
            old_license_title = old_license_titles[old_license_id]
            new_license_id = map[old_license_title]
            new_ids[package_id] = new_license_id
            print "Switched license_id %s to %s" % (old_license_id, new_license_id)
    return new_ids

def _set_new_package_license_ids(migrate_engine, new_ids):
    for (package_id, license_id) in new_ids.items():
        _set_package_license_id(migrate_engine, package_id, license_id)

def _set_package_license_id(migrate_engine, package_id, license_id):
    set_package_license_id = """UPDATE package SET license_id ='%s' where id = '%s';""" % (license_id, package_id)
    migrate_engine.execute(set_package_license_id)

def _set_new_package_revision_license_ids(migrate_engine, new_ids):
    for (package_id, license_id) in new_ids.items():
        _set_package_revision_license_id(migrate_engine, package_id, license_id)

def _set_package_revision_license_id(migrate_engine, package_id, license_id):
    set_package_license_id = """UPDATE package_revision SET license_id ='%s' where id = '%s';""" % (license_id, package_id)
    migrate_engine.execute(set_package_license_id)


