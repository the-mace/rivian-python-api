#!/usr/bin/env python
# encoding: utf-8

import os
import argparse
from rivian_api import *
import pickle
from dateutil.parser import parse
from dateutil import tz
import time

POLL_FREQUENCY = 10

PICKLE_FILE = 'rivian_auth.pickle'


def save_state(rivian):
    state = {
        "_access_token": rivian._access_token,
        "_refresh_token": rivian._refresh_token,
        "_user_session_token": rivian._user_session_token,
    }
    with open(PICKLE_FILE, 'wb') as f:
        pickle.dump(state, f)


def restore_state(rivian):
    rivian.create_csrf_token()
    if os.path.exists(PICKLE_FILE):
        with open(PICKLE_FILE, 'rb') as f:
            obj = pickle.load(f)
        rivian._access_token = obj['_access_token']
        rivian._refresh_token = obj['_refresh_token']
        rivian._user_session_token = obj['_user_session_token']
    else:
        raise Exception("Please log in first")


def get_rivian_object():
    rivian = Rivian()
    restore_state(rivian)
    return rivian


def login(verbose):
    rivian = Rivian()
    try:
        rivian.login(os.getenv('RIVIAN_USERNAME'), os.getenv('RIVIAN_PASSWORD'))
    except Exception:
        print("Authentication failed, check RIVIAN_USERNAME and RIVIAN_PASSWORD")
        return

    if rivian.otp_needed:
        otpCode = input('Enter OTP: ')
        try:
            rivian.login_with_otp(username=os.getenv('RIVIAN_USERNAME'), otpCode=otpCode)
        except Exception:
            print("Authentication failed, OTP mismatch")
            return

    print("Login successful")
    save_state(rivian)
    return


def user_information(verbose):
    rivian = get_rivian_object()
    response = rivian.get_user_information()
    response_json = response.json()
    if verbose:
        print(f"user_information:\n{response_json}")
    return response_json['data']['currentUser']


def vehicle_orders(verbose):
    rivian = get_rivian_object()
    response = rivian.vehicle_orders()
    response_json = response.json()
    if verbose:
        print(f"orders:\n{response_json}")
    orders = []
    for order in response_json['data']['orders']['data']:
        orders.append({
            'id': order['id'],
            'orderDate': order['orderDate'],
            'state': order['state'],
            'configurationStatus': order['configurationStatus'],
            'fulfillmentSummaryStatus': order['fulfillmentSummaryStatus'],
            'items': [i['sku'] for i in order['items']],
            'isConsumerFlowComplete': order['consumerStatuses']['isConsumerFlowComplete'],
        })
    return orders


def order_details(order_id, verbose):
    rivian = get_rivian_object()
    response = rivian.order(order_id=order_id)
    response_json = response.json()
    if verbose:
        print(f"order_details:\n{response_json}")
    data = {
        'vehicleId': response_json['data']['order']['vehicle']['vehicleId'],
        'vin': response_json['data']['order']['vehicle']['vin'],
        'modelYear': response_json['data']['order']['vehicle']['modelYear'],
        'make': response_json['data']['order']['vehicle']['make'],
        'model': response_json['data']['order']['vehicle']['model'],
    }
    for i in response_json['data']['order']['items']:
        for c in i['configuration']['options']:
            data[c['groupName']] = c['optionName']
    return data


def retail_orders(verbose):
    rivian = get_rivian_object()
    response = rivian.retail_orders()
    response_json = response.json()
    if verbose:
        print(f"retail_orders:\n{response_json}")
    orders = []
    for order in response_json['data']['searchOrders']['data']:
        orders.append({
            'id': order['id'],
            'orderDate': order['orderDate'],
            'state': order['state'],
            'fulfillmentSummaryStatus': order['fulfillmentSummaryStatus'],
            'items': [item['title'] for item in order['items']]
        })
    return orders


