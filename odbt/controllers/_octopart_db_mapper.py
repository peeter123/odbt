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
from ._db_mapper import DBMapper
from google import google


class OctopartDBMapper(DBMapper):

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
            result = google.search('{} - {} site:{}'.format('Digi-Key', supplier.sku, 'digikey.com'))
            if len(result):
                return result[0].link
            else:
                return None
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
        datasheets = None

        #Only run if we have no datasheet yet
        if self._empty('HelpURL'):
            # Filter for PDF datasheets
            if octo.datasheets is not None and len(octo.datasheets) != 0:
                datasheets = [d for d in octo.datasheets if re.match('.*\.pdf$', d)]

            self._datasheet(datasheets)
