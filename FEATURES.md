
# Search Engines
- sitemap (/sitemap/sitemap.xml)
- robots.txt

# Harvesting

## CKAN Harvester Type

config settings
- api_key: api token of a registered user on the ckan being harvested from.
  allows harvesting private datasets
- organizations_filter_include: list (['strings']) - list organizations to include in the harvest
- organizations_filter_exclude: list (['strings']) - list organizations to exclude from the harvest
- groups_filter_include: list (['strings']) - list groups to include in the harvest
- groups_filter_exclude: list (['strings']) - list groups to exclude from the harvest
- field_filter_include: list ([{field:"", value:""}]) - list of fields and values to filter datasets by for including in harvest
- field_filter_exclude: list ([{field:"", value:""}]) - list of fields and values to filter datasets by for excluding from harvest

- clean_tags: munge tags to remove special characters
- force_all: boolean (true|false) - force harvester to gather all datasets even if the dataset was not updated since the last time the harvester was run. only datasets whos content have changed will be updated.
force_package_type

- default_tags: list - Set default tags if needed eg: ['waf', 'test']
- remote_groups: string ('only_local'|'create') -  populate group if exists,
  create remote groups, or nothing
- remote_orgs: string ('only_local'|'create') - same as above but for
  organizations. If organization can not be determined from dataset it falls
  back to the organization that owns the harvester.
- default_groups: list
- default_extras: dictinary
- override_extras: (default: False)

## CKAN Spatial Harvester Type
This is a custom harvester that allows harvesting datasets from a remote ckan
instance who's spatial geomitry intersects with a given polygon, multipolygon,
or bbox.

when using ckan spatial harvester the following harvester config settings are available, these are in adition to the ckan harvester config settings:

- spatial_filter_file: Path, relative to the src folder, to a file containing well known text formated polygons eg "./pacific_RA.wkt"
- spatial_filter: same as above but a literal text string in well know text format.
- spatial_crs: define the crs of the spatial coordinates (default: 4326)

note that when using the ckan spatial harvester, the catalogue you are harvesting
from must have implomented our modified /api/2/search/dataset/geo endpoint to
allow searching by polygon. The default endpoint only allows searching using
bounding box.
