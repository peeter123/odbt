import re
from cement import Controller, ex

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

        # Get the table list from the database
        table_list = list(self.app.db.tables(tableType='TABLE'))
        if self.app.pargs.table is None:
            self.app.print('Please provide the table to add the component to')
            self.app.exit_code = 1
            self.app.close()

        if self.app.pargs.query is not None:
            query = self.app.pargs.query
            self.app.print("Searching for: " + query)

            # Query Octopart with a simple search
            search = self.app.octo.search(query, limit=10)
            results = search['results']

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
                            results[choice_index]['item']['brand']['name'],
                            results[choice_index]['item']['mpn'],
                            results[choice_index]['item']['uid']))
                        uid = results[choice_index]['item']['uid']
                    else:
                        self.app.print('No such variant')
                        self.app.exit_code = 1
                        self.app.close()
                else:
                    # No number given, exit application
                    self.app.exit_code = 1
                    self.app.close()

            # Query Octopart with an uid to get the single part which was requested
            search = self.app.octo.part(uid, includes=['datasheets', 'short_description', 'description', 'specs'])

    def update(self):
        """Example sub-command."""

        data = {
            'foo' : 'bar',
        }

        ### do something with arguments
        if self.app.pargs.foo is not None:
            data['foo'] = self.app.pargs.foo

        self.app.render(data, 'command1.jinja2')

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
            search = self.app.octo.search(query, limit=10)
            results = search['results']

            if len(results) == 0:
                self.app.print('No results found')
                self.app.exit_code = 1
                self.app.close()
            else:
                self.app.render({'results': results}, 'search-list-result.jinja2')
