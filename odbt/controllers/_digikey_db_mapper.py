from digikey import models as digimodels
from datetime import datetime
from selenium import webdriver
from cement import App, shell
from fake_useragent import UserAgent
from ._db_mapper import DBMapper
from ._utils import Utils
from google import google


class DigikeyDBMapper(DBMapper):
    def spec(self, dkp: digimodels.Part):
        """ Populate specification fields in the database dict """
        self.app.print('Filling specs ...')

        # Independent fields
        self._update_if_empty('Description', dkp.description_product)
        self._update_if_empty('Manufacturer_1', dkp.manufacturer.upper())
        self._update_if_empty('Manufacturer_Part_Number_1', dkp.mpn)
        self._update_if_empty('Designer', 'P. Oostewechel')
        self._update_if_empty('Creation_Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        # Optional fields
        self.dbmapping_new['Status'] = dkp.part_status \
            if dkp.part_status else self.dbmapping_original['Status']

        # Fields based on component type
        # if 'Aluminum Electrolytic Capacitors' in [c.name for c in self.categories]:
        #     self._update_if_empty('Library_Ref', 'Capacitor Polarized')
        #
        #     if 'dielectric_material' in dkp.specs.keys():
        #         value = dkp.specs['dielectric_material'].value[0]
        #         self._update_if_empty('Material_Type', value.upper())
        #
        # if 'Capacitors' in [c.name for c in self.categories]:
        #     self._update_if_empty('Library_Ref', 'Capacitor')
        #
        #     if 'capacitance' in dkp.specs.keys():
        #         value = dkp.specs['capacitance'].value[0]
        #         suffix = dkp.specs['capacitance'].metadata['unit']['symbol']
        #         self._update_if_empty('Value', Utils.eng_string(value, suffix=suffix))
        #
        #     if 'voltage_rating_dc' in dkp.specs.keys():
        #         value = dkp.specs['voltage_rating_dc'].value[0]
        #         suffix = dkp.specs['voltage_rating_dc'].metadata['unit']['symbol']
        #         self._update_if_empty('Voltage_Rating', Utils.eng_string(value, suffix=suffix))
        #
        #     if 'capacitance_tolerance' in dkp.specs.keys():
        #         value = dkp.specs['capacitance_tolerance'].value[0]
        #         self._update_if_empty('Tolerance', value)
        #
        #     if 'dielectric_characteristic' in dkp.specs.keys():
        #         value = dkp.specs['dielectric_characteristic'].value[0]
        #         self._update_if_empty('Material_Type', value.upper())
        #
        #     if 'case_package' in dkp.specs.keys():
        #         value = dkp.specs['case_package'].value[0]
        #         self._update_if_empty('Case_Style', value)
        #         self._update_if_empty('Footprint_Ref', 'C-{}'.format(value))
        #
        # if 'Resistors' in [c.name for c in self.categories]:
        #     self._update_if_empty('Library_Ref', 'Resistor')
        #
        #     if 'resistance' in dkp.specs.keys():
        #         value = dkp.specs['resistance'].value[0]
        #         suffix = dkp.specs['resistance'].metadata['unit']['symbol']
        #         self._update_if_empty('Value', Utils.eng_string(value, suffix=suffix))
        #
        #     if 'voltage_rating_dc' in dkp.specs.keys():
        #         value = dkp.specs['voltage_rating_dc'].value[0]
        #         suffix = dkp.specs['voltage_rating_dc'].metadata['unit']['symbol']
        #         self._update_if_empty('Voltage_Rating', Utils.eng_string(value, suffix=suffix))
        #
        #     if 'resistance_tolerance' in dkp.specs.keys():
        #         value = dkp.specs['resistance_tolerance'].value[0]
        #         self._update_if_empty('Tolerance', value)
        #
        #     if 'power_rating' in dkp.specs.keys():
        #         value = dkp.specs['power_rating'].value[0]
        #         suffix = dkp.specs['power_rating'].metadata['unit']['symbol']
        #         self._update_if_empty('Power_Rating', Utils.eng_string(value, suffix=suffix))
        #
        #     if 'case_package' in dkp.specs.keys():
        #         value = dkp.specs['case_package'].value[0]
        #         self._update_if_empty('Case_Style', value)
        #         self._update_if_empty('Footprint_Ref', 'R-{}'.format(value))

    def suppliers(self, dkp: digimodels.Part):
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
            # Populate data for first supplier
            if supplier_1 == 'Digi-Key':
                self.dbmapping_new['Supplier_1'] = supplier_1
                self.dbmapping_new['ComponentLink1Description'] = '&{0!s} product page'.format(supplier_1)
                if self._empty('Supplier_Part_Number_1') or self._empty('ComponentLink1URL'):
                    self.dbmapping_new['Supplier_Part_Number_1'] = dkp.digikey_pn
                    self.dbmapping_new['ComponentLink1URL'] = dkp.digikey_url

            # Populate data for second supplier
            if supplier_2 == 'Digi-Key':
                self.dbmapping_new['Supplier_2'] = supplier_2
                self.dbmapping_new['ComponentLink2Description'] = '&{0!s} product page'.format(supplier_2)
                if self._empty('Supplier_Part_Number_2') or self._empty('ComponentLink2URL'):
                    self.dbmapping_new['Supplier_Part_Number_2'] = dkp.digikey_pn
                    self.dbmapping_new['ComponentLink2URL'] = dkp.digikey_url

    def datasheet(self, dkp: digimodels.Part, interactive=True):
        datasheets = None

        #Only run if we have no datasheet yet
        if self._empty('HelpURL'):
            # Only use PDF datasheets
            if dkp.datasheet is not None:
                datasheets = [dkp.datasheet]

            self._datasheet(datasheets)
