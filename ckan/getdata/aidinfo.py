#!/usr/bin/env python
"""
AidInfo CKAN Package Loader.

This program remotely registers and updates CKAN packages that have been
recorded in a Google Spreadsheet. Instructions for users are below.

1 . Install software and software dependencies.

        $ easy_install ckanclient
        $ easy_install gdata
        $ wget http://knowledgeforge.net/ckan/trac/browser/ckan/getdata/aidinfo.py?format=raw


2.  Run with appropriate options (Google account, Google spreadsheet, CKAN service, and CKAN API key).

        $ python aidinfo.py --help
        $ python aidinfo.py [OPTIONS]


3. Report issues and contribute feedback.

    Private feedback:
 
        john.bywater@appropriatesoftware.net
        info@okfn.org

    Public mailing list:

        ckan-discuss@lists.okfn.org

"""

from optparse import OptionParser
from gdata.spreadsheet.service import SpreadsheetsService as GoogleSpreadsheetsService
from ckanclient import CkanClient
from time import sleep
import string
import pprint

class GoogleSpreadsheetReader(object):
    """
    Directs Google Spreadsheets service client to obtain spreadsheet cells.
    """

    def __init__(self, options):
        """Init the Google Spreadsheets service client."""
        self.options = options
        self.service = GoogleSpreadsheetsService()
        self.service.email = self.options.google_email
        self.service.password = self.options.google_password
        self.service.ProgrammaticLogin()

    def get_cells(self, sheet_index=0):
        """Returns a dict of cell data keyed by cell coordinate (row, col)."""
        cells = {}
        spreadsheet_key = self.options.google_spreadsheet_key
        sheets_feed = self.service.GetWorksheetsFeed(spreadsheet_key)
        sheet_id = sheets_feed.entry[sheet_index].id.text.split('/')[-1]
        cells_feed = self.service.GetCellsFeed(spreadsheet_key, sheet_id)
        for entry in cells_feed.entry:
            try:
                row_id = entry.cell.row
                col_id = entry.cell.col
                data = entry.content.text
            except Exception, inst:
                msg = "Couldn't read cell feed entry: %s" % inst
                msg += "\n%s" % entry
                raise Exception, msg
            try:
                row_id = int(row_id)
                col_id = int(col_id)
            except:
                continue
            cells[(row_id, col_id)] = data
        return cells


