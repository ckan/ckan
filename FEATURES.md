
# Search Engines

- sitemap (/sitemap/sitemap.xml)
- robots.txt

## Generating a sitemap

Generating a sitemap can enable searching and harvesting of a CIOOS catalogue by some external organizations like the [Ocean Data and Information System (ODIS)](https://catalogue.odis.org/).  

```bash
 sudo docker exec -it ckan ckan --config=/etc/ckan/production.ini sitemap create
```

The sitemap needs to be regenerated whenever a new dataset is added or removed to accurately reflect the contents of the catalogue.  Scheduling this task to occur daily is perhaps the easiest way to ensure the sitemap is reasonably up-to-date.

# Harvesting

## CKAN Harvester Type

Config settings:

- api_key: api token of a registered user on the ckan being harvested from.
  allows harvesting private datasets
- organizations_filter_include: list (['strings']) - list organizations to include in the harvest
- organizations_filter_exclude: list (['strings']) - list organizations to exclude from the harvest
- groups_filter_include: list (['strings']) - list groups to include in the harvest
- groups_filter_exclude: list (['strings']) - list groups to exclude from the harvest
- field_filter_include: list ([{field:"", value:""}]) - list of fields and values to filter datasets by for including in harvest
- field_filter_exclude: list ([{field:"", value:""}]) - list of fields and values to filter datasets by for excluding from harvest

- clean_tags: munge tags to remove special characters
- force_all: boolean (true|false) - force harvester to gather all datasets even if the dataset was not updated since the last time the harvester was run. Only datasets whose content have changed will be updated.
force_package_type

- default_tags: list - Set default tags if needed eg: ['waf', 'test']
- remote_groups: string ('only_local'|'create') -  populate group if exists,
  create remote groups, or nothing
- remote_orgs: string ('only_local'|'create') - same as above but for
  organizations. If organization can not be determined from dataset it falls
  back to the organization that owns the harvester.
- default_groups: list
- default_extras: dictionary
- override_extras: (default: False)

## CKAN Spatial Harvester Type
This is a custom harvester that allows harvesting datasets from a remote ckan
instance who's spatial geometry intersects with a given polygon, multipolygon,
or bbox.

when using ckan spatial harvester the following harvester config settings are available, these are in addition to the ckan harvester config settings:

- spatial_filter_file: Path, relative to the src folder, to a file containing well known text formatted polygons eg "./pacific_RA.wkt"
- spatial_filter: same as above but a literal text string in well know text format.
- spatial_crs: define the crs of the spatial coordinates (default: 4326)

note that when using the ckan spatial harvester, the catalogue you are harvesting
from must have implemented our modified /api/2/search/dataset/geo endpoint to
allow searching by polygon. The default endpoint only allows searching using
bounding box.

# Menu

it is now possible to sync the menu items from a compatible wordpress site, into ckan. The wordpress instance must implement the following endpoints

```text
/wp-json/ra/menu/en
/wp-json/ra/menu/fr
```

To use, first set the 'Custome Header Filename' config option to the appropriate value, for example `/menu/pacific_menu_list.html`.  If you are using an existing file then you could stop there. CKAN will pull the menu items from the appropriate template in the /menu/ folder.

To sync menu items from a wordpress site we run the `menu create` CLI command.

## CLI Command Usage

```bash
ckan  menu create --url [path to wordpress api endpoint] --output [output menu list file (default: /menu/menu_list.html)]
```

## Example

```bash
sudo docker exec -u root -it ckan  ckan --config /etc/ckan/production.ini menu create --url https://cioospacific.ca/wp-json/ra/menu/ --output /menu/pacific_menu_list.html
```

# organization_list api end point
added a fq paramiter to organization_list so that results can be filtered on fields other then name, description, and title.
not queries are supported by adding a negative sign in front of the field name.

example query ```/api/3/action/organization_list?q=hakai&all_fields=true&include_extras=true&fq=-organization-uri:code"_ "",&fq=organization-uri:__```
