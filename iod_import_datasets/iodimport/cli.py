import gzip
import click
try:
    from urllib import parser as urlparse
except ImportError:
    import urlparse
from subprocess import call
from openpyxl import load_workbook
from click_validate_url import URL
import helpers as h


@click.command()
@click.argument('file', type=click.Path(exists=True))
@click.argument('sheet', type=click.STRING)
@click.argument('remote', type=URL())
@click.argument('ownerorg', type=click.STRING)
@click.argument('apikey', type=click.STRING)
def cli(file, sheet, remote, ownerorg, apikey):
    """This script parses an iod xlsx file to
    CKAN format dataset and uploads to specified CKAN instance"""

    click.echo('Parsing file')
    wb = load_workbook(filename=file, read_only=True)
    ws = wb[sheet]

    datasets = []

    for idx, row in enumerate(ws.rows):

        if idx == 0:
            continue
        idx+=1

        dataset = {}

        dataset['owner_org'] = ownerorg
        dataset['private'] = False
        dataset['name'] = h.validate_not_empty(row[0].value, 'dataset name', idx)
        dataset['title'] = h.validate_not_empty(row[1].value, 'dataset title', idx)

        title_translated = {}
        title_translated['en'] = h.validate_not_empty(row[1].value, 'dataset title english', idx)
        title_translated['fa_IR'] = h.validate_not_empty(row[2].value, 'dataset title farsi', idx)
        dataset['title_translated'] = title_translated

        dataset['notes'] = row[3].value
        notes_translated = {}
        notes_translated['en'] = h.validate_not_empty(row[3].value, 'dataset notes english', idx)
        notes_translated['fa_IR'] = h.validate_not_empty(row[4].value, ' dataset notes farsi', idx)
        dataset['notes_translated'] = notes_translated
        dataset['tags_string'] = h.parse_string_to_array(row[5].value)
        dataset['tags'] = h.tags_string_to_list(dataset['tags_string'])
        dataset['date_start_gregorian'] = h.strftime(row[6].value, 'date start gregorian', idx)
        dataset['date_end_gregorian'] = h.strftime(row[7].value, 'date end gregorian', idx)
        dataset['date_start_iranian'] = h.strftime(row[8].value, 'date start iranian', idx)
        dataset['date_end_iranian'] = h.strftime(row[9].value, 'date end iranian', idx)
        dataset['publisher'] = row[10].value
        dataset['publisher_url'] = h.validate_url(row[11].value, idx)
        dataset['methodology'] = h.validate_not_empty(row[13].value, 'methodology', idx)
        dataset['license_id'] = h.validate_not_empty(row[14].value, 'license_id', idx)

        dataset['resources'] = []
        resource_en = {}
        resource_en['url'] = h.validate_url(row[15].value, idx, True)

        notes_translated_en = {}
        notes_translated_en['en'] = row[17].value if row[17].value else ''
        notes_translated_en['fa_IR'] = row[18].value if row[18].value else ''
        resource_en['notes_translated'] = notes_translated_en

        resource_en['publisher'] = row[19].value
        resource_en['publisher_url'] = row[20].value

        source_translated_en = {}
        source_translated_en['en'] = row[21].value
        source_translated_en['fa_IR'] = row[22].value
        resource_en['source_translated'] = source_translated_en
        resource_en['language'] = 'English'
        resource_en['cleaning_stage'] = h.validate_not_empty(row[24].value, 'resource cleaning stage', idx)
        resource_en['name'] = h.validate_not_empty(row[30].value, 'resource name', idx) + 'en'
        dataset['resources'].append(resource_en)

        resource_fa = {}
        resource_fa['url'] = h.validate_url(row[16].value, idx, True)

        notes_translated_fa = {}
        notes_translated_fa['en'] = row[17].value if row[17].value else ''
        notes_translated_fa['fa_IR'] = row[18].value if row[18].value else ''
        resource_fa['notes_translated'] = notes_translated_fa

        resource_fa['publisher'] = row[19].value
        resource_fa['publisher_url'] = row[20].value

        source_translated_fa = {}
        source_translated_fa['en'] = row[21].value
        source_translated_fa['fa_IR'] = row[22].value
        resource_fa['source_translated'] = source_translated_fa
        resource_fa['language'] = 'Farsi'
        resource_fa['cleaning_stage'] = h.validate_not_empty(row[24].value, 'resource cleaning stage', idx)
        resource_fa['name'] = h.validate_not_empty(row[30].value, 'resource name', idx) + 'fa'
        dataset['resources'].append(resource_fa)
        dataset['groups'] =  h.themes_list_to_list_of_dicts(h.parse_string_to_array(row[26].value))

        datasets.append(dataset)

    with open("datasets.jsonl.gz", 'wb') as jsonl_output:
        with gzip.GzipFile(fileobj=jsonl_output) as jsonl_output_gz:
            for dataset in datasets:
                jsonl_output_gz.write(h.compact_json(dataset,
                                                sort_keys=True) + b'\n')
    click.echo('Parsing file finished')

    click.echo('Starting upload')
    call(["ckanapi", "load", "datasets", "-a", apikey, "-I", "datasets.jsonl.gz", "-z", "-p", "3", "-r",
          remote])
    click.echo('Upload finished')











