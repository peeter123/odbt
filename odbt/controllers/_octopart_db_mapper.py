import os, time, re
import requests
from tabulate import tabulate
from pathlib import Path
from octopart import models as octomodels
from datetime import datetime
from selenium import webdriver
from cement import App, shell
from fake_useragent import UserAgent

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

        # Create dict from columns to map data on the database and store original data
        self.dbmapping_original = {}
        self.dbmapping_new = {}
        for col in common_col_names:
            self.dbmapping_original[col.replace(' ', '_')] = None
            self.dbmapping_new[col.replace(' ', '_')] = None


    def _fetch_supplier_link(self, supplier: octomodels.PartOffer):
        options = webdriver.ChromeOptions()
        # options.add_argument('headless')
        # options.add_argument('disable-gpu')

        if supplier.seller == 'Farnell':
            browser = webdriver.Chrome(options=options,
                                       executable_path=str(
                                           Path(os.path.dirname(__file__) + "/../../bin/chromedriver.exe")))
            url = 'https://nl.farnell.com/{0}'.format(supplier.sku)
            browser.get(url)
            while True:
                if 'farnell.com/{0!s}'.format(supplier.sku) not in browser.current_url:
                    url = browser.current_url.split('?')[0]
                    browser.quit()
                    return url
                time.sleep(1)
        # Fallback to Octopart redirect URL
        else:
            return supplier.product_url

    def _find_seller(self, octo: octomodels.Part, name: str):
        for index, offer in enumerate(octo.offers, 0):
            if offer.seller == name:
                return index

        return None

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

    def update_item_database(self):
        # Preview data
        headers = ['Key', 'Original Data', 'New Data']
        table = []
        for k, v in self.dbmapping_original.items():
            table.append((k, v, self.dbmapping_new[k]))

        self.app.print(tabulate(table, headers=headers))
        accept = shell.Prompt("Execute component add?", options=['y', 'n']).prompt()

        dbmapping_new = self._purge_empty_keys(self.dbmapping_new)

        # Get possible ID
        sql_id = dbmapping_new['dict'].pop('ID', None)

        if accept == 'y':
            # Create query from data list
            kv_pairs = ','.join(['[{0}]=\'{1}\''.format(str(k.replace('_', ' ')),
                                                        str(v)) for k, v in dbmapping_new['dict'].items()])
            query = 'UPDATE {0} SET {1} WHERE ID={2}'.format(self.table, kv_pairs, sql_id)
            self.app.db.execute(query)
            self.app.db.commit()
            self.app.print("Updating component in database")
        else:
            # Cleanup
            self.app.print("No update, cleanup...")
            if self.dbmapping_original['HelpURL'] is None:
                self.app.print("Remove downloaded datasheet")
                self.datasheet_file.unlink()

    def insert_item_database(self):
        dbmapping_new = self._purge_empty_keys(self.dbmapping_new)

        # Preview data
        self.app.print(tabulate([(k, v) for k, v in dbmapping_new['dict'].items()]))
        accept = shell.Prompt("Execute component add?", options=['y', 'n']).prompt()

        if accept == 'y':
            # Create query from data list
            query = 'INSERT INTO {0} ([{1}]) VALUES (\'{2}\')'.format(self.table,
                                                                      '], ['.join(dbmapping_new['keys']),
                                                                      '\', \''.join(dbmapping_new['values']))
            self.app.db.execute(query)
            self.app.db.commit()
            self.app.print("Adding component to database")
        else:
            # Cleanup
            self.app.print("No add, cleanup...")
            self.app.print("Remove downloaded datasheet")
            self.datasheet_file.unlink()

    def populate_original_data(self, sql_id):
        query = 'SELECT * FROM {0} WHERE ID={1}'.format(self.table, sql_id)
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
        print('Filling specs ...')

        # Independent fields
        self.dbmapping_new['Description'] = octo.short_description
        self.dbmapping_new['Manufacturer_1'] = octo.manufacturer.upper()
        self.dbmapping_new['Manufacturer_Part_Number_1'] = octo.mpn
        self.dbmapping_new['Designer'] = 'P. Oostewechel'
        self.dbmapping_new['Creation_Date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

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
            if supplier_1_index is not None:
                self.dbmapping_new['Supplier_Part_Number_1'] = octo.offers[supplier_1_index].sku
                self.dbmapping_new['ComponentLink1URL'] = self._fetch_supplier_link(octo.offers[supplier_1_index])

            # Populate data for second supplier
            self.dbmapping_new['Supplier_2'] = supplier_2
            self.dbmapping_new['ComponentLink2Description'] = '&{0!s} product page'.format(supplier_2)
            if supplier_2_index is not None:
                self.dbmapping_new['Supplier_Part_Number_2'] = octo.offers[supplier_2_index].sku
                self.dbmapping_new['ComponentLink2URL'] = self._fetch_supplier_link(octo.offers[supplier_2_index])

    def datasheet(self, octo: octomodels.Part):
        if octo.datasheets is not None and len(octo.datasheets) != 0:
            # Only use PDF datasheets
            datasheets = [d for d in octo.datasheets if re.match('.*\.pdf$', d)]

            # Manually select datasheet and preview it in Chrome
            is_fit = 'n'
            datasheet_url = None
            while is_fit != 'y':
                datasheet_url = shell.Prompt("Pick a datasheet to preview and use')", options=datasheets, numbered=True).prompt()
                browser = webdriver.Chrome(executable_path=str(Path(os.path.dirname(__file__) + "/../../bin/chromedriver.exe")))
                browser.get(datasheet_url)
                is_fit = shell.Prompt("Is the datasheet ok?", options=['y', 'n']).prompt()
                time.sleep(0.1)

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



