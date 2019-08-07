# encoding: utf-8


def upgrade(migrate_engine):
    migrate_engine.execute(
        '''
        ALTER TABLE public.package_marsavin add column number_of_attributes text;
        ALTER TABLE public.package_marsavin add column creation_date timestamp;
        ALTER TABLE public.package_marsavin add column expiry_date timestamp;
        ALTER TABLE public.package_marsavin add column has_missing_values boolean;
        '''
    )
