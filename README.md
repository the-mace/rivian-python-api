# rivian-python-api - A python API for Rivian

## Sources

Based on information from https://github.com/kaedenbrinkman/rivian-api.

## State

Pre-delivery commands, have not yet been able to test vehicle commands.

## Dependencies

Python 3

## Setup

None

## Run Commands

### Login
```
python rivian_cli.py --login
```

### Vehicle Orders
```
python rivian_cli.py --vehicle_orders
```

### Vehicle Orders hiding PII
```
python rivian_cli.py --vehicle_orders --privacy
```

### Vehicle Orders with raw dumps
```
python rivian_cli.py --vehicle_orders --verbose
```

### Other commands
```
python rivian_cli.py --help
```

## CLI Notes
* Supports authentication with and without OTP (interactive terminal)
* Saves login information in a .pickle file to avoid login each time (login once, then run other commands)
