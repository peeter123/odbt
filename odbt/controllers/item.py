import octopart
from tabulate import tabulate
from ._octopart_db_mapper import OctopartDBMapper
from cement import Controller, ex, shell

class Item(Controller):
    class Meta:
        label = 'item'
        stacked_on = 'base'
        stacked_type = 'nested'

        # text displayed at the top of --help output
        description = 'Use Octopart to update and add componenta to an Altium DBlib'

        # text displayed at the bottom of --help output
        epilog = 'Usage: odbt item --table Capacitors add'

        # controller level arguments. ex: 'odbt --version'
        arguments = [
            ### add a version banner
            ( [ '-t', '--table' ],
              { 'action'  : 'version'} ),
        ]

    def _default(self):
        """Default action if no sub-command is passed."""

        self.app.args.print_help()

    def _check_table_valid(self):
        # Get the table list from the database and strip lookup tables
        table_list = list(self.app.db.tables(tableType='TABLE'))
        table_list = [x for x in table_list if 'lookup_' not in x.table_name]

        if self.app.pargs.table is None or self.app.pargs.table not in [x.table_name for x in table_list]:
            self.app.print('Please provide the correct table name')
            self.app.exit_code = 1
            self.app.close()


    @ex(
        help='Add an item to the database in a specific table',

        # sub-command level arguments. ex: 'odbt command1 --foo bar'
        arguments=[
            ( ['query'],
              {'help': 'search query for Octopart',
              'action': 'store' } ),
            ( [ '-t', '--table' ],
              { 'help' : 'The table where the item should be stored',
                'action'  : 'store',
                'dest' : 'table' } ),
        ],
    )
    def add(self):
        """ Search octopart with query and interactively add result"""
        self._check_table_valid()
        odbm = OctopartDBMapper(self.app, self.app.pargs.table)

        if self.app.pargs.query is not None:
            query = self.app.pargs.query
            self.app.print("Searching for: " + query)

            # Query Octopart with a simple search
            search = octopart.search(query, limit=10, include_short_description=True)
            results = search.parts

            # List results and pick one to add to the database
            if len(results) == 0:
                self.app.print('No results found')
                self.app.exit_code = 1
                self.app.close()
            else:
                self.app.render({'results': results}, 'search-list-result.jinja2')
                self.app.print('Pick a [number]: ')
                choice_word = input()
                if choice_word.isdecimal():
                    choice_index = int(choice_word)
                    if 0 <= choice_index <= 9:
                        self.app.print('Chosen: {} {} (UID {})'.format(
                            results[choice_index].manufacturer,
                            results[choice_index].mpn,
                            results[choice_index].uid))
                        uid = results[choice_index].uid
                    else:
                        self.app.print('No such variant')
                        self.app.exit_code = 1
                        self.app.close()
                else:
                    # No number given, exit application
                    self.app.exit_code = 1
                    self.app.close()

            # Query Octopart with an uid to get the single part which was requested
            part = octopart.part(uid, includes=['datasheets', 'short_description', 'description', 'specs'])
            odbm.spec(part)
            odbm.suppliers(part)
            odbm.datasheet(part)
            odbm.insert_item_database()
            pass
        else:
            self._default()

    @ex(
        help='Update an item in a specific table',

        # sub-command level arguments. ex: 'odbt command1 --foo bar'
        arguments=[
             (['sql_id'],
              {'help': 'item id to update',
               'action': 'store'}),
             (['-t', '--table'],
              {'help': 'The table where the item should be stored',
               'action': 'store',
               'dest': 'table'}),
        ],
    )
    def update(self):
        """ Search octopart with query and interactively add result"""
        self._check_table_valid()
        odbm = OctopartDBMapper(self.app, self.app.pargs.table)

        if self.app.pargs.sql_id is not None:
            sql_id = self.app.pargs.sql_id
            self.app.print("Updating: " + sql_id)

            # Store original data
            odbm.populate_original_data(sql_id=sql_id)

            # Query Octopart with a simple search
            search_string = odbm.dbmapping_original['Manufacturer_1'] + ' ' + \
                            odbm.dbmapping_original['Manufacturer_Part_Number_1']
            search = octopart.search(search_string, limit=10, include_short_description=True)
            results = search.parts

            # List results and pick one to add to the database
            if len(results) == 0:
                self.app.print('No results found')
                self.app.exit_code = 1
                self.app.close()
            else:
                self.app.render({'results': results}, 'search-list-result.jinja2')
                self.app.print('Pick a [number]: ')
                choice_word = input()
                if choice_word.isdecimal():
                    choice_index = int(choice_word)
                    if 0 <= choice_index <= 9:
                        self.app.print('Chosen: {} {} (UID {})'.format(
                            results[choice_index].manufacturer,
                            results[choice_index].mpn,
                            results[choice_index].uid))
                        uid = results[choice_index].uid
                    else:
                        self.app.print('No such variant')
                        self.app.exit_code = 1
                        self.app.close()
                else:
                    # No number given, exit application
                    self.app.exit_code = 1
                    self.app.close()

            # Query Octopart with an uid to get the single part which was requested
            part = octopart.part(uid, includes=['datasheets', 'short_description', 'description', 'specs', 'category_uids'])
            odbm.spec(part)
            odbm.suppliers(part)
            odbm.datasheet(part)
            odbm.update_item_database()
            pass
        else:
            self._default()



    @ex(
        help='search Octopart and list results',
        arguments=[
            ( ['query'],
              {'help': 'search query for Octopart',
              'action': 'store' } ),
        ],
    )
    def search(self):
        """ Search octopart with query and list results"""

        if self.app.pargs.query is not None:
            query = self.app.pargs.query
            self.app.print("Searching for: " + query)

            # Query Octopart with a simple search
            search = octopart.search(query, limit=10, include_descriptions=True)
            results = search.parts

            if len(results) == 0:
                self.app.print('No results found')
                self.app.exit_code = 1
                self.app.close()
            else:
                self.app.render({'results': results}, 'search-list-result.jinja2')
