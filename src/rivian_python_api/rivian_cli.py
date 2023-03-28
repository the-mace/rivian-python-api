#!/usr/bin/env python
# encoding: utf-8

import os
import argparse
from rivian_api import *
import pickle
from dateutil.parser import parse
from dateutil import tz
import time
from datetime import datetime

# Polling constantly while vehicle is awake keeps it awake, all times in seconds
POLL_FREQUENCY = 30
# If not sleeping and nothing changes for this period of time then do a VEHICLE_SLEEP_WAIT
# Set to 0 for continual polling at POLL_FREQUENCY
INACTIVITY_WAIT = 0
# INACTIVITY_WAIT = 30 * 60
# How long to stop polling to let car go to sleep
VEHICLE_SLEEP_WAIT = 40 * 60

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
    while True:
        try:
            rivian.create_csrf_token()
            break
        except Exception as e:
            time.sleep(5)

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
                "id": d["id"],
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
        print(f"{str(e)}")
        return None
    try:
        response_json = response.json()
    except Exception as e:
        log.warning(f"Error getting vehicle state: {str(e)}")
        return None
    if verbose:
        print(f"get_vehicle_state:\n{response_json}")
    return response_json['data']['vehicleState']


def get_vehicle_last_seen(vehicle_id, verbose):
    rivian = get_rivian_object()
    try:
        response = rivian.get_vehicle_last_connection(vehicle_id=vehicle_id)
    except Exception as e:
        print(f"{str(e)}")
        return None
    response_json = response.json()
    if verbose:
        print(f"get_vehicle_last_seen:\n{response_json}")
    last_seen = parse(response_json['data']['vehicleState']['cloudConnection']['lastSync'])
    return last_seen


def plan_trip(vehicle_id, starting_soc, starting_range_meters, origin_lat, origin_long, dest_lat, dest_long, verbose):
    rivian = get_rivian_object()
    try:
        response = rivian.plan_trip(
            vehicle_id=vehicle_id,
            starting_soc=float(starting_soc),
            starting_range_meters=float(starting_range_meters),
            origin_lat=float(origin_lat),
            origin_long=float(origin_long),
            dest_lat=float(dest_lat),
            dest_long=float(dest_long),
        )
    except Exception as e:
        print(f"{str(e)}")
        return None
    response_json = response.json()
    if verbose:
        print(f"plan_trip:\n{response_json}")
    return response_json


def get_ota_info(vehicle_id, verbose):
    rivian = get_rivian_object()
    try:
        response = rivian.get_ota_details(vehicle_id=vehicle_id)
    except Exception as e:
        print(f"{str(e)}")
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


def vehicle_command(command, vehicle_id=None, verbose=False):
    vehiclePublicKey = None
    user_info = user_information(verbose)
    for v in user_info['vehicles']:
        if vehicle_id and v['id'] == vehicle_id:
            found = True
        else:
            vehicle_id = v['id']
            found = True
        if found:
            vehiclePublicKey = v['vas']['vehiclePublicKey']
            break
        # Only need first
    vasPhoneId = user_info['enrolledPhones'][0]['vas']['vasPhoneId']
    deviceName = user_info['enrolledPhones'][0]['enrolled'][0]['deviceName']

    vehicle = get_vehicle(vehicle_id=vehicle_id, verbose=verbose)
    deviceId = None
    for u in vehicle:
        for d in u['devices']:
            if d['deviceName'] == deviceName:
                deviceId = d['id']
                break
        if deviceId:
            break

    print(f"Vehicle ID: {vehicle_id} vasPhoneID: {vasPhoneId} vehiclePublicKey: {vehiclePublicKey} deviceId: {deviceId}")


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
    if type(ts) is str:
        t = parse(ts)
    else:
        t = ts
    to_zone = tz.tzlocal()
    t = t.astimezone(to_zone)
    return t.strftime("%m/%d/%Y, %H:%M%p %Z")


def celsius_to_fahrenheit(c):
    return (c * 9/5) + 32


def meters_to_miles(m, metric=False):
    if metric:
        return m
    else:
        return m / 1609.0


def miles_to_meters(m, metric=False):
    if metric:
        return m
    else:
        return m * 1609.0


