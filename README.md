# Use Octopart to update and add components to an Altium DBlib

## Installation

```
$ virtualenv --prompt '|> odbt <| ' env
$ pip install -r requirements.txt
$ setup.py develop
```

## Usage
ODBT is a CLI application which can be used from the command line.

### Requirements
You need to setup an Altium DBLib structure + database. Furthermore you request an Octopart API key.

The required directory structure is shown below:

```
Components\
    Capacitors\
        Datasheets\
        Capacitors.PcbLib
        Capacitors.SchLib
    ...
    Resistors\
Database.mdb
Database.DbLib
```

### Configuration
 Before you can use the application you need to setup the config file in the config directory. 
 You can copy ``odbt.yml.samle`` to ``odbt.yml`` and edit the file to match your setup.
 
- You will need to obtain an *API key* from [Octopart](https://octopart.com/api/register) and need to enter it 
in the configuration under ``odbt -> octopart_api_key``.
- You will need to enter a path to the database given in the section above under ``odbt -> db_path``
as ``C:\Path\To\Directory\Structure\Database.mdb``

### Running
Activate your virtual environment (See development section for creating one):
```
$ source env/bin/activate
```

And run the application:
```
### run odbt cli application
$ odbt --help

usage: odbt [-h] [-d] [-q] [-v] {table,item,config} ...

Use Octopart to update and add componenta to an Altium DBlib

optional arguments:
  -h, --help           show this help message and exit
  -d, --debug          full application debug mode
  -q, --quiet          suppress all console output
  -v, --version        show program's version number and exit

sub-commands:
  {table,item,config}
    table              table controller
    item               item controller
    config             config controller

Usage: odbt [command]

```

## Development

This project includes a number of helpers in the `Makefile` to streamline common development tasks.

### Environment Setup

The following demonstrates setting up and working with a development environment:

```
### create a virtualenv for development
$ make virtualenv
$ source env/bin/activate

### run odbt cli application
$ odbt --help

### run pytest / coverage
$ make test
```

### TODO
- [ ] Script to create a default empty database including file paths
- [ ] Handle thrown errors
- [ ] Functional testing