class CkanLoader(object):
    """
    Directs a CKAN service client to put obtained packages on CKAN.
    """
    
    usage  = '''usage: %prog [path]'''

    def __init__(self):
        """Sets up options and init the CKAN service client."""
        parser = OptionParser(self.usage)
        self.add_options(parser)
        (self.options, self.args) = parser.parse_args()
        self.init_ckanclient()

    def add_options(self, parser):
        """Adds options for CKAN serice location and REST API key."""
        parser.add_option(
            '--ckan-api-location',
            dest='ckan_api_location',
            default='http://127.0.0.1:5000/api',
            help="""The location of working CKAN REST API.""")
        parser.add_option(
            '--ckan-api-key',
            dest='ckan_api_key',
            help="""A valid CKAN REST API key.""")

    def init_ckanclient(self):
        """Init the CKAN client from options."""
        if not self.options.ckan_api_location:
            print "Warning: CKAN API location not provided."
        if not self.options.ckan_api_key:
            print "Warning: CKAN API key not provided."
        self.ckanclient = CkanClient(
            base_location=self.options.ckan_api_location,
            api_key=self.options.ckan_api_key,
        )

    def run(self):
        """Obtain packages and put them on CKAN."""
        try:
            self.packages = []
            self.obtain_packages()
            print "Putting %s packages on CKAN running at %s" % (len(self.packages), self.options.ckan_api_location)
            self.put_packages_on_ckan()
        except KeyboardInterrupt:
            print ""
            print "exiting..."
            print ""

    def obtain_packages(self):
        """Abstract method for obtaining packages."""
        raise Exception, "Abstract method not implemented."

    def put_packages_on_ckan(self):
        """Uses CKAN client to register (or update) obtained packages."""
        # Todo: Fix ckan or ckanclient, so this method isn't so long-winded.
        print ""
        sleep(1)
        for package in self.packages:
            registered_package = self.ckanclient.package_entity_get(package['name'])
            if self.ckanclient.last_status == 200:
                print "Package '%s' is already registered" % package['name']
                print ""
                pprint.pprint(package)
                print ""
                answer = raw_input("Do you want to update this package with CKAN now? [y/N] ")
                if not answer or answer.lower()[0] != 'y':
                    print "Skipping '%s' package..." % package['name']
                    print ""
                    sleep(1)
                    continue
                print "Updating package..."
                self.ckanclient.package_entity_put(package)
                if self.ckanclient.last_status == 200:
                    print "Updated package '%s' OK." % package['name']
                    sleep(1)
                elif self.ckanclient.last_status == 403 or '403' in str(self.ckanclient.last_url_error):
                    print "Error: Not authorised. Check your API key."
                    sleep(1)
                    sleep(1)
                    sleep(1)
                    sleep(1)
                elif self.ckanclient.last_http_error:
                    print "Error: CKAN returned status code %s: %s" % (
                        self.ckanclient.last_status, self.ckanclient.last_http_error)
                    sleep(1)
                    sleep(1)
                    sleep(1)
                elif self.ckanclient.last_url_error:
                    print "Error: URL problems: %s" % self.ckanclient.last_url_error
                    sleep(1)
                    sleep(1)
                    sleep(1)
                else:
                    raise Exception, "Error: CKAN request didn't work at all."
            elif self.ckanclient.last_status == 404 or '404' in str(self.ckanclient.last_url_error):
                print "Package '%s' not currently registered" % package['name']
                print ""
                pprint.pprint(package)
                print ""
                answer = raw_input("Do you want to register this package with CKAN now? [y/N] ")
                if not answer or answer.lower()[0] != 'y':
                    print "Skipping '%s' package..." % package['name']
                    print ""
                    sleep(1)
                    continue
                print "Registering package..."
                self.ckanclient.package_register_post(package)
                if self.ckanclient.last_status == 200:
                    print "Registered package '%s' OK." % package['name']
                    sleep(1)
                elif self.ckanclient.last_status == 403 or '403' in str(self.ckanclient.last_url_error):
                    print "Error: Not authorised. Check your API key."
                    sleep(1)
                    sleep(1)
                    sleep(1)
                    sleep(1)
                elif self.ckanclient.last_http_error:
                    print "Error: CKAN returned status code %s: %s" % (
                        self.ckanclient.last_status, self.ckanclient.last_http_error)
                    sleep(1)
                    sleep(1)
                    sleep(1)
                elif self.ckanclient.last_url_error:
                    print "Error: URL problems: %s" % self.ckanclient.last_url_error
                    sleep(1)
                    sleep(1)
                    sleep(1)
                else:
                    raise Exception, "Error: CKAN request didn't work at all."
            elif self.ckanclient.last_http_error:
                print "Error: CKAN returned status code %s: %s" % (
                    self.ckanclient.last_status, self.ckanclient.last_http_error)
                sleep(1)
                sleep(1)
                sleep(1)
            elif self.ckanclient.last_url_error:
                print "Error: URL problems: %s" % self.ckanclient.last_url_error
                sleep(1)
                sleep(1)
                sleep(1)
            else:
                raise Exception, "Error: CKAN request didn't work at all."

    def create_package(self, name, title='', url='', maintainer='', 
            maintainer_email='', author='', author_email='', notes='', 
            tags=[], extras={}, license_id=''):
        """Returns a CKAN REST API package from method arguments."""
        if not isinstance(tags, list):
            raise Exception, "Package tags must be a list: %s" % tags
        if not isinstance(extras, dict):
            raise Exception, "Package extras must be a dict: %s" % tags
        package = {}
        package['name'] = self.coerce_package_name(name)
        package['title'] = title
        package['url'] = url
        package['maintainer'] = maintainer
        package['maintainer_email'] = maintainer_email
        package['author'] = author
        package['author_email'] = author_email
        package['tags'] = tags
        package['extras'] = extras
        package['license_id'] = license_id
        return package

    def coerce_package_name(self, name):
        """Converts unicode string to valid CKAN package name."""
        # Todo: Probably needs to be finished off.
        name = self.substitute_ascii_equivalents(name)
        name = name.lower()
        return name

    def substitute_ascii_equivalents(self, unicrap):
        # Method taken from: http://code.activestate.com/recipes/251871/
        """This takes a UNICODE string and replaces Latin-1 characters with
            something equivalent in 7-bit ASCII. It returns a plain ASCII string. 
            This function makes a best effort to convert Latin-1 characters into 
            ASCII equivalents. It does not just strip out the Latin-1 characters.
            All characters in the standard 7-bit ASCII range are preserved. 
            In the 8th bit range all the Latin-1 accented letters are converted 
            to unaccented equivalents. Most symbol characters are converted to 
            something meaningful. Anything not converted is deleted.
        """
        xlate={0xc0:'A', 0xc1:'A', 0xc2:'A', 0xc3:'A', 0xc4:'A', 0xc5:'A',
            0xc6:'Ae', 0xc7:'C',
            0xc8:'E', 0xc9:'E', 0xca:'E', 0xcb:'E',
            0xcc:'I', 0xcd:'I', 0xce:'I', 0xcf:'I',
            0xd0:'Th', 0xd1:'N',
            0xd2:'O', 0xd3:'O', 0xd4:'O', 0xd5:'O', 0xd6:'O', 0xd8:'O',
            0xd9:'U', 0xda:'U', 0xdb:'U', 0xdc:'U',
            0xdd:'Y', 0xde:'th', 0xdf:'ss',
            0xe0:'a', 0xe1:'a', 0xe2:'a', 0xe3:'a', 0xe4:'a', 0xe5:'a',
            0xe6:'ae', 0xe7:'c',
            0xe8:'e', 0xe9:'e', 0xea:'e', 0xeb:'e',
            0xec:'i', 0xed:'i', 0xee:'i', 0xef:'i',
            0xf0:'th', 0xf1:'n',
            0xf2:'o', 0xf3:'o', 0xf4:'o', 0xf5:'o', 0xf6:'o', 0xf8:'o',
            0xf9:'u', 0xfa:'u', 0xfb:'u', 0xfc:'u',
            0xfd:'y', 0xfe:'th', 0xff:'y',
            #0xa1:'!', 0xa2:'{cent}', 0xa3:'{pound}', 0xa4:'{currency}',
            #0xa5:'{yen}', 0xa6:'|', 0xa7:'{section}', 0xa8:'{umlaut}',
            #0xa9:'{C}', 0xaa:'{^a}', 0xab:'<<', 0xac:'{not}',
            #0xad:'-', 0xae:'{R}', 0xaf:'_', 0xb0:'{degrees}',
            #0xb1:'{+/-}', 0xb2:'{^2}', 0xb3:'{^3}', 0xb4:"'",
            #0xb5:'{micro}', 0xb6:'{paragraph}', 0xb7:'*', 0xb8:'{cedilla}',
            #0xb9:'{^1}', 0xba:'{^o}', 0xbb:'>>', 
            #0xbc:'{1/4}', 0xbd:'{1/2}', 0xbe:'{3/4}', 0xbf:'?',
            #0xd7:'*', 0xf7:'/'
            }

        r = ''
        for i in unicrap:
            if xlate.has_key(ord(i)):
                r += xlate[ord(i)]
            elif ord(i) >= 0x80:
                pass
            else:
                r += str(i)
        return r