def kilometers_to_miles(m, metric=False):
    if metric:
        return m
    else:
        return (m * 1000) / 1609.0


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
    parser.add_argument('--metric', help='Use metric vs imperial units', required=False, action='store_true')
    parser.add_argument('--plan_trip', help='Plan a trip - starting soc, starting range in meters, origin lat,origin long,dest lat,dest long', required=False)
    parser.add_argument('--command', help='Send vehicle a command', required=False,
                        choices=['WAKE_VEHICLE',
                                 'OPEN_FRUNK',
                                 'CLOSE_FRUNK',
                                 'OPEN_ALL_WINDOWS',
                                 'CLOSE_ALL_WINDOWS',
                                 'UNLOCK_ALL_CLOSURES',
                                 'LOCK_ALL_CLOSURES',
                                 'ENABLE_GEAR_GUARD_VIDEO',
                                 'DISABLE_GEAR_GUARD_VIDEO',
                                 'HONK_AND_FLASH_LIGHTS',
                                 'OPEN_TONNEAU_COVER',
                                 'CLOSE_TONNEAU_COVER',
                                 ]
                        )
    args = parser.parse_args()

    if args.login:
        login(args.verbose)

    rivian_info = {
        'vehicle_orders': [],
        'retail_orders': [],
        'vehicles': [],
    }

    vehicle_id = None

    needs_vehicle = args.vehicles or \
                    args.vehicle or \
                    args.state or \
                    args.last_seen or \
                    args.ota or \
                    args.poll or \
                    args.plan_trip or \
                    args.user_info

    if args.vehicle_orders or (needs_vehicle and not args.vehicle_id):
        verbose = args.vehicle_orders and args.verbose
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

    if args.vehicles or (needs_vehicle and not args.vehicle_id):
        found_vehicle = False
        verbose = args.vehicles and args.verbose
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
                print(f"Available OTA Version: {ota['availableOTAUpdateDetails']['version']}")
                print(f"Available OTA Release notes: {ota['availableOTAUpdateDetails']['url']}")
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
        for p in user_info['enrolledPhones']:
            print("Enrolled phones:")
            for d in p['enrolled']:
                if d['vehicleId'] == vehicle_id:
                    print(f"   Device Name: {d['deviceName']}")
                    print(f"   Device identityId: {d['identityId']}")
            print(f"   vasPhoneId: {p['vas']['vasPhoneId']}")
            print(f"   publicKey: {p['vas']['publicKey']}")

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
        print(f"Mileage: {meters_to_miles(state['vehicleMileage']['value'], args.metric):.1f} miles")
        print(f"Location: {state['gnssLocation']['latitude']},{state['gnssLocation']['longitude']}")

        print("Battery:")
        print(f"   Battery Level: {state['batteryLevel']['value']:.1f}%")
        print(f"   Range: {state['distanceToEmpty']['value']} miles")
        print(f"   Battery Limit: {state['batteryLimit']['value']:.1f}%")
        print(f"   Charging state: {state['chargerState']['value']}")
        print(f"   Charger status: {state['chargerStatus']['value']}")
        print(f"   Time to end of charge: {state['timeToEndOfCharge']['value']}")

        print("OTA:")
        print(f"   Current Version: {state['otaCurrentVersion']['value']}")
        print(f"   Available version: {state['otaAvailableVersion']['value']}")
        print(f"   Status: {state['otaStatus']['value']}")
        print(f"   Install type: {state['otaInstallType']['value']}")
        print(f"   Duration: {state['otaInstallDuration']['value']}")
        print(f"   Download progress: {state['otaDownloadProgress']['value']}")
        print(f"   Install ready: {state['otaInstallReady']['value']}")
        print(f"   Install progress: {state['otaInstallProgress']['value']}")
        print(f"   Install time: {state['otaInstallTime']['value']}")
        print(f"   Current Status: {state['otaCurrentStatus']['value']}")

        print("Climate:")
        print(f"   Climate Interior Temp: {celsius_to_fahrenheit(state['cabinClimateInteriorTemperature']['value'])}ºF")
        print(f"   Climate Driver Temp: {celsius_to_fahrenheit(state['cabinClimateDriverTemperature']['value'])}ºF")
        print(f"   Cabin Preconditioning Status: {state['cabinPreconditioningStatus']['value']}")
        print(f"   Cabin Preconditioning Type: {state['cabinPreconditioningType']['value']}")
        print(f"   Defrost: {state['defrostDefogStatus']['value']}")
        print(f"   Steering Wheel Heat: {state['steeringWheelHeat']['value']}")
        print(f"   Pet Mode: {state['petModeStatus']['value']}")

        print("Security:")
        print(f"   Alarm active: {state['alarmSoundStatus']['value']}")
        print(f"   Gear Guard Video: {state['gearGuardVideoStatus']['value']}")
        print(f"   Gear Guard Mode: {state['gearGuardVideoMode']['value']}")
        print(f"   Last Alarm: {show_local_time(state['alarmSoundStatus']['timeStamp'])}")
        print(f"   Gear Guard Locked: {state['gearGuardLocked']['value'] == 'locked'}")

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

        print("Storage:")
        print("   Frunk:")
        print(f"      Frunk locked: {state['closureFrunkLocked']['value'] == 'locked'}")
        print(f"      Frunk closed: {state['closureFrunkClosed']['value'] == 'closed'}")

        print("   Lift Gate:")
        print(f"      Lift Gate Locked: {state['closureLiftgateLocked']['value'] == 'locked'}")
        print(f"      Lift Gate Closed: {state['closureLiftgateClosed']['value']}")

        print("   Tonneau:")
        print(f"      Tonneau Locked: {state['closureTonneauLocked']['value']}")
        print(f"      Tonneau Closed: {state['closureTonneauClosed']['value']}")

        print("Maintenance:")
        print(f"   Wiper Fluid: {state['wiperFluidState']['value']}")
        print("   Tire pressures:")
        print(f"      Front Left: {state['tirePressureStatusFrontLeft']['value']}")
        print(f"      Front Right: {state['tirePressureStatusFrontRight']['value']}")
        print(f"      Rear Left: {state['tirePressureStatusRearLeft']['value']}")
        print(f"      Rear Right: {state['tirePressureStatusRearRight']['value']}")

    if args.poll:
        # Power state = ready, go, sleep, standby,
        # Charge State = charging_ready or charging_active
        # Charger Status = chrgr_sts_not_connected, chrgr_sts_connected_charging, chrgr_sts_connected_no_chrg
        print(f"Polling car every {POLL_FREQUENCY} seconds, only showing changes in data.")
        if INACTIVITY_WAIT:
            print(f"If 'ready' and inactive for {INACTIVITY_WAIT / 60:.0f} minutes will pause polling once for "
                  f"every ready state cycle for {VEHICLE_SLEEP_WAIT / 60:.0f} minutes to allow car to go to sleep.")
        print("")

        print("timestamp,Power,Drive Mode,Gear,Mileage,Battery,Range,Latitude,Longitude,Charger Status,Charge State,Battery Limit,Charge End")
        last_state_change = time.time()
        last_state = None
        last_power_state = None
        long_sleep_completed = False
        while True:
            state = get_vehicle_state(vehicle_id, args.verbose, minimal=True)
            if not state:
                time.sleep(5)
                continue
            if last_power_state != 'ready' and state['powerState']['value'] == 'ready':
                # Allow one long sleep per ready state cycle to allow car to sleep
                long_sleep_completed = False
            last_power_state = state['powerState']['value']
            current_state = \
                f"{state['powerState']['value']}," \
                f"{state['driveMode']['value']}," \
                f"{state['gearStatus']['value']}," \
                f"{meters_to_miles(state['vehicleMileage']['value'], args.metric):.1f}," \
                f"{state['batteryLevel']['value']:.1f}%," \
                f"{kilometers_to_miles(state['distanceToEmpty']['value'], args.metric):.1f}," \
                f"{state['gnssLocation']['latitude']}," \
                f"{state['gnssLocation']['longitude']}," \
                f"{state['chargerStatus']['value']}," \
                f"{state['chargerState']['value']}," \
                f"{state['batteryLimit']['value']:.1f}%," \
                f"{state['timeToEndOfCharge']['value']}"
            if current_state != last_state:
                print(f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S %p %Z').strip()}," + current_state)
                last_state_change = datetime.now()
            last_state = current_state
            if state['powerState']['value'] == 'sleep':
                time.sleep(POLL_FREQUENCY)
            else:
                delta = (datetime.now() - last_state_change).total_seconds()
                if INACTIVITY_WAIT and not long_sleep_completed and delta >= INACTIVITY_WAIT:
                    print(f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S %p %Z').strip()} "
                          f"Sleeping for {VEHICLE_SLEEP_WAIT / 60:.0f} minutes")
                    time.sleep(VEHICLE_SLEEP_WAIT)
                    print(f"{datetime.now().strftime('%m/%d/%Y, %H:%M:%S %p %Z').strip()} "
                          f"Back to polling every {POLL_FREQUENCY} seconds, showing changes only")
                    long_sleep_completed = True
                else:
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
                print(f"      {d['deviceName']}, Paired: {d['isPaired']}, Enabled: {d['isEnabled']}, ID: {d['id']}")

    if args.last_seen:
        last_seen = get_vehicle_last_seen(vehicle_id, args.verbose)
        print(f"Vehicle last seen: {show_local_time(last_seen)}")

    if args.plan_trip:
        starting_soc, starting_range, origin_lat, origin_long, dest_lat, dest_long = args.plan_trip.split(',')
        starting_range_meters = miles_to_meters(float(starting_range), args.metric)
        planned_trip = plan_trip(
            vehicle_id,
            starting_soc,
            starting_range_meters,
            origin_lat,
            origin_long,
            dest_lat,
            dest_long,
            args.verbose
        )
        print(planned_trip)

    if args.command:
        vehicle_command(args.command, args.vehicle_id, args.verbose)


if __name__ == '__main__':
    main()
