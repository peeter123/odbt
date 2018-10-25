import pyodbc
import octopart
import os
from pathlib import Path
from cement import App, TestApp, init_defaults
from cement.core.exc import CaughtSignal
from .core.exc import odbtError
from .controllers.base import Base
from .controllers.config import Config
from .controllers.item import Item
from .controllers.table import Table

# configuration defaults
CONFIG = init_defaults('odbt')


def extend_access_db(app):
    # Check if MS Access DB connector is installed
    connector = [x for x in pyodbc.drivers() if x.startswith('Microsoft Access Driver')]

    if len(connector) == 0:
        app.log.error("MS Database connector not installed, please install it before using this application")
        exit(1)

    try:
        db_file = app.config.get('odbt', 'db_path')
    except Exception as e:
        print('Config error: {0}'.format(e))
        print('Please make sure your config file exists and has a database path defined')
        exit(1)
    else:
        # Ensure the database file is valid
        db_file = Path(db_file)
        if not os.path.isfile(db_file):
            print("Database not found")
            exit(1)

        app.log.debug('Access database file is: %s' % db_file)

        conn_str = (
            r'DRIVER={' + connector[0] + '};'
            r'DBQ=' + str(db_file)
        )
        cnxn = pyodbc.connect(conn_str)
        crsr = cnxn.cursor()
        app.extend('db', crsr)


def extend_octopart_api(app):
    try:
        # Get the API key from the configuration store
        api_key = app.config.get('odbt', 'octopart_api_key')
    except Exception as e:
        print('Config error: {0}'.format(e))
        print('Please make sure your config file exists and has an API key')
        exit(1)
    else:
        try:
            os.environ['OCTOPART_API_KEY'] = api_key
        except ValueError as e:
            print(e)
            exit(1)

class Odbt(App):
    """Octopart DBlib Tools primary application."""

    class Meta:
        label = 'odbt'

        # configuration defaults
        config_defaults = CONFIG

        # call sys.exit() on close
        close_on_exit = True

        # load additional framework extensions
        extensions = [
            'yaml',
            'json',
            'colorlog',
            'jinja2',
            'print',
        ]

        hooks = [
            ('post_setup', extend_access_db),
            ('post_setup', extend_octopart_api),
        ]

        # configuration handler
        config_handler = 'yaml'

        # configuration file suffix
        config_file_suffix = '.yml'

        # add extra configuration file path
        config_files = [
            str(Path(os.path.dirname(__file__) + "/.." + "/config/odbt.yml"))
        ]

        # set the log handler
        log_handler = 'colorlog'

        # set the output handler
        output_handler = 'jinja2'

        # register handlers
        handlers = [
            Base,
            Config,
            Item,
            Table
        ]

        exit_on_close = True

class odbtTest(TestApp, Odbt):
    """A sub-class of odbt that is better suited for testing."""

    class Meta:
        label = 'odbt'


def main():
    with Odbt() as app:
        try:
            app.run()

        except AssertionError as e:
            print('AssertionError > %s' % e.args[0])
            app.exit_code = 1

            if app.debug is True:
                import traceback
                traceback.print_exc()

        except odbtError as e:
            print('odbtError > %s' % e.args[0])
            app.exit_code = 1

            if app.debug is True:
                import traceback
                traceback.print_exc()

        except CaughtSignal as e:
            # Default Cement signals are SIGINT and SIGTERM, exit 0 (non-error)
            print('\n%s' % e)
            app.exit_code = 0


if __name__ == '__main__':
    main()
