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
            ### add a sample foo option under subcommand namespace
            ( [ '-t', '--table' ],
              { 'help' : 'The table where the item should be stored',
                'action'  : 'store',
                'dest' : 'foo' } ),
        ],
    )
    def add(self):
        """Example sub-command."""

        data = {
            'foo' : 'bar',
        }

        ### do something with arguments
        if self.app.pargs.foo is not None:
            data['foo'] = self.app.pargs.foo

        self.app.render(data, 'command1.jinja2')

    def update(self):
        """Example sub-command."""

        data = {
            'foo' : 'bar',
        }

        ### do something with arguments
        if self.app.pargs.foo is not None:
            data['foo'] = self.app.pargs.foo

        self.app.render(data, 'command1.jinja2')

    def search(self):
        """ Search table with query and list results"""

        data = {
            'foo' : 'bar',
        }

        ### do something with arguments
        if self.app.pargs.foo is not None:
            data['foo'] = self.app.pargs.foo

        self.app.render(data, 'command1.jinja2')
