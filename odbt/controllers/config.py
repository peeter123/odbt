import yaml
from cement import Controller, ex

class Config(Controller):
    class Meta:
        label = 'config'
        stacked_on = 'base'
        stacked_type = 'nested'

        # text displayed at the top of --help output
        description = 'Use Octopart to update and add componenta to an Altium DBlib'

        # text displayed at the bottom of --help output
        epilog = 'Usage: odbt config show'

    def _pretty(self, d, indent=0):
        for key, value in d.items():
            if isinstance(value, dict):
                self.app.print('\t' * indent + str(key))
                self._pretty(value, indent + 1)
            else:
                self.app.print('\t' * indent + str(key) + ' : ' + str(value))

    def _default(self):
        """Default action if no sub-command is passed."""

        self.app.args.print_help()

    @ex(
        help='Show global options',
    )
    def show(self):
        """Print current configuration."""
        self.app.print('Current configuration:')
        dict = self.app.config.get_dict()
        self._pretty(dict)