def get_order(order_id, verbose):
    rivian = get_rivian_object()
    response = rivian.get_order(order_id=order_id)
    response_json = response.json()
    if verbose:
        print(f"get_order:\n{response_json}")
    order = {}
    order['orderDate'] = response_json['data']['order']['orderDate']
    return order


def payment_methods(verbose):
    rivian = get_rivian_object()
    response = rivian.payment_methods()
    response_json = response.json()
    if verbose:
        print(f"payment_methods:\n{response_json}")
    pmt = []
    for p in response_json['data']['paymentMethods']:
        pmt.append({
            'type': p['type'],
            'default': p['default'],
            'card': p['card'] if 'card' in p else None,
        })
    return pmt


def check_by_rivian_id(verbose):
    rivian = get_rivian_object()
    response = rivian.check_by_rivian_id()
    response_json = response.json()
    if verbose:
        print(f"check_by_rivian_id:\n{response_json}")
    data = {'Chargepoint checkByRivianId': response_json['data']['chargepoint']['checkByRivianId']}
    return data


def get_linked_email_for_rivian_id(verbose):
    rivian = get_rivian_object()
    response = rivian.get_linked_email_for_rivian_id()
    response_json = response.json()
    if verbose:
        print(f"get_linked_email_for_rivian_id:\n{response_json}")
    data = {
        'Chargepoint linked email':
            response_json['data']['chargepoint']['getLinkedEmailForRivianId']['email']
    }
    return data

def get_parameter_store_values(verbose):
    rivian = get_rivian_object()
    response = rivian.get_parameter_store_values()
    response_json = response.json()
    if verbose:
        print(f"get_parameter_store_values:\n{response_json}")


def get_vehicle(vehicle_id, verbose):
    rivian = get_rivian_object()
    response = rivian.get_vehicle(vehicle_id=vehicle_id)
    response_json = response.json()
    if verbose:
        print(f"get_vehicle:\n{response_json}")
    data = []
    for u in response_json['data']['getVehicle']['invitedUsers']:
        if u['__typename'] != 'ProvisionedUser':
            continue
        ud = {
            'firstName': u['firstName'],
            'lastName': u['lastName'],
            'email': u['email'],
            'roles': ', '.join(u['roles']),
            'devices': [],
        }
        for d in u['devices']:
            ud['devices'].append({
                "deviceName": d["deviceName"],
                "isPaired": d["isPaired"],
                "isEnabled": d["isEnabled"],
            })
        data.append(ud)
    return data


def get_vehicle_state(vehicle_id, verbose, minimal=False):
    rivian = get_rivian_object()
    try:
        response = rivian.get_vehicle_state(vehicle_id=vehicle_id)
    except Exception as e:
        _, _, message, _, _ = e.args
        print(f"{message['errors'][0]['message']}")
        return None
    response_json = response.json()
    if verbose:
        print(f"get_vehicle_state:\n{response_json}")
    return response_json['data']['vehicleState']


def get_vehicle_last_seen(vehicle_id, verbose):
    rivian = get_rivian_object()
    try:
        response = rivian.get_vehicle_last_connection(vehicle_id=vehicle_id)
    except Exception as e:
        _, _, message, _, _ = e.args
        print(f"{message['errors'][0]['message']}")
        return None
    response_json = response.json()
    if verbose:
        print(f"get_vehicle_last_seen:\n{response_json}")
    last_seen = parse(response_json['data']['vehicleState']['cloudConnection']['lastSync'])
    return last_seen


def get_ota_info(vehicle_id, verbose):
    rivian = get_rivian_object()
    try:
        response = rivian.get_ota_details(vehicle_id=vehicle_id)
    except Exception as e:
        _, _, message, _, _ = e.args
        print(f"{message['errors'][0]['message']}")
        return None
    response_json = response.json()
    if verbose:
        print(f"get_ota_info:\n{response_json}")
    return response_json['data']['getVehicle']


