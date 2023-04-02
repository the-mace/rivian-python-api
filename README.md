# rivian-python-api - A python API for Rivian

## Sources

Based on information from https://github.com/kaedenbrinkman/rivian-api.

## State of development

### Polling
After a number of tests, polling appears not to impact the sleep state of the vehicle unlike
the behavior of other vendors.

The CLI has a polling option (--poll) which you can experiment with yourself, but leaving the 
vehicle alone from a polling perspective or constantly hitting it via the API appears to have no impact 
on when it goes to sleep.

Polling was also possible during a software update with no disruption to the update and it's possible
to monitor software update progress that way.

### Actions
I have not yet tested/completed actions like "Open Frunk" (see `--command` option in CLI)
Rivian has greatly limited the utility of this for third parties because:

1. They limit you to 2 phones per vehicle
2. Actions are cryptographically signed by the registered phones and validated
3. You can't move/use your signature from your phone, so you need to register a new "phone" (the API) to do actions, thus giving up one of the 2 precious phone slots. 
4. With more than one driver this is very limiting

So while technically possible to remotely control the vehicle via API, 
the utility is greatly limited due to Rivian's approach.

Note you can definitely argue that their approach is more secure than that of other vendors, but
it also limits the ability to extend the owners experience through third party products.

### Missing & Unknown
1. There does not appear to be an API call that returns `speed` for the vehicle. With GPS location and polling and math you can figure it out with haversine etc. type approaches. Example in the CLI

## Dependencies

Python 3
pip

## Setup

### For API
None

### For CLI
`pip install -r requirements.txt`

*Note: For any actions with the CLI you'll need to login, see login information below.*

## CLI Commands

The CLI is meant to be an example of API usage as well as to provide some 
useful outputs to see what your vehicle is reporting. The CLI is not meant to be
a full-blown application.

For simplicity, the CLI will "guess" at which vehicle it should be talking to for responses. 
You can specify a specific vehicle (and avoid some extra API calls) using `--vehicle_id`

There's intentionally no multi-vehicle support other than the above, the CLI is a limited
test bed / example of API use.

In most cases CLI output shows a subset of overall response data. Use `--verbose` to see
all the infor returned by the API for the given call.

### Login
```
bin/rivian_cli --login
```

Login, will interactively prompt for MFA if needed.
Expects `RIVIAN_USERNAME` and `RIVIAN_PASSWORD` in shell environment.

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
bin/rivian_cli --plan_trip 85,225,40.5112,-89.0559,39.9310,-104.9530
Plan trip will create a basic visualization of the route and charge stops. MAPBOX_API_KEY needs to be set in .env
```

### Other commands
```
bin/rivian_cli --help
```

## CLI Notes
* Supports authentication with and without OTP (interactive terminal)
* Saves login information in a .pickle file to avoid login each time (login once, then run other commands)
