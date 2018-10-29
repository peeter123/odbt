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

    def _default(self):
        """Default action if no sub-command is passed."""

        self.app.args.print_help()

    @ex(
        help='List items from a specific table',

        # sub-command level arguments. ex: 'odbt command1 --foo bar'
        arguments=[
            ### add a sample foo option under subcommand namespace
            (['table'],
             {'help': 'The table where the item should be stored',
              'action': 'store'}),
        ],
    )
    def list(self):
        """List database table"""

        ### do something with arguments
        if self.app.pargs.table is not None:
            data = {'data': self.app.db.execute('select * from ' + self.app.pargs.table).fetchall()}
            self.app.render(data, 'table-list.jinja2')
        else:
            print('Please specify a table to list')
