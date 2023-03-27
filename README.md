# rivian-python-api - A python API for Rivian

## Sources

Based on information from https://github.com/kaedenbrinkman/rivian-api.

## State

* Have not yet tested actions (open frunk etc.)
* Polling impact on sleep not yet known
* No known way to get speed yet

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

### Vehicle State
```
bin/rivian_cli --state
```

### Vehicle State Polling
```
bin/rivian_cli --poll
```

### Trip planning
```
bin/rivian_cli --plan_trip 85,225,42.0772,-71.6303,42.1399,-71.5163
```

### Other commands
```
bin/rivian_cli --help
```

## CLI Notes
* Supports authentication with and without OTP (interactive terminal)
* Saves login information in a .pickle file to avoid login each time (login once, then run other commands)
