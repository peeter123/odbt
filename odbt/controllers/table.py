from cement import Controller, ex


class Table(Controller):
    class Meta:
        label = 'table'
        stacked_on = 'base'
        stacked_type = 'nested'

        # text displayed at the top of --help output
        description = 'Use Octopart to update and add componenta to an Altium DBlib'

        # text displayed at the bottom of --help output
        epilog = 'Usage: odbt table --foo bar'

        # controller level arguments. ex: 'odbt --version'
        arguments = [
            ### add a version banner
            (['-t', '--table'],
             {'help': 'The table where the item should be stored',
              'action': 'store',
              'dest': 'table'}),
            (['-y', '--non-interactive'],
             {'help': 'Run in non-interactive mode',
              'action': 'store_true',
              'dest': 'non_interactive'}),
        ]

    def _check_table_valid(self):
        # Get the table list from the database and strip lookup tables
        table_list = list(self.app.db.tables(tableType='TABLE'))
        table_list = [x for x in table_list if 'lookup_' not in x.table_name]

        if self.app.pargs.table is None or self.app.pargs.table not in [x.table_name for x in table_list]:
            self.app.print('Please provide the correct table name')
            self.app.exit_code = 1
            self.app.close()

    def _default(self):
        """Default action if no sub-command is passed."""

        self.app.args.print_help()

    @ex(
        help='List items from a specific table',

        # sub-command level arguments. ex: 'odbt command1 --foo bar'
        arguments=[],
    )
    def list(self):
        """List database table"""

        ### do something with arguments
        if self.app.pargs.table is not None:
            self._check_table_valid()
            data = {'data': self.app.db.execute('select * from ' + self.app.pargs.table).fetchall()}
            self.app.render(data, 'table-list.jinja2')
        else:
            print('Please specify a table to list')