class AbstractGoogleSpreadsheetLoader(CkanLoader):
    """
    Obtains packages from a Google spreadsheet and puts them on CKAN.
    """

    def __init__(self):
        """Sets up a Google spreadsheet reader."""
        super(AbstractGoogleSpreadsheetLoader, self).__init__()
        self.spreadsheet = GoogleSpreadsheetReader(self.options)

    def add_options(self, parser):
        """Adds options for accessing Google spreadsheet."""
        super(AbstractGoogleSpreadsheetLoader, self).add_options(parser)
        parser.add_option(
            '--google-spreadsheet-key',
            dest='google_spreadsheet_key',
            help="""The projects databases metadata (a Google docs Spreadsheet key).""")
        parser.add_option(
            '--google-email',
            dest='google_email',
            help="""A Google account email address.""")
        parser.add_option(
            '--google-password',
            dest='google_password',
            help="""A Google account password for the email address.""")

    def obtain_packages(self):
        """Obtains packages from a Google spreadsheet."""
        self.read_spreadsheet()
        self.convert_cells_to_packages()

    def read_spreadsheet(self):
        """Obtains cells from a Google spreadsheet."""
        print "Reading Google spreadsheet. Please wait..."
        self.cells = self.spreadsheet.get_cells()

    def convert_cells_to_packages(self):
        """Abstract method for inferring CKAN packages from dict of cells."""
        raise Exception, "Abstract method not implemented."


