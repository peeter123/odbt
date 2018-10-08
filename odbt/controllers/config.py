from cement import Controller, ex

class Config(Controller):
    class Meta:
        label = 'config'
        stacked_on = 'base'
        stacked_type = 'nested'

        # text displayed at the top of --help output
        description = 'Use Octopart to update and add componenta to an Altium DBlib'

        # text displayed at the bottom of --help output
        epilog = 'Usage: odbt config --foo bar'

    def _default(self):
        """Default action if no sub-command is passed."""

        self.app.args.print_help()


    @ex(
        help='Get and set global options',

        # sub-command level arguments. ex: 'odbt command1 --foo bar'
        arguments=[
            ### add a sample foo option under subcommand namespace
            ( [ '-t', '--table' ],
              { 'help' : 'The table where the item should be stored',
                'action'  : 'store',
                'dest' : 'foo' } ),
        ],
    )
    def get(self):
        """Example sub-command."""

        data = {
            'foo' : 'bar',
        }

        ### do something with arguments
        if self.app.pargs.foo is not None:
            data['foo'] = self.app.pargs.foo

        self.app.render(data, 'command1.jinja2')

    @ex(
        help='Get and set global options',

        # sub-command level arguments. ex: 'odbt command1 --foo bar'
        arguments=[
            ### add a sample foo option under subcommand namespace
            ( [ '-t', '--table' ],
              { 'help' : 'The table where the item should be stored',
                'action'  : 'store',
                'dest' : 'foo' } ),
        ],
    )
    def set(self):
        """Example sub-command."""

        data = {
            'foo' : 'bar',
        }

        ### do something with arguments
        if self.app.pargs.foo is not None:
            data['foo'] = self.app.pargs.foo

        self.app.render(data, 'command1.jinja2')

    def list(self):
        """List database table"""

        data = {
            'foo' : 'bar',
        }

        ### do something with arguments
        if self.app.pargs.foo is not None:
            data['foo'] = self.app.pargs.foo

        self.app.render(data, 'command1.jinja2')