def transaction_status(order_id, verbose):
    rivian = get_rivian_object()
    response = rivian.transaction_status(order_id)
    response_json = response.json()
    if verbose:
        print(f"transaction_status:\n{response_json}")
    status = {}
    transaction_status = response_json['data']['transactionStatus']
    for s in (
        'titleAndReg',
        'tradeIn',
        'finance',
        'delivery',
        'insurance',
        'documentUpload',
        'contracts',
        'payment',
    ):
        status[transaction_status[s]['consumerStatus']['displayOrder']] = {
            'item': s,
            'status': transaction_status[s]['sourceStatus']['status'],
            'complete': transaction_status[s]['consumerStatus']['complete']
        }
    return status


def finance_summary(order_id, verbose):
    rivian = get_rivian_object()
    response = rivian.finance_summary(order_id=order_id)
    response_json = response.json()
    if verbose:
        print(f"finance_summary:\n{response_json}")


def chargers(verbose):
    rivian = get_rivian_object()
    response = rivian.get_registered_wallboxes()
    response_json = response.json()
    if verbose:
        print(f"chargers:\n{response_json}")
    return response_json['data']['getRegisteredWallboxes']


def delivery(order_id, verbose):
    rivian = get_rivian_object()
    response = rivian.delivery(order_id=order_id)
    response_json = response.json()
    if verbose:
        print(f"delivery:\n{response_json}")
    vehicle = {}
    vehicle['vin'] = response_json['data']['delivery']['vehicleVIN']
    vehicle['carrier'] = response_json['data']['delivery']['carrier']
    vehicle['status'] = response_json['data']['delivery']['status']
    vehicle['appointmentDetails'] = response_json['data']['delivery']['appointmentDetails']
    return vehicle


def speakers(verbose):
    rivian = get_rivian_object()
    response = rivian.get_provisioned_camp_speakers()
    response_json = response.json()
    if verbose:
        print(f"speakers:\n{response_json}")
    return response_json['data']['currentUser']['vehicles']


def images(verbose):
    rivian = get_rivian_object()
    response = rivian.get_vehicle_images()
    response_json = response.json()
    if verbose:
        print(f"images:\n{response_json}")
    images = []
    for i in response_json['data']['getVehicleOrderMobileImages']:
        images.append({
            'size': i['size'],
            'design': i['design'],
            'placement': i['placement'],
            'url': i['url']
        })
    print(images)
    return images


def get_user_info(verbose):
    rivian = get_rivian_object()
    response = rivian.get_user_info()
    response_json = response.json()
    if verbose:
        print(f"get_user_info:\n{response_json}")
    vehicles = []
    for vehicle in response_json['data']['currentUser']['vehicles']:
        vehicles.append({
            'id': vehicle['id'],
            'vin': vehicle['vin'],
            'model': vehicle['vehicle']['model'],
        })
    return vehicles


def get_user(verbose):
    rivian = get_rivian_object()
    response = rivian.user()
    response_json = response.json()
    if verbose:
        print(f"get_user:\n{response_json}")
    user = {
        'userId': response_json['data']['user']['userId'],
        'email': response_json['data']['user']['email']['email'],
        'phone': response_json['data']['user']['phone']['formatted'],
        'firstName': response_json['data']['user']['firstName'],
        'lastName': response_json['data']['user']['lastName'],
        'newsletterSubscription': response_json['data']['user']['newsletterSubscription'],
        'smsSubscription': response_json['data']['user']['smsSubscription'],
        'registrationChannels2FA': response_json['data']['user']['registrationChannels2FA'],
        'addresses': [],
    }
    for a in response_json['data']['user']['addresses']:
        user['addresses'].append({
            'type': a['type'],
            'line1': a['line1'],
            'line2': a['line2'],
            'city': a['city'],
            'state': a['state'],
            'country': a['country'],
            'postalCode': a['postalCode'],
        })
    return user


