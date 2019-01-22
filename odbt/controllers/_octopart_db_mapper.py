import os, time, re
import requests
import octopart
from tabulate import tabulate
from pathlib import Path
from octopart import models as octomodels
from datetime import datetime
from selenium import webdriver
from cement import App, shell
from fake_useragent import UserAgent
from ._utils import Utils
from google import google

common_col_names = \
       ('ID',
        'Preferred',
        'Description',
        'Comment',
        'Footprint Ref',
        'Footprint Path',
        'Library Ref',
        'Library Path',
        'Supplier 1',
        'Supplier Part Number 1',
        'Supplier 2',
        'Supplier Part Number 2',
        'Manufacturer 1',
        'Manufacturer Part Number 1',
        'Manufacturer 2',
        'Manufacturer Part Number 2',
        'Status',
        'Release Version',
        'Designer',
        'Creation Date',
        'Value',
        'Tolerance',
        'Voltage Rating',
        'Material Type',
        'Power Rating',
        'Case Style',
        'HelpURL',
        'ComponentLink1Description',
        'ComponentLink1URL',
        'ComponentLink2Description',
        'ComponentLink2URL')

class OctopartDBMapper:
    def __init__(self, app: App, table):

        # State variables
        self.app = app
        self.config = app.config
        self.table = table
        self.datasheet_file = Path()

        # Component categories
        self.categories = []

        # Create dict from columns to map data on the database and store original data
        self.dbmapping_original = {}
        self.dbmapping_new = {}
        for col in common_col_names:
            self.dbmapping_original[col.replace(' ', '_')] = None
            self.dbmapping_new[col.replace(' ', '_')] = None

    def _replace_special_chars(self, text: str):
        specialharsDictionary = {u'Ü': 'U', u'ü': 'u'}
        umap = {ord(key): val for key, val in specialharsDictionary.items()}
        return text.translate(umap)


    def _fetch_supplier_link(self, supplier: octomodels.PartOffer):
        options = webdriver.ChromeOptions()
        # options.add_argument('headless')
        # options.add_argument('disable-gpu')

        if supplier.seller == 'Farnell':
            browser = webdriver.Chrome(executable_path=str(
                                           Path(os.path.dirname(__file__) + "/../../bin/chromedriver.exe")))
            url = 'https://nl.farnell.com/{0}'.format(supplier.sku)
            browser.get(url)
            while True:
                if 'farnell.com/{0!s}'.format(supplier.sku) not in browser.current_url:
                    url = browser.current_url.split('?')[0]
                    browser.quit()
                    return url
                time.sleep(1)
        elif supplier.seller == 'Digi-Key':
            result = google.search('{} - {}'.format(supplier.seller, supplier.sku))
            return result[0].link
        # Fallback to Octopart redirect URL
        else:
            return supplier.product_url

    def _find_seller(self, octo: octomodels.Part, name: str):
        for index, offer in enumerate(octo.offers, 0):
            if offer.seller == name:
                return index

        return None

    def _get_component_categories(self, octo: octomodels.Part):
        try:
            for category_uid in octo.category_uids:
                self.categories.append(octopart.get_category(category_uid))
        except KeyError:
            pass

    def _purge_empty_keys(self, dictionary: dict):
        # Purge empty columns from mapping
        dictionary = {k: v for k, v in dictionary.items() if v}

        # Restore original column names
        dictionary_keys = []
        dictionary_values = []
        for k, v in dictionary.items():
            dictionary_keys.append(str(k).replace('_', ' '))
            dictionary_values.append(str(v))

        return {'dict': dictionary, 'keys': dictionary_keys, 'values': dictionary_values}

    def _update_if_empty(self, key, value):
        if self.dbmapping_original[key] is None:
            self.dbmapping_new[key] = value

    def _exists(self, key):
        if self.dbmapping_original[key] is not None:
            return True
        else:
            return False

    def _empty(self, key):
        if self.dbmapping_original[key] is not None:
            return False
        else:
            return True

    def update_item_database(self, interactive=True):
        # Preview data
        headers = ['Key', 'Original Data', 'New Data']
        table = []
        for k, v in self.dbmapping_original.items():
            if v != self.dbmapping_new[k]:
                table.append((k, v, self.dbmapping_new[k]))

        if len(table):
            self.app.print(tabulate(table, headers=headers))

            # Auto accept if non-interactive
            accept = 'y'
            if interactive:
                accept = shell.Prompt("Execute component update?", options=['y', 'n']).prompt()

            dbmapping_new = self._purge_empty_keys(self.dbmapping_new)

            # Get possible ID
            sql_id = dbmapping_new['dict'].pop('ID', None)

            if accept == 'y':
                # Create query from data list
                kv_pairs = ','.join(['[{0}]=\'{1}\''.format(str(k.replace('_', ' ')),
                                                            str(v)) for k, v in dbmapping_new['dict'].items()])
                query = 'UPDATE [{0}] SET {1} WHERE ID={2}'.format(self.table, kv_pairs, sql_id)
                self.app.db.execute(query)
                self.app.db.commit()
                self.app.print("Updating component in database")
            else:
                # Cleanup
                self.app.print("No update, cleanup...")
                if self.dbmapping_original['HelpURL'] is None:
                    self.app.print("Remove downloaded datasheet")
                    self.datasheet_file.unlink()

    def insert_item_database(self, interactive=True):
        dbmapping_new = self._purge_empty_keys(self.dbmapping_new)

        # Preview data
        self.app.print(tabulate([(k, v) for k, v in dbmapping_new['dict'].items()]))

        # Auto accept if non-interactive
        accept = 'y'
        if interactive:
            accept = shell.Prompt("Execute component add?", options=['y', 'n'], default='y').prompt()

        # Populate the database with the new data
        if accept == 'y':
            # Create query from data list
            query = 'INSERT INTO [{0}] ([{1}]) VALUES (\'{2}\')'.format(self.table,
                                                                      '], ['.join(dbmapping_new['keys']),
                                                                      '\', \''.join(dbmapping_new['values']))
            self.app.db.execute(query)
            self.app.db.commit()
            self.app.print("Adding component to database")
        else:
            # Cleanup
            self.app.print("No add, cleanup...")
            if self.dbmapping_new['HelpURL'] is not None:
                self.app.print("Remove downloaded datasheet")
                self.datasheet_file.unlink()

    def populate_original_data(self, sql_id):
        query = 'SELECT * FROM [{0}] WHERE ID={1}'.format(self.table, sql_id)
        self.app.db.execute(query)
        row = self.app.db.fetchone()

        for col in common_col_names:
            try:
                self.dbmapping_original[col.replace(' ', '_')] = row.__getattribute__(col)
                self.dbmapping_new[col.replace(' ', '_')] = row.__getattribute__(col)
            except AttributeError:
                pass
        pass

    def spec(self, octo: octomodels.Part):
        """ Populate specification fields in the database dict """
        self.app.print('Filling specs ...')

        # Get component categories
        self._get_component_categories(octo)

        # Independent fields
        self._update_if_empty('Description', octo.short_description)
        self._update_if_empty('Manufacturer_1', self._replace_special_chars(octo.manufacturer.upper()))
        self._update_if_empty('Manufacturer_Part_Number_1', octo.mpn)
        self._update_if_empty('Designer', self.config.get('odbt', 'db_designer'))
        self._update_if_empty('Creation_Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        # Optional fields
        self.dbmapping_new['Status'] = octo.specs['lifecycle_status'].value[0] \
            if 'lifecycle_status' in octo.specs.keys() else self.dbmapping_original['Status']

        # Fields based on component type
        if 'Aluminum Electrolytic Capacitors' in [c.name for c in self.categories]:
            self._update_if_empty('Library_Ref', 'Capacitor Polarized')

            if 'dielectric_material' in octo.specs.keys():
                value = octo.specs['dielectric_material'].value[0]
                self._update_if_empty('Material_Type', value.upper())

        if 'Capacitors' in [c.name for c in self.categories]:
            self._update_if_empty('Library_Ref', 'Capacitor')

            if 'capacitance' in octo.specs.keys():
                value = octo.specs['capacitance'].value[0]
                suffix = octo.specs['capacitance'].metadata['unit']['symbol']
                self._update_if_empty('Value', Utils.eng_string(value, suffix=suffix))

            if 'voltage_rating_dc' in octo.specs.keys():
                value = octo.specs['voltage_rating_dc'].value[0]
                suffix = octo.specs['voltage_rating_dc'].metadata['unit']['symbol']
                self._update_if_empty('Voltage_Rating', Utils.eng_string(value, suffix=suffix))

            if 'capacitance_tolerance' in octo.specs.keys():
                value = octo.specs['capacitance_tolerance'].value[0]
                self._update_if_empty('Tolerance', value)

            if 'dielectric_characteristic' in octo.specs.keys():
                value = octo.specs['dielectric_characteristic'].value[0]
                self._update_if_empty('Material_Type', value.upper())

            if 'case_package' in octo.specs.keys():
                value = octo.specs['case_package'].value[0]
                self._update_if_empty('Case_Style', value)
                self._update_if_empty('Footprint_Ref', 'C-{}'.format(value))

        if 'Resistors' in [c.name for c in self.categories]:
            self._update_if_empty('Library_Ref', 'Resistor')

            if 'resistance' in octo.specs.keys():
                value = octo.specs['resistance'].value[0]
                suffix = octo.specs['resistance'].metadata['unit']['symbol']
                self._update_if_empty('Value', Utils.eng_string(value, suffix=suffix))

            if 'voltage_rating_dc' in octo.specs.keys():
                value = octo.specs['voltage_rating_dc'].value[0]
                suffix = octo.specs['voltage_rating_dc'].metadata['unit']['symbol']
                self._update_if_empty('Voltage_Rating', Utils.eng_string(value, suffix=suffix))

            if 'resistance_tolerance' in octo.specs.keys():
                value = octo.specs['resistance_tolerance'].value[0]
                self._update_if_empty('Tolerance', value)

            if 'power_rating' in octo.specs.keys():
                value = octo.specs['power_rating'].value[0]
                suffix = octo.specs['power_rating'].metadata['unit']['symbol']
                self._update_if_empty('Power_Rating', Utils.eng_string(value, suffix=suffix))

            if 'case_package' in octo.specs.keys():
                value = octo.specs['case_package'].value[0]
                self._update_if_empty('Case_Style', value)
                self._update_if_empty('Footprint_Ref', 'R-{}'.format(value))

    def suppliers(self, octo: octomodels.Part):
        """ Populate supplier fields in the database dict and try to search for links """
        try:
            # Get the supplier names from the configuration store
            supplier_1 = self.config.get('odbt', 'db_supplier_1')
            supplier_2 = self.config.get('odbt', 'db_supplier_2')
        except Exception as e:
            print('Config error: {0}'.format(e))
            print('Please make sure your config file exists and has an API key')
            exit(1)
        else:
            supplier_1_index = self._find_seller(octo, supplier_1)
            supplier_2_index = self._find_seller(octo, supplier_2)

            # Populate data for first supplier
            self.dbmapping_new['Supplier_1'] = supplier_1
            self.dbmapping_new['ComponentLink1Description'] = '&{0!s} product page'.format(supplier_1)
            if supplier_1_index is not None and (self._empty('Supplier_Part_Number_1') or self._empty('ComponentLink1URL')):
                self.dbmapping_new['Supplier_Part_Number_1'] = octo.offers[supplier_1_index].sku
                self.dbmapping_new['ComponentLink1URL'] = self._fetch_supplier_link(octo.offers[supplier_1_index])

            # Populate data for second supplier
            self.dbmapping_new['Supplier_2'] = supplier_2
            self.dbmapping_new['ComponentLink2Description'] = '&{0!s} product page'.format(supplier_2)
            if supplier_2_index is not None and (self._empty('Supplier_Part_Number_2') or self._empty('ComponentLink2URL')):
                self.dbmapping_new['Supplier_Part_Number_2'] = octo.offers[supplier_2_index].sku
                self.dbmapping_new['ComponentLink2URL'] = self._fetch_supplier_link(octo.offers[supplier_2_index])

    def datasheet(self, octo: octomodels.Part, interactive=True):
        datasheet_url = None

        #Only run if we have no datasheet yet
        if self._empty('HelpURL'):
            # Only use PDF datasheets
            if octo.datasheets is not None and len(octo.datasheets) != 0:
                datasheets = [d for d in octo.datasheets if re.match('.*\.pdf$', d)]

            if octo.datasheets is not None and len(octo.datasheets) != 0:
                # Pick first datasheet if not running in interactive mode
                if interactive:
                    # Manually select datasheet and preview it in Chrome
                    is_fit = 'n'
                    while is_fit != 'y':
                        datasheet_url = shell.Prompt("Pick a datasheet to preview and use')", options=datasheets, numbered=True).prompt()
                        browser = webdriver.Chrome(executable_path=str(Path(os.path.dirname(__file__) + "/../../bin/chromedriver.exe")))
                        browser.get(datasheet_url)
                        is_fit = shell.Prompt("Is the datasheet ok?", options=['y', 'n'], default='y').prompt()
                        time.sleep(0.1)
                else:
                    datasheet_url = datasheets[0]
            else:
                # Ask for datasheet URL
                self.app.print('No datasheet found...')
                is_fit = 'n'
                while is_fit != 'y':
                    datasheet_url = shell.Prompt('Manually enter an URL:', default="break").prompt()
                    if re.match('.*\.pdf$', datasheet_url):
                        is_fit = 'y'
                    if datasheet_url == 'break':
                        datasheet_url = None
                        break

            # Download datasheet
            if datasheet_url is not None:
                try:
                    lib_path = Path(os.path.dirname(self.app.config.get('odbt', 'db_path')))
                except Exception as e:
                    print('Config error: {0}'.format(e))
                    print('Please make sure your config file exists and has a database path defined')
                    exit(1)
                else:
                    datasheet_path = Path(os.path.join(lib_path, 'Components', self.table, 'Datasheets'))

                    # Create datasheet path if it does not exists
                    if not datasheet_path.exists():
                        datasheet_path.mkdir(parents=True)

                    # Replace illegal filename characters
                    filename = self.dbmapping_new['Manufacturer_1'] + '_' + self.dbmapping_new['Manufacturer_Part_Number_1']
                    illegals = ('\\', '/', ':', '*', '?', '\'', '\"', '<', '>', '|', '.', ',', ' ')
                    for sym in illegals:
                        filename = filename.replace(sym, '_')

                    # Destination path for datasheet
                    datasheet_file = Path(os.path.join(datasheet_path, filename + '.pdf'))

                    # Fix 'HTTP Error 403' from https://stackoverflow.com/a/36663971
                    ua = UserAgent()
                    header = {'User-Agent': str(ua.chrome)}

                    self.app.print('Downloading pdf from {0} to {1}'.format(datasheet_url, datasheet_path))
                    try:
                        r = requests.get(datasheet_url, headers=header, allow_redirects=True)
                        open(datasheet_file, 'wb').write(r.content)
                    except Exception as e:
                        self.app.print('Download failed: {0}'.format(e))
                    else:
                        self.app.print('Download successfull')
                        self.dbmapping_new['HelpURL'] = str(datasheet_file)
                        self.datasheet_file = datasheet_file
            else:
                self.app.print('No datasheet found...')



