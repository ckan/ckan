from sqlalchemy import MetaData
import ckan.model as model
from ckan.model.license import License, LicenseRegister, license_statuses
import ckan.lib.dictization.model_save as model_save
from ckan.model.package import Package
from pylons import config


def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine

    context = {'model': model, 'session': model.Session}

    migrate_engine.execute(
        '''
        CREATE TYPE license_status AS ENUM (
            'active',
            'deleted'
        );

        CREATE TABLE license (
            id text NOT NULL,
            title text NOT NULL,
            is_okd_compliant boolean,
            is_generic boolean,
            url text,
            home_url text,
            extras text,
            status license_status NOT NULL
        );

        ALTER TABLE license
            ADD CONSTRAINT license_pkey PRIMARY KEY (id);
        '''
    )

    if not config.get('licenses_group_url', None):
        ## Move used licenses to DB
        licenses_dict = {}
        for license in LicenseRegister().get_default_license_list().values():
            licenses_dict.setdefault(license.id, {
                'id': license.id,
                'title': license.title,
                'is_okd_compliant': license.is_okd_compliant,
                'url': license.url,
                'is_generic': license.is_generic,
                'extras': {},
                'status': license.status,
            })

        licenses = {}
        for package in model.Session.query(Package).all():
            license_data = licenses_dict[package.license_id] \
                if licenses_dict.get[package.license_id] else {
                    'id': package.license_id,
                    'title': package.license_id,
                    'is_okd_compliant': False,
                    'url': '',
                    'is_generic': False,
                    'extras': {},
                    'status': 'active',
                }
            licenses.setdefault(package.license_id, license_data)

        if licenses:
            for item in licenses:
                model_save.license_save(item, context)
        else:
            # We ned to create one license
            data_dict = {
                'id': 'cc-by',
                'title': 'Creative Commons Attribution',
                'is_okd_compliant': True,
                'url': 'http://www.opendefinition.org/licenses/cc-by',
                'is_generic': True,
                'status': 'active',
            }
            model_save.license_save(data_dict, context)

            data_dict = {
                'id': 'odc-by',
                'title': 'Open Data Commons Attribution License',
                'is_okd_compliant': True,
                'url': 'http://www.opendefinition.org/licenses/odc-by',
                'is_generic': False,
                'status': 'active',
            }
            model_save.license_save(data_dict, context)

        # commits changes to DB
        model.Session.commit()
