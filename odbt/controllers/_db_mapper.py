import os, time, re
import requests
from selenium.common.exceptions import WebDriverException
from tabulate import tabulate
from pathlib import Path
from octopart import models as octomodels
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from cement import App, shell
from fake_useragent import UserAgent
from ._utils import Utils
from search_engine_parser.core.engines.google import Search as GoogleSearch
from search_engine_parser.core.engines.duckduckgo import Search as DuckSearch
from urllib.parse import urlsplit, parse_qs

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


class DBMapper:
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

    def _webdriver(self):
        chrome_options = Options()
        chrome_options.add_argument('--silent')
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        if Path(self.app.config.get('odbt', 'browser_path')):
            chrome_options.binary_location = self.app.config.get('odbt', 'browser_path')
        return webdriver.Chrome(chrome_options=chrome_options,
                                executable_path=str(Path(os.path.dirname(__file__) + "/../../bin/chromedriver.exe")))

    def _replace_special_chars(self, text: str):
        specialharsDictionary = {u'Ü': 'U', u'ü': 'u'}
        umap = {ord(key): val for key, val in specialharsDictionary.items()}
        return text.translate(umap)

    def _search_supplier_data(self, supplier, url, mpn):
        info = {'url': None,
                'sku': None}

        dsearch = DuckSearch()

        if supplier == 'Farnell':
            self.app.print('Searching Farnell...')
            try:
                search_results = dsearch.search(f'Farnell {mpn} site:{url}')
            except Exception as e:
                return None

            if not search_results:
                return None

            results = [result for result in search_results]

            for i, val in enumerate(results):
                # params = parse_qs(urlsplit(val['links']).query)
                # results[i]['q_params'] = params
                self.app.print(f'{i} {val.get("links", None)}')

            self.app.print('Pick a result [number, or none to cancel]: ')
            choice_word = input()
            if choice_word.isdecimal():
                choice_index = int(choice_word)
                info['url'] = results[choice_index]['links'].strip('RL')
                info['sku'] = re.search('.*/(\d*)', info['url']).group(1)
                return info
        else:
            return None

    def _fetch_supplier_link(self, supplier):
        pass

    def _find_seller(self, octo: octomodels.Part, name: str):
        pass

    def _get_component_categories(self, octo: octomodels.Part):
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
        pass

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
        pass

    def _datasheet(self, datasheets, interactive=True):
        datasheet_url = None

        if datasheets is not None and len(datasheets) != 0:
            # Pick first datasheet if not running in interactive mode
            if interactive:
                # Manually select datasheet and preview it in Chrome
                is_fit = 'n'
                while is_fit != 'y':
                    datasheet_url = shell.Prompt("Pick a datasheet to preview and use ...", options=datasheets, numbered=True).prompt()
                    try:
                        browser = self._webdriver()
                        browser.get(datasheet_url)
                        count = 5
                        while count > 0:
                            self.app.print(f'Waiting for datasheet to load... {count} s remaining')
                            if '.pdf' in browser.current_url:
                                split_url = urlsplit(browser.current_url)
                                datasheet_url = f'{split_url.scheme}://{split_url.netloc}{split_url.path}'
                                break
                            time.sleep(1)
                            count -= 1
                    except WebDriverException as e:
                        pass
                    is_fit = shell.Prompt("Is the datasheet ok? (press m for manual url)", options=['y', 'n', 'm'], default='y').prompt()
                    if is_fit == 'm':
                        datasheet_url = shell.Prompt('Manually enter an URL:', default="break").prompt()
                        if re.match('.*\.pdf$', datasheet_url):
                            is_fit = 'y'
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

                filename = Utils.remove_umlaut(filename)

                # Destination path for datasheet
                datasheet_file = Path(os.path.join(datasheet_path, filename + '.pdf'))

                # Fix 'HTTP Error 403' from https://stackoverflow.com/a/36663971
                ua = UserAgent()
                header = {'User-Agent': str(ua.ie)}

                self.app.print('Downloading pdf from {0} to {1}'.format(datasheet_url, datasheet_file))
                try:
                    r = requests.get(datasheet_url, headers=header, allow_redirects=True, timeout=5)
                    r.raise_for_status()
                    if r.headers['content-type'] == 'application/pdf':
                        open(datasheet_file, 'wb').write(r.content)
                    else:
                        raise Exception('Response is not a PDF')
                except Exception as e:
                    self.app.print('Download failed: {0}'.format(e))
                else:
                    self.app.print('Download successfull')
                    self.dbmapping_new['HelpURL'] = str(datasheet_file)
                    self.datasheet_file = datasheet_file
        else:
            self.app.print('No datasheet found...')



