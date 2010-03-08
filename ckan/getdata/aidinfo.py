from optparse import OptionParser
from swiss.tabular.gdocs import GDocsReaderSpreadsheet
from ckanclient import CkanClient
from time import sleep
import string
import pprint

class CkanLoader(object):

    def __init__(self):
        parser = OptionParser(self.usage)
        self.add_options(parser)
        (self.options, self.args) = parser.parse_args()
        self.init_ckanclient()

    def run(self):
        try:
            self.load_data()
        except KeyboardInterrupt:
            print ""
            print "exiting..."
            print

    def add_options(self, parser):
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
        if not self.options.ckan_api_location:
            print "Warning: CKAN API location not provided."
        if not self.options.ckan_api_key:
            print "Warning: CKAN API key not provided."
        self.ckanclient = CkanClient(
            base_location=self.options.ckan_api_location,
            api_key=self.options.ckan_api_key,
        )

    def load_data(self):
        pass


class AidProjectsLoader(CkanLoader):

    usage  = '''usage: %prog [path]'''

    def __init__(self):
        super(AidProjectsLoader, self).__init__()
        self.init_google_docs_spreadsheet()

    def add_options(self, parser):
        super(AidProjectsLoader, self).add_options(parser)
        parser.add_option(
            '--spreadsheet-key',
            dest='spreadsheet_key',
            help="""The projects databases metadata (a Google docs Spreadsheet key).""")
        parser.add_option(
            '--guser',
            dest='guser',
            help="""A Google account username.""")
        parser.add_option(
            '--gpass',
            dest='gpass',
            help="""A Google account password.""")

    def init_google_docs_spreadsheet(self):
        if not self.options.spreadsheet_key:
            print "Warning: Spreadsheet key not provided."
        if not self.options.guser:
            print "Warning: Google account username not provided."
        if not self.options.gpass:
            print "Warning: Google account password not provided."
        self.spreadsheet = GDocsSpreadsheet(
            spreadsheet_id = self.options.spreadsheet_key,
            username=self.options.guser,
            password=self.options.gpass,
        )

    def load_data(self):
        print "Reading Google docs Spreadsheet. Please wait..."
        self.read_spreadsheet_data()
        print "Converting Google docs Spreadsheet data to CKAN package data."
        self.convert_spreadsheet_data_to_packages()
        print "Putting CKAN package data on CKAN."
        self.put_packages_on_ckan()
        self.assert_spreadsheet_data_is_available_on_ckan()

    def read_spreadsheet_data(self):
        self.spreadsheet_data = self.spreadsheet.read()

    def convert_spreadsheet_data_to_packages(self):
        # Note well, headings are in first column (columns are entities).
        cells = {}
        # - discover working area.
        max_row_id = 1
        min_row_id = 1
        max_col_id = 1
        min_col_id = 1
        for i, entry in enumerate(self.spreadsheet_data.entry):
            try:
                row_id = entry.cell.row
                col_id = entry.cell.col
                data = entry.content.text
            except Exception, inst:
                msg = "Couldn't read entry: %s" % inst
                msg += "\n%s" % entry
                raise Exception, msg
            try:
                row_id = int(row_id)
                col_id = int(col_id)
            except:
                continue
            cells[(row_id, col_id)] = data
        coords = cells.keys()
        coords.sort()
        row_ids = [i[0] for i in coords]
        col_ids = [i[1] for i in coords]
        top_left_coord = (min(row_ids), min(col_ids))
        bottom_right_coord = (max(row_ids), max(col_ids))
        row_range = range(top_left_coord[0], bottom_right_coord[1]+1)
        col_range = range(top_left_coord[1], bottom_right_coord[0]+1)
        self.raw_entities = []
        self.headings = []
        #  - gather headings.
        for row_id in row_range:
            coord = (row_id, col_range[0])
            if coord in cells:
                heading = cells[coord]
            else:
                heading = ""
            self.headings.append(heading)
        print "Headings: %s" % ", ".join(self.headings)
        #  - gather entity attributes.
        for col_id in col_range[1:]:
            raw_entity = []
            self.raw_entities.append(raw_entity)
            for row_id in row_range:
                coord = (row_id, col_id)
                if coord in cells:
                    attribute = cells[coord]
                else:
                    attribute = ""
                raw_entity.append(attribute)
        #  - consolidate recorded entities.
        self.entities = []
        for i, raw_entity in enumerate(self.raw_entities):
            entity = {}
            self.entities.append(entity)
            for j, value in enumerate(raw_entity):
                spreadsheet_name = self.headings[j]
                entity[spreadsheet_name] = value.strip()
        print "  %s lines of data were found in the Spreadsheet." % len(self.entities)
        self.packages = []
        #  - construct packages.
        for entity in self.entities:
            if entity['Title'].strip() == "":
                continue
            package = {}
            self.packages.append(package)
            package_name = entity['Title'].lower()
            package_name = self.substitute_ascii_equivalents(package_name.decode('utf8'))
            package_name = "".join([c for c in package_name if c in string.letters+' '])
            package_name = "-".join([s for s in package_name.split(' ') if s])
            package['name'] = package_name
            package['title'] = entity['Title']
            package['url'] = entity['Website']
            package['maintainer'] = entity['Owner']
            package['maintainer_email'] = entity['Email']
            package['author'] = entity['Owner']
            package['author_email'] = entity['Email']
            notes = entity['Overview']
            if entity['Details']:
                notes += "\n\n## Details\n"
                notes += entity['Details']
            if entity['Contact']:
                notes += "\n\n## Contact\n"
                notes += entity['Contact']
            if entity['Owner']:
                notes += "\n\n## Owner\n"
                notes += entity['Owner']
            if entity['Operator']:
                notes += "\n\n## Operator\n"
                notes += entity['Operator']
            if entity['Funding']:
                notes += "\n\n## Funding\n"
                notes += entity['Funding']
            if entity['People']:
                notes += "\n\n## People\n"
                notes += entity['People']
            if entity['Data Overview']:
                notes += "\n\n## Data Overview\n"
                notes += entity['Data Overview']
            if entity['Database type']:
                notes += "\n\n## Database type\n"
                notes += entity['Database type']
            if entity['Standard compliance']:
                notes += "\n\n## Standard compliance\n"
                notes += entity['Standard compliance']
            if entity['Donor Type']:
                notes += "\n\n## Donor Type\n"
                notes += entity['Donor Type']
            if entity['Donor Details']:
                notes += "\n\n## Donor Details\n"
                notes += entity['Donor Details']
            if entity['Recipient Details']:
                notes += "\n\n## Recipient Details\n"
                notes += entity['Recipient Details']
            if entity['Humanitarian Aid']:
                notes += "\n\n## Humanitarian Aid\n"
                notes += entity['Humanitarian Aid']
            if entity['Development Aid']:
                notes += "\n\n## Development Aid\n"
                notes += entity['Development Aid']
            if entity['Contents']:
                notes += "\n\n## Contents\n"
                notes += entity['Contents']
            if entity['Data level']:
                notes += "\n\n## Data level\n"
                notes += entity['Data level']
            if entity['Are there projects in the pipeline?']:
                notes += "\n\n## Are there projects in the pipeline?\n"
                notes += entity['Are there projects in the pipeline?']
            if entity['Data broken down by sector?']:
                notes += "\n\n## Data broken down by sector?\n"
                notes += entity['Data broken down by sector?']
            package['notes'] = notes 
        print "  %s data packages with titles were extracted from the Spreadsheet." % len(self.packages)

    def put_packages_on_ckan(self):
        print "  putting %s packages on CKAN running at %s" % (len(self.packages), self.options.ckan_api_location)
        print ""
        sleep(1)
        for spreadsheet_package in self.packages:
            registered_package = self.ckanclient.package_entity_get(spreadsheet_package['name'])
            if self.ckanclient.last_status == 200:
                print "Package '%s' is already registered" % spreadsheet_package['name']
                sleep(0.25)
            elif self.ckanclient.last_status == 404 or '404' in str(self.ckanclient.last_url_error):
                print "Package '%s' not currently registered" % spreadsheet_package['name']
                print ""
                pprint.pprint(spreadsheet_package)
                print ""
                answer = raw_input("Do you want to register this package with CKAN now? [Y/n] ")
                if not answer or answer.lower()[0] != 'n':
                    print "Skipping '%s' package..." % spreadsheet_package['name']
                    print ""
                    sleep(1)
                    continue
                print "Registering package..."
                self.ckanclient.package_register_post(spreadsheet_package)
                if self.ckanclient.last_status == 200:
                    print "Registered package '%s' OK." % spreadsheet_package['name']
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

    def assert_spreadsheet_data_is_available_on_ckan(self):
        pass

    # Method taken from: http://code.activestate.com/recipes/251871/
    def substitute_ascii_equivalents(self, unicrap):
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
            0xa1:'!', 0xa2:'{cent}', 0xa3:'{pound}', 0xa4:'{currency}',
            0xa5:'{yen}', 0xa6:'|', 0xa7:'{section}', 0xa8:'{umlaut}',
            0xa9:'{C}', 0xaa:'{^a}', 0xab:'<<', 0xac:'{not}',
            0xad:'-', 0xae:'{R}', 0xaf:'_', 0xb0:'{degrees}',
            0xb1:'{+/-}', 0xb2:'{^2}', 0xb3:'{^3}', 0xb4:"'",
            0xb5:'{micro}', 0xb6:'{paragraph}', 0xb7:'*', 0xb8:'{cedilla}',
            0xb9:'{^1}', 0xba:'{^o}', 0xbb:'>>', 
            0xbc:'{1/4}', 0xbd:'{1/2}', 0xbe:'{3/4}', 0xbf:'?',
            0xd7:'*', 0xf7:'/'
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

#        spreadsheet_names = """
##        Title
##        Website
##        Overview
##        Details
#        Contact
##        Email
#        Owner
#        Operator
#        Funding
#        People
#        Data Overview
#        Database type
#        Standard compliance
#        Donor Type
#        Donor Details
#        Recipient Details
#        Humanitarian Aid
#        Development Aid
#        Contents
#        Data level
#        Are there projects in the pipeline?
#        Data broken down by sector?
#        """

class GDocsSpreadsheet(GDocsReaderSpreadsheet):

    def read(self, sheet_index=0):
        self.gd_client.source = self.source  # the spreadsheet key...
        self.gd_client.ProgrammaticLogin()
        spreadsheets_feed = self.gd_client.GetSpreadsheetsFeed()
        worksheets_feed = self.gd_client.GetWorksheetsFeed(self.source)
        worksheet_id = worksheets_feed.entry[sheet_index].id.text.split('/')[-1]
        return self.gd_client.GetCellsFeed(self.source, worksheet_id)


if __name__ == '__main__':
    AidProjectsLoader().run()



