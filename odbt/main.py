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

    db_file = app.config.get('odbt', 'db_path')

    # Ensure the database file is valid
    db_file = Path(db_file)
    if not os.path.isfile(db_file):
        app.log.error("Database not found")
        exit(1)

    app.log.info('Access database file is: %s' % db_file)

    conn_str = (
        r'DRIVER={' + connector[0] + '};'
        r'DBQ=' + str(db_file)
    )
    cnxn = pyodbc.connect(conn_str)
    crsr = cnxn.cursor()
    # for table_info in crsr.tables(tableType='TABLE'):
    #     logging.INFO(table_info.table_name)

    app.extend('db', crsr)

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
        ]

        hooks = [
            ('post_setup', extend_access_db),
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

        debug = True

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