def test_graphql(verbose):
    rivian = get_rivian_object()
    query = {
        "operationName": "GetAdventureFeed",
        "query": 'query GetAdventureFeed($locale: String!, $slug: String!) { egAdventureFeedCollection(locale: $locale, limit: 1, where: { slug: $slug } ) { items { slug entryTitle cardsCollection(limit: 15) { items { __typename ... on EgAdventureFeedStoryCard { slug entryTitle title subtitle cover { entryTitle sourcesCollection(limit: 1) { items { entryTitle media auxiliaryData { __typename ... on EgImageAuxiliaryData { altText } } } } } slidesCollection { items { entryTitle duration theme gradient mediaCollection(limit: 2) { items { __typename ... on EgCloudinaryMedia { entryTitle sourcesCollection(limit: 1) { items { entryTitle media auxiliaryData { __typename ... on EgImageAuxiliaryData { altText } } } } } ... on EgLottieAnimation { entryTitle altText media mode } } } } } } ... on EgAdventureFeedEditorialCard { slug entryTitle title subtitle cover { entryTitle sourcesCollection(limit: 1) { items { entryTitle media auxiliaryData { __typename ... on EgImageAuxiliaryData { altText } } } } } sectionsCollection { items { entryTitle theme mediaCollection(limit: 2) { items { __typename ... on EgCloudinaryMedia { entryTitle sourcesCollection(limit: 1) { items { entryTitle media auxiliaryData { __typename ... on EgImageAuxiliaryData { altText } } } } } ... on EgLottieAnimation { entryTitle altText media mode } } } } } } } } } } }',
        "variables": {
            "locale": "en_US",
        },
    }
    response = rivian.raw_graphql_query(url=RIVIAN_CONTENT_PATH, query=query, headers=rivian.gateway_headers())
    response_json = response.json()
    if verbose:
        print(f"test_graphql:\n{response_json}")


def show_local_time(ts):
    t = parse(ts)
    to_zone = tz.tzlocal()
    t = t.astimezone(to_zone)
    return t.strftime("%m/%d/%Y, %H:%M%p %Z")


def celsius_to_fahrenheit(c):
    return (c * 9/5) + 32


def meters_to_miles(m):
    return m / 1609.0


