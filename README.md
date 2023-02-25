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
bin/rivian_cli --login
```

### Vehicle Orders
```
bin/rivian_cli --vehicle_orders
```

### Vehicle Orders hiding PII
```
bin/rivian_cli --vehicle_orders --privacy
```

### Vehicle Orders with raw dumps
```
bin/rivian_cli --vehicle_orders --verbose
```

### Other commands
```
bin/rivian_cli --help
```

## CLI Notes
* Supports authentication with and without OTP (interactive terminal)
* Saves login information in a .pickle file to avoid login each time (login once, then run other commands)