class SimpleGoogleSpreadsheetLoader(AbstractGoogleSpreadsheetLoader):
    """
    Obtains packages from a "simple" Google spreadsheet and puts them on CKAN.
    """
    #Todo: More about what a "simple" spreadsheet consists of.

    HEADING_ROW_POSN = 0
    FIRST_ENTITY_ROW_POSN = 1

    def convert_cells_to_packages(self):
        """Infers CKAN packages from "simple" spreadsheet structure."""
        # Discover working area.
        coords = self.cells.keys()
        coords.sort()
        row_ids = [i[0] for i in coords]
        col_ids = [i[1] for i in coords]
        top_left_coord = (min(row_ids), min(col_ids))
        bottom_right_coord = (max(row_ids), max(col_ids))
        print "Working area of spreadsheet: top-left %s; bottom-right %s." % (top_left_coord, bottom_right_coord)
        row_range = range(top_left_coord[0], bottom_right_coord[0]+1)
        col_range = range(top_left_coord[1], bottom_right_coord[1]+1)
        self.raw_entities = []
        self.headings = []
        # Gather headings.
        for col_id in col_range:
            row_id = row_range[self.HEADING_ROW_POSN]
            coord = (row_id, col_id)
            if coord in self.cells:
                heading = self.cells[coord]
            else:
                heading = ""
            self.headings.append(heading)
        print "There are %s headings: %s" % (len(self.headings), ", ".join(self.headings))
        # Gather entity attributes.
        for row_id in row_range[self.FIRST_ENTITY_ROW_POSN:]:
            raw_entity = []
            self.raw_entities.append(raw_entity)
            for col_id in col_range:
                coord = (row_id, col_id)
                if coord in self.cells:
                    attribute = self.cells[coord]
                else:
                    attribute = ""
                raw_entity.append(attribute)
        # Consolidate recorded entities.
        self.entities = []
        for i, raw_entity in enumerate(self.raw_entities):
            entity = {}
            self.entities.append(entity)
            for j, value in enumerate(raw_entity):
                key = self.headings[j]
                entity[key] = value.strip()
        print "There are %s entities: %s" % (len(self.entities), ", ".join([self.coerce_package_name(e[self.headings[0]]) for e in self.entities]))
        # Construct packages.
        for entity in self.entities:
            package = self.entity_to_package(entity)
            if package:
                self.packages.append(package)
        print "There are %s metadata packages with titles extracted from the spreadsheet." % len(self.packages)

    def entity_to_package(self, entity):
        """Makes a CKAN package from "simple" spreadsheet entity."""
        if 'name' in entity:
            package = self.create_package(
                name=entity.pop('name'),
                title=entity.pop('title', ''),
                url=entity.pop('url', ''),
                maintainer=entity.pop('maintainer', ''),
                maintainer_email=entity.pop('maintainer_email', ''),
                author=entity.pop('author', ''),
                author_email=entity.pop('author_email', ''),
                notes=entity.pop('notes', ''),
                tags=[tag for tag in entity.pop('tags', '').split(' ')],
                license_id=entity.pop('license', ''),
                extras=entity,
            )
        else:
            package = None
        return package


class AidProjectsLoader(SimpleGoogleSpreadsheetLoader):
    """
    Obtains packages from Aid Projects spreadsheet and puts them on CKAN.
    """
    
    HEADING_ROW_POSN = 1
    FIRST_ENTITY_ROW_POSN = 4

    def entity_to_package(self, entity):
        """Makes a CKAN package from an Aid Projects spreadsheet entity."""
        return self.create_package(
            name=entity['unique_id'],
            title=entity['title'],
            url=entity['website_1'],
            maintainer='OKFN',
            maintainer_email='info@okfn.org',
            author='OKFN',
            author_email='info@okfn.org',
            notes=entity['overview'] + "\n\n## Details\n" + entity['details'],
            tags=["aidinfo"],
            extras=entity,
        #    license_id='other-open',
        )


class NorwegianGovernmentLoader(SimpleGoogleSpreadsheetLoader):
    """
    Obtains packages from Norwegian Government spreadsheet and puts them on CKAN.
    """
    
    HEADING_ROW_POSN = 2
    FIRST_ENTITY_ROW_POSN = 3

    def entity_to_package(self, entity):
        """Makes a CKAN package from Norwegian Government spreadsheet entity."""
        if entity.get('Unique identifier', ''):
            package = self.create_package(
                name=entity.pop('Unique identifier'),
                title=entity.pop('Title (description)', ''),
                url=entity.pop('Url to source of data', ''),
                maintainer=entity.pop('Updated by', ''),
                author=entity.pop('Updated by', ''),
                notes=entity.pop('notes', ''),
                tags=['norwegian-government-data'],
                extras=entity,
            )
        else:
            package = None
        return package

if __name__ == '__main__':
    AidProjectsLoader().run()
    #NorwegianGovernmentLoader().run()