def main():
    parser = argparse.ArgumentParser(description='Rivian CLI')
    parser.add_argument('--login', help='Login to account', required=False, action='store_true')
    parser.add_argument('--user', help='Display user info', required=False, action='store_true')
    parser.add_argument('--vehicles', help='Display vehicles', required=False, action='store_true')
    parser.add_argument('--chargers', help='Display chargers', required=False, action='store_true')
    parser.add_argument('--speakers', help='Display Speakers', required=False, action='store_true')
    parser.add_argument('--images', help='Display Image URLs', required=False, action='store_true')
    parser.add_argument('--vehicle_orders', help='Display vehicle orders', required=False, action='store_true')
    parser.add_argument('--retail_orders', help='Display retail orders', required=False, action='store_true')
    parser.add_argument('--payment_methods', help='Show payment methods', required=False, action='store_true')
    parser.add_argument('--test', help='For testing graphql queries', required=False, action='store_true')
    parser.add_argument('--charge_ids', help='Show charge_ids', required=False, action='store_true')
    parser.add_argument('--verbose', help='Verbose output', required=False, action='store_true')
    parser.add_argument('--privacy', help='Fuzz order/vin info', required=False, action='store_true')
    parser.add_argument('--state', help='Get vehicle state', required=False, action='store_true')
    parser.add_argument('--vehicle', help='Get vehicle access info', required=False, action='store_true')
    parser.add_argument('--vehicle_id', help='Vehicle to query (defaults to first one found)', required=False)
    parser.add_argument('--last_seen', help='Timestamp vehicle was last seen', required=False, action='store_true')
    parser.add_argument('--user_info', help='Show user information', required=False, action='store_true')
    parser.add_argument('--ota', help='Show user information', required=False, action='store_true')
    parser.add_argument('--poll', help='Poll vehicle state', required=False, action='store_true')
    args = parser.parse_args()

    if args.login:
        login(args.verbose)

    rivian_info = {
        'vehicle_orders': [],
        'retail_orders': [],
        'vehicles': [],
    }

    vehicle_id = None

    needs_vehicle = args.vehicles or args.vehicle or args.state or args.last_seen or args.ota or args.poll

    if args.vehicle_orders or needs_vehicle:
        verbose = args.vehicle_orders
        rivian_info['vehicle_orders'] = vehicle_orders(verbose)

    if args.vehicle_orders:
        if len(rivian_info['vehicle_orders']):
            print("Vehicle Orders:")
            for order in rivian_info['vehicle_orders']:
                order_id = 'xxxx' + order['id'][-4:] if args.privacy else order['id']
                print(f"Order ID: {order_id}")
                print(f"Order Date: {order['orderDate'][:10] if args.privacy else order['orderDate']}")
                print(f"Config State: {order['configurationStatus']}")
                print(f"Order State: {order['state']}")
                print(f"Status: {order['fulfillmentSummaryStatus']}")
                print(f"Item: {order['items'][0]}")
                print(f"Customer flow complete: {'Yes' if order['isConsumerFlowComplete'] else 'No'}")

                # No extra useful info to display
                # order_info = get_order(order['id'], args.verbose)

                # Get delivery info
                delivery_status = delivery(order['id'], args.verbose)
                print(f"Delivery carrier: {delivery_status['carrier']}")
                print(f"Delivery status: {delivery_status['status']}")
                if delivery_status['appointmentDetails']:
                    print("Delivery appointment details:")
                    start = parse(delivery_status['appointmentDetails']['startDateTime'])
                    end = parse(delivery_status['appointmentDetails']['endDateTime'])
                    print(f'   Start: {start.strftime("%m/%d/%Y, %H:%M %p")}')
                    print(f'   End  : {end.strftime("%m/%d/%Y, %H:%M %p")}')
                else:
                    print("Delivery appointment details: Not available yet")

                # Get transaction steps
                transaction_steps = transaction_status(order['id'], args.verbose)
                i = 1
                completed = 0
                for s in transaction_steps:
                    if transaction_steps[s]['complete']:
                        completed += 1
                print(f"{completed}/{len(transaction_steps)} Steps Complete:")
                for s in sorted(transaction_steps):
                    print(f"   Step: {s}: {transaction_steps[s]['item']}: {transaction_steps[s]['status']}, Complete: {transaction_steps[s]['complete']}")
                    i += 1

                # Don't need to show this for now
                # finance_summary(order['id'], args.verbose)
                print("\n")
        else:
            print("No Vehicle Orders found")

    if args.retail_orders:
        rivian_info['retail_orders'] = retail_orders(args.verbose)
        if len(rivian_info['retail_orders']):
            print("Retail Orders:")
            for order in rivian_info['retail_orders']:
                order_id = 'xxxx' + order['id'][-4:] if args.privacy else order['id']
                print(f"Order ID: {order_id}")
                print(f"Order Date: {order['orderDate'][:10] if args.privacy else order['orderDate']}")
                print(f"Order State: {order['state']}")
                print(f"Status: {order['fulfillmentSummaryStatus']}")
                print(f"Items: {', '.join(order['items'])}")
                print("\n")
        else:
            print("No Retail Orders found")

    if args.vehicles or needs_vehicle:
        found_vehicle = False
        verbose = args.vehicles
        for order in rivian_info['vehicle_orders']:
            details = order_details(order['id'], verbose)
            vehicle = {}
            for i in details:
                value = details[i]
                if i in ('vin', 'vehicleId') and args.privacy:
                    value = value[-8:-3] + 'xxx'
                vehicle[i] = value
            rivian_info['vehicles'].append(vehicle)
            if not found_vehicle:
                if args.vehicle_id:
                    if vehicle['vehicleId'] == args.vehicle_id:
                        found_vehicle = True
                else:
                    vehicle_id = vehicle['vehicleId']
                    found_vehicle = True
        if not found_vehicle:
            print(f"Didn't find vehicle ID {args.vehicle_id}")
            return -1

    if args.vehicles:
        if len(rivian_info['vehicles']):
            print("Vehicles:")
            for v in rivian_info['vehicles']:
                for i in v:
                    print(f"{i}: {v[i]}")
                print("\n")
        else:
            print("No Vehicles found")

    if args.payment_methods:
        pmt = payment_methods(args.verbose)
        print("Payment Methods:")
        if len(pmt):
            for p in pmt:
                print(f"Type: {p['type']}")
                print(f"Default: {p['default']}")
                if p['card']:
                    for i in p['card']:
                        print(f"Card {i}: {p['card'][i]}")
                print("\n")
        else:
            print("No Payment Methods found")

    if args.charge_ids:
        print("Charge IDs:")
        data = check_by_rivian_id(args.verbose)
        for i in data:
            print(f"{i}: {data[i]}")
        data = get_linked_email_for_rivian_id(args.verbose)
        for i in data:
            print(f"{i}: {data[i]}")
        print("\n")

    # No value?
    # get_parameter_store_values(args.verbose)

    # For testing new graphql queries
    if args.test:
        test_graphql(args.verbose)

    if args.chargers:
        rivian_info['chargers'] = chargers(args.verbose)
        if len(rivian_info['chargers']):
            print("Chargers:")
            for c in rivian_info['chargers']:
                for i in c:
                    print(f"{i}: {c[i]}")
                print("\n")
        else:
            print("No Chargers found")

    if args.speakers:
        rivian_info['speakers'] = speakers(args.verbose)
        if len(rivian_info['speakers']):
            print("Speakers:")
            for v in rivian_info['speakers']:
                print(f"Vehicle ID: {v['id']}")
                for c in v['connectedProducts']:
                    print(f"   {c['__typename']}: Serial # {c['serialNumber']}")
        else:
            print("No Speakers found")

    if args.ota:
        ota = get_ota_info(vehicle_id, args.verbose)
        if len(ota):
            if ota['availableOTAUpdateDetails']:
                print(f"Available OTA Version: {ota['currentOTAUpdateDetails']['version']}")
                print(f"Available OTA Release notes: {ota['currentOTAUpdateDetails']['url']}")
            if ota['currentOTAUpdateDetails']:
                print(f"Current Version: {ota['currentOTAUpdateDetails']['version']}")
                print(f"Current Version Release notes: {ota['currentOTAUpdateDetails']['url']}")
        else:
            print("No OTA info available")

    # Basic images for vehicle
    if args.images:
        rivian_info['images'] = images(args.verbose)
        if len(rivian_info['images']):
            print("Images:")
            for c in rivian_info['images']:
                for i in c:
                    print(f"{i}: {c[i]}")
                print("\n")
        else:
            print("No Images found")

    if args.user_info:
        print("User Vehicles:")
        user_info = user_information(args.verbose)
        for v in user_info['vehicles']:
            print(f"Vehicle ID: {v['id']}")
            if args.privacy:
                vin = v['vin'][-8:-3] + 'xxx'
            else:
                vin = v['vin']
            print(f"   Vin: {vin}")
            print(f"   State: {v['state']}")
            print(f"   Kind: {v['vehicle']['modelYear']} {v['vehicle']['make']} {v['vehicle']['model']}")
            print(f"   General assembly date: {v['vehicle']['actualGeneralAssemblyDate']}")
            print(f"   OTA early access: {v['vehicle']['otaEarlyAccessStatus']}")
            print("   Features:")
            for f in v['vehicle']['vehicleState']['supportedFeatures']:
                print(f"      {f['name']}: {f['status']}")

    if args.user and not args.privacy:
        user = get_user(args.verbose)
        print("User details:")
        for i in user:
            if i == 'registrationChannels2FA':
                for j in user[i]:
                    print(f"registrationChannels2FA {j}: {user[i][j]}")
            elif i == 'addresses':
                address_num = 1
                for a in user[i]:
                    print(f"Address {address_num}:")
                    for j in a:
                        data = a[j]
                        if type(data) == list:
                            data = ", ".join(data)
                        print(f"   {j}: {data}")
                    address_num += 1
            else:
                print(f"{i}: {user[i]}")
        print("\n")

    if args.state:
        state = get_vehicle_state(vehicle_id, args.verbose)
        print("Vehicle State:")
        print(f"Power State: {state['powerState']['value']}")
        print(f"Drive Mode: {state['driveMode']['value']}")
        print(f"Gear Status: {state['gearStatus']['value']}")
        print(f"Battery Level: {state['batteryLevel']['value']:.1f}%")
        print(f"Range: {state['distanceToEmpty']['value']} miles")
        print(f"Battery Limit: {state['batteryLimit']['value']:.1f}%")
        print(f"Charging state: {state['chargerState']['value']}")
        print(f"Charger status: {state['chargerStatus']['value']}")
        print(f"Mileage: {meters_to_miles(state['vehicleMileage']['value']):.1f} miles")
        print(f"Version: {state['otaCurrentVersion']['value']}")
        print(f"OTA: {state['otaAvailableVersion']['value']}")
        print(f"OTA Download progress: {state['otaDownloadProgress']['value']:.1f}%")
        print(f"OTA Installation Duration: {state['otaInstallDuration']['value']}")
        print(f"OTA Install progress: {state['otaInstallProgress']['value']:.1f}%")
        print(f"OTA Install Ready: {state['otaInstallReady']['value']}")
        print(f"OTA Installation Time: {state['otaInstallTime']['value']}")
        print(f"OTA Installation Type: {state['otaInstallType']['value']}")
        print(f"OTA Installation Status: {state['otaStatus']['value']}")
        print(f"OTA Current Status: {state['otaCurrentStatus']['value']}")
        print(f"Location: {state['gnssLocation']['latitude']},{state['gnssLocation']['longitude']}")
        print(f"Location Last Seen: {show_local_time(state['gnssLocation']['timeStamp'])}")

        print(f"Climate Interior Temp: {celsius_to_fahrenheit(state['cabinClimateInteriorTemperature']['value'])}ºF")
        print(f"Climate Driver Temp: {celsius_to_fahrenheit(state['cabinClimateDriverTemperature']['value'])}ºF")
        print(f"Cabin Preconditioning Status: {state['cabinPreconditioningStatus']['value']}")
        print(f"Cabin Preconditioning Type: {state['cabinPreconditioningType']['value']}")
        print(f"Defrost: {state['defrostDefogStatus']['value']}")
        print(f"Steering Wheel Heat: {state['steeringWheelHeat']['value']}")
        print(f"Alarm active: {state['alarmSoundStatus']['value']}")
        print(f"Pet Mode: {state['petModeStatus']['value']}")
        print(f"Gear Guard Video: {state['gearGuardVideoStatus']['value']}")
        print(f"Gear Guard Mode: {state['gearGuardVideoMode']['value']}")
        print(f"Last Alarm: {show_local_time(state['alarmSoundStatus']['timeStamp'])}")
        print(f"Time to end of charge: {state['timeToEndOfCharge']['value']}")
        print(f"Time to end of charge: {state['timeToEndOfCharge']['value']}")
        print("Doors:")
        print(f"   Front left locked: {state['doorFrontLeftLocked']['value'] == 'locked'}")
        print(f"   Front left closed: {state['doorFrontLeftClosed']['value'] == 'closed'}")
        print(f"   Front right locked: {state['doorFrontRightLocked']['value'] == 'locked'}")
        print(f"   Front right closed: {state['doorFrontRightClosed']['value'] == 'closed'}")
        print(f"   Rear left locked: {state['doorRearLeftLocked']['value'] == 'locked'}")
        print(f"   Rear left closed: {state['doorRearLeftClosed']['value'] == 'closed'}")
        print(f"   Rear right locked: {state['doorRearRightLocked']['value'] == 'locked'}")
        print(f"   Rear right closed: {state['doorRearRightClosed']['value'] == 'closed'}")
        print("Windows:")
        print(f"   Front left closed: {state['windowFrontLeftClosed']['value'] == 'closed'}")
        print(f"   Front right closed: {state['windowFrontRightClosed']['value'] == 'closed'}")
        print(f"   Rear left closed: {state['windowRearLeftClosed']['value'] == 'closed'}")
        print(f"   Rear right closed: {state['windowRearRightClosed']['value'] == 'closed'}")
        print("Seats:")
        print(f"   Front left Heat: {state['seatFrontLeftHeat']['value'] == 'On'}")
        print(f"   Front right Heat: {state['seatFrontRightHeat']['value'] == 'On'}")
        print(f"   Rear left Heat: {state['seatRearLeftHeat']['value'] == 'On'}")
        print(f"   Rear right Heat: {state['seatRearRightHeat']['value'] == 'On'}")
        print("Frunk:")
        print(f"   Frunk locked: {state['closureFrunkLocked']['value'] == 'locked'}")
        print(f"   Frunk closed: {state['closureFrunkClosed']['value'] == 'closed'}")
        print(f"Gear Guard Locked: {state['gearGuardLocked']['value'] == 'locked'}")
        print("Lift Gate:")
        print(f"   Lift Gate Locked: {state['closureLiftgateLocked']['value'] == 'locked'}")
        print(f"   Lift Gate Closed: {state['closureLiftgateClosed']['value'] == 'closed'}")
        print("Tonneau:")
        print(f"   Tonneau Locked: {state['closureTonneauLocked']['value'] == 'locked'}")
        print(f"   Tonneau Closed: {state['closureTonneauClosed']['value'] == 'closed'}")
        print(f"Wiper Fluid: {state['wiperFluidState']['value']}")
        print("Tire pressures:")
        print(f"   Front Left: {state['tirePressureStatusFrontLeft']['value']}")
        print(f"   Front Right: {state['tirePressureStatusFrontRight']['value']}")
        print(f"   Rear Left: {state['tirePressureStatusRearLeft']['value']}")
        print(f"   Rear Right: {state['tirePressureStatusRearRight']['value']}")

    if args.poll:
        # Charge State = charging_ready or charging_active
        # Charger Status = chrgr_sts_not_connected, chrgr_sts_connected_charging, chrgr_sts_connected_no_chrg
        print("Power,Drive Mode,Gear,Mileage,Battery,Range,Location,Charger Status,Charge State,Battery Limit,Charge End")
        while True:
            state = get_vehicle_state(vehicle_id, args.verbose, minimal=True)
            print(
                f"{state['powerState']['value']}, "
                f"{state['driveMode']['value']}, "
                f"{state['gearStatus']['value']}, "
                f"{meters_to_miles(state['vehicleMileage']['value']):.1f}, "
                f"{state['batteryLevel']['value']:.1f}%, "
                f"{state['distanceToEmpty']['value']}, "
                f"{state['gnssLocation']['latitude']} / {state['gnssLocation']['longitude']}, "
                f"{state['chargerStatus']['value']}, "
                f"{state['chargerState']['value']}, "
                f"{state['batteryLimit']['value']:.1f}%, "
                f"{state['timeToEndOfCharge']['value']}"
            )
            time.sleep(POLL_FREQUENCY)

    if args.vehicle:
        vehicle = get_vehicle(vehicle_id, args.verbose)
        print("Vehicle Users:")
        for u in vehicle:
            print(f"{u['firstName']} {u['lastName']}")
            print(f"   Email: {u['email']}")
            print(f"   Roles: {u['roles']}")
            print("   Devices:")
            for d in u['devices']:
                print(f"      {d['deviceName']}, Paired: {d['isPaired']}, Enabled: {d['isEnabled']}")

    if args.last_seen:
        last_seen = get_vehicle_last_seen(vehicle_id, args.verbose)
        print(f"Vehicle last seen: {show_local_time(last_seen)}")


if __name__ == '__main__':
    main()

