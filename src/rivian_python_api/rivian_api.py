import logging
import requests
import uuid

RIVIAN_BASE_PATH = "https://rivian.com/api/gql"
RIVIAN_GATEWAY_PATH = RIVIAN_BASE_PATH + "/gateway/graphql"
RIVIAN_CHARGING_PATH = RIVIAN_BASE_PATH + "/chrg/user/graphql"
RIVIAN_ORDERS_PATH = RIVIAN_BASE_PATH + '/orders/graphql'
RIVIAN_CONTENT_PATH = RIVIAN_BASE_PATH + '/content/graphql'
RIVIAN_TRANSACTIONS_PATH = RIVIAN_BASE_PATH + '/t2d/graphql'

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "RivianApp/1304 CFNetwork/1404.0.5 Darwin/22.3.0",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Apollographql-Client-Name": "com.rivian.ios.consumer-apollo-ios",
}


class Rivian:
    def __init__(self):
        self._close_session = False
        self._session_token = ""
        self._access_token = ""
        self._refresh_token = ""
        self._app_session_token = ""
        self._user_session_token = ""
        self.client_id = ""
        self.client_secret = ""
        self.request_timeout = ""
        self._csrf_token = ""

        self.otp_needed = False
        self._otp_token = ""

    def login(self, username, password):
        self.create_csrf_token()
        url = RIVIAN_GATEWAY_PATH
        headers = HEADERS
        headers.update(
            {
                "Csrf-Token": self._csrf_token,
                "A-Sess": self._app_session_token,
                "Apollographql-Client-Name": "com.rivian.ios.consumer-apollo-ios",
                "Dc-Cid": f"m-ios-{uuid.uuid4()}",
            }
        )

        query = {
            "operationName": "Login",
            "query": "mutation Login($email: String!, $password: String!) {\n  login(email: $email, password: $password) {\n    __typename\n    ... on MobileLoginResponse {\n      __typename\n      accessToken\n      refreshToken\n      userSessionToken\n    }\n    ... on MobileMFALoginResponse {\n      __typename\n      otpToken\n    }\n  }\n}",
            "variables": {"email": username, "password": password},
        }

        response = self.raw_graphql_query(url=url, query=query, headers=headers)
        response_json = response.json()
        login_data = response_json["data"]["login"]
        if "otpToken" in login_data:
            self.otp_needed = True
            self._otp_token = login_data["otpToken"]
        else:
            self._access_token = login_data["accessToken"]
            self._refresh_token = login_data["refreshToken"]
            self._user_session_token = login_data["userSessionToken"]
        return response

    def login_with_otp(self, username, otpCode):
        url = RIVIAN_GATEWAY_PATH
        headers = HEADERS
        headers.update(
            {
                "Csrf-Token": self._csrf_token,
                "A-Sess": self._app_session_token,
                "Apollographql-Client-Name": "com.rivian.ios.consumer-apollo-ios",
            }
        )

        query = {
            "operationName": "LoginWithOTP",
            "query": "mutation LoginWithOTP($email: String!, $otpCode: String!, $otpToken: String!) {\n  loginWithOTP(email: $email, otpCode: $otpCode, otpToken: $otpToken) {\n    __typename\n    ... on MobileLoginResponse {\n      __typename\n      accessToken\n      refreshToken\n      userSessionToken\n    }\n  }\n}",
            "variables": {
                "email": username,
                "otpCode": otpCode,
                "otpToken": self._otp_token,
            },
        }

        response = self.raw_graphql_query(url=url, query=query, headers=headers)
        response_json = response.json()
        login_data = response_json["data"]["loginWithOTP"]
        self._access_token = login_data["accessToken"]
        self._refresh_token = login_data["refreshToken"]
        self._user_session_token = login_data["userSessionToken"]
        return response

    def create_csrf_token(self):
        url = RIVIAN_GATEWAY_PATH
        headers = HEADERS

        query = {
            "operationName": "CreateCSRFToken",
            "query": "mutation CreateCSRFToken {createCsrfToken {__typename csrfToken appSessionToken}}",
            "variables": None,
        }

        response = self.raw_graphql_query(url=url, query=query, headers=headers)
        response_json = response.json()
        csrf_data = response_json["data"]["createCsrfToken"]
        self._csrf_token = csrf_data["csrfToken"]
        self._app_session_token = csrf_data["appSessionToken"]
        return response

    def raw_graphql_query(self, url, query, headers):
        response = requests.post(url, json=query, headers=headers)
        return response

    def gateway_headers(self):
        headers = HEADERS
        headers.update(
            {
                "Csrf-Token": self._csrf_token,
                "A-Sess": self._app_session_token,
                "U-Sess": self._user_session_token,
                "Dc-Cid": f"m-ios-{uuid.uuid4()}",
            }
        )
        return headers

    def transaction_headers(self):
        headers = self.gateway_headers()
        headers.update(
            {
                "dc-cid": f"t2d--{uuid.uuid4()}--{uuid.uuid4()}",
                "csrf-token": self._csrf_token,
                "app-id": "t2d"
            }
        )
        return headers

    def vehicle_orders(self):
        headers = self.gateway_headers()
        query = {
            "operationName": "vehicleOrders",
            "query": "query vehicleOrders { orders(input: {orderTypes: [PRE_ORDER, VEHICLE], pageInfo: {from: 0, size: 10000}}) { __typename data { __typename id orderDate state configurationStatus fulfillmentSummaryStatus items { __typename sku } consumerStatuses { __typename isConsumerFlowComplete } } } }",
            "variables": {},
        }
        response = self.raw_graphql_query(url=RIVIAN_GATEWAY_PATH, query=query, headers=headers)
        return response

    def delivery(self, order_id):
        headers = self.gateway_headers()
        query = {
            "operationName": "delivery",
            "query": "query delivery($orderId: ID!) { delivery(orderId: $orderId) { __typename status carrier deliveryAddress { __typename addressLine1 addressLine2 city state country zipcode } appointmentDetails { __typename appointmentId startDateTime endDateTime timeZone } vehicleVIN } }",
            "variables": {
                "orderId": order_id,
            },
        }
        response = self.raw_graphql_query(url=RIVIAN_GATEWAY_PATH, query=query, headers=headers)
        return response

    def transaction_status(self, order_id):
        headers = self.transaction_headers()
        query = {
            "operationName": "transactionStatus",
            "query": "query transactionStatus($orderId: ID!) { transactionStatus(orderId: $orderId) { titleAndReg { sourceStatus { status details } consumerStatus { displayOrder current complete locked inProgress notStarted error } } tradeIn { sourceStatus { status details } consumerStatus { displayOrder current complete locked inProgress notStarted error } } finance { sourceStatus { status details } consumerStatus { displayOrder current complete locked inProgress notStarted error } } delivery { sourceStatus { status details } consumerStatus { displayOrder current complete locked inProgress notStarted error } } insurance { sourceStatus { status details } consumerStatus { displayOrder current complete locked inProgress notStarted error } } documentUpload { sourceStatus { status details } consumerStatus { displayOrder current complete locked inProgress notStarted error } } contracts { sourceStatus { status details } consumerStatus { displayOrder current complete locked inProgress notStarted error } } payment { sourceStatus { status details } consumerStatus { displayOrder current complete locked inProgress notStarted error } } } }",
            "variables": {
                "orderId": order_id
            },
        }
        response = self.raw_graphql_query(url=RIVIAN_TRANSACTIONS_PATH, query=query, headers=headers)
        return response

    def finance_summary(self, order_id):
        headers = self.transaction_headers()
        query = {
            "operationName": "financeSummary",
            "query": "query financeSummary($orderId: ID!) { ...FinanceSummaryFragment } fragment FinanceSummaryFragment on Query { financeSummary(orderId: $orderId) { orderId status financeChoice { financeChoice institutionName paymentMethod trackingNumber preApprovedAmount loanOfficerName loanOfficerContact downPayment rate term rateAndTermSkipped } } }",
            "variables": {"orderId": order_id},
        }
        response = self.raw_graphql_query(url=RIVIAN_TRANSACTIONS_PATH, query=query, headers=headers)
        return response

    def order(self, order_id):
        headers = self.transaction_headers()
        query = {
            "operationName": "order",
            "query": "query order($id: String!) { order(id: $id) { vin state billingAddress { firstName lastName line1 line2 city state country postalCode } shippingAddress { firstName lastName line1 line2 city state country postalCode } orderCancelDate orderEmail currency locale storeId type subtotal discountTotal taxTotal feesTotal paidTotal remainingTotal outstandingBalance costAfterCredits total payments { id intent date method amount referenceNumber status card { last4 expiryDate brand } bank { bankName country last4 } transactionNotes } tradeIns { tradeInReferenceId amount } vehicle { vehicleId vin modelYear model make } items { id discounts { total items {  amount  title  code } } subtotal quantity title productId type unitPrice fees { items {  description  amount  code  type } total } taxes { items {  description  amount  code  rate  type } total } sku shippingAddress { firstName lastName line1 line2 city state country postalCode } configuration { ruleset {  meta {  rulesetId  storeId  country  vehicle  version  effectiveDate  currency  locale  availableLocales  }  defaults {  basePrice  initialSelection  }  groups  options  specs  rules } basePrice version options {  optionId  optionName  optionDetails {  name  attrs  price  visualExterior  visualInterior  hidden  disabled  required  }  groupId  groupName  groupDetails {  name  attrs  multiselect  required  options  }  price } } } }}",
            "variables": {"id": order_id},
        }
        response = self.raw_graphql_query(url=RIVIAN_ORDERS_PATH, query=query, headers=headers)
        return response

    def retail_orders(self):
        headers = self.transaction_headers()
        query = {
            "operationName": "searchOrders",
            "query": "query searchOrders($input: UserOrderSearchInput!) { searchOrders(input: $input) { total data { id type orderDate state fulfillmentSummaryStatus items { id title type sku __typename } __typename } __typename }}",
            "variables": {
                "input": {
                    "orderTypes": ["RETAIL"],
                    "orderStates": None,
                    "pageInfo": {
                        "from": 0,
                        "size": 5
                    },
                    "dateRange": None,
                    "sortFields": {
                        "orderDate": "DESC"
                    }
                }
            },
        }
        response = self.raw_graphql_query(url=RIVIAN_ORDERS_PATH, query=query, headers=headers)
        return response

    def get_order(self, order_id):
        headers = self.transaction_headers()
        query = {
            "operationName": "getOrder",
            "query": "query getOrder($orderId: String!) { order(id: $orderId) { id storeId userId orderDate orderCancelDate type state currency locale subtotal discountTotal taxTotal total shippingAddress { firstName lastName line1 line2 city state country postalCode __typename } payments { method currency status type card { last4 expiryDate brand __typename } __typename } items { id title type sku unitPrice quantity state productDetails { ... on ChildProduct { dimensionValues { name valueName localizedStrings __typename } __typename } __typename } __typename } fulfillmentSummaryStatus fulfillmentInfo { fulfillments { fulfillmentId fulfillmentStatus fulfillmentMethod fulfillmentVendor tracking { status carrier number url shipDate deliveredDate serviceType __typename } estimatedDeliveryWindow { startDate endDate __typename } items { orderItemId quantityFulfilled isPartialFulfillment __typename } __typename } pendingFulfillmentItems { orderItemId quantity __typename } __typename } __typename }}",
            "variables": {
                "orderId": order_id
            },
        }
        response = self.raw_graphql_query(url=RIVIAN_ORDERS_PATH, query=query, headers=headers)
        return response

    def payment_methods(self):
        headers = self.transaction_headers()
        query = {
            "operationName": "paymentMethods",
            "query": "query paymentMethods { paymentMethods { id type default card { lastFour brand expiration postalCode } } }",
            "variables": {},
        }
        response = self.raw_graphql_query(url=RIVIAN_ORDERS_PATH, query=query, headers=headers)
        return response

    def get_user_information(self):
        headers = self.gateway_headers()
        query = {
            "operationName": "getUserInfo",
            "query": "query getUserInfo { currentUser { __typename id firstName lastName email address { __typename country } vehicles { __typename id name owner roles vin vas { __typename vasVehicleId vehiclePublicKey } state createdAt updatedAt vehicle { __typename id vin modelYear make model expectedBuildDate plannedBuildDate expectedGeneralAssemblyStartDate actualGeneralAssemblyDate mobileConfiguration { __typename trimOption { __typename optionId optionName } exteriorColorOption { __typename optionId optionName } interiorColorOption { __typename optionId optionName } } vehicleState { __typename supportedFeatures { __typename name status } } otaEarlyAccessStatus } settings { __typename name { __typename value } } } enrolledPhones { __typename vas { __typename vasPhoneId publicKey } enrolled { __typename deviceType deviceName vehicleId identityId shortName } } pendingInvites { __typename id invitedByFirstName role status vehicleId vehicleModel email } } }",
            # "query": "query getUserInfo {currentUser {__typename id firstName lastName email address { __typename country } vehicles {id name owner roles vin vas {__typename vasVehicleId vehiclePublicKey } state createdAt updatedAt vehicle { __typename id vin modelYear make model expectedBuildDate plannedBuildDate expectedGeneralAssemblyStartDate actualGeneralAssemblyDate } } }}",
            "variables": None,
        }
        response = self.raw_graphql_query(url=RIVIAN_GATEWAY_PATH, query=query, headers=headers)
        return response

    def get_vehicle_state(self, vehicle_id, minimal=False):
        headers = self.gateway_headers()
        if minimal:
            query = "query GetVehicleState($vehicleID: String!) { vehicleState(id: $vehicleID) { " \
                    "cloudConnection { lastSync } " \
                    "powerState { value } " \
                    "driveMode { value } " \
                    "gearStatus { value } " \
                    "vehicleMileage { value } " \
                    "batteryLevel { value } " \
                    "distanceToEmpty { value } " \
                    "gnssLocation { latitude longitude } " \
                    "chargerStatus { value } " \
                    "chargerState { value } " \
                    "batteryLimit { value } " \
                    "timeToEndOfCharge { value } " \
                    "} }"
        else:
            query = "query GetVehicleState($vehicleID: String!) { " \
                    "vehicleState(id: $vehicleID) { __typename " \
                    "cloudConnection { __typename lastSync } " \
                    "gnssLocation { __typename latitude longitude timeStamp } " \
                    "alarmSoundStatus { __typename timeStamp value } " \
                    "timeToEndOfCharge { __typename timeStamp value } " \
                    "doorFrontLeftLocked { __typename timeStamp value } " \
                    "doorFrontLeftClosed { __typename timeStamp value } " \
                    "doorFrontRightLocked { __typename timeStamp value } " \
                    "doorFrontRightClosed { __typename timeStamp value } " \
                    "doorRearLeftLocked { __typename timeStamp value } " \
                    "doorRearLeftClosed { __typename timeStamp value } " \
                    "doorRearRightLocked { __typename timeStamp value } " \
                    "doorRearRightClosed { __typename timeStamp value } " \
                    "windowFrontLeftClosed { __typename timeStamp value } " \
                    "windowFrontRightClosed { __typename timeStamp value } " \
                    "windowRearLeftClosed { __typename timeStamp value } " \
                    "windowRearRightClosed { __typename timeStamp value } " \
                    "windowFrontLeftCalibrated { __typename timeStamp value } " \
                    "windowFrontRightCalibrated { __typename timeStamp value } " \
                    "windowRearLeftCalibrated { __typename timeStamp value } " \
                    "windowRearRightCalibrated { __typename timeStamp value } " \
                    "closureFrunkLocked { __typename timeStamp value } " \
                    "closureFrunkClosed { __typename timeStamp value } " \
                    "gearGuardLocked { __typename timeStamp value } " \
                    "closureLiftgateLocked { __typename timeStamp value } " \
                    "closureLiftgateClosed { __typename timeStamp value } " \
                    "windowRearLeftClosed { __typename timeStamp value } " \
                    "windowRearRightClosed { __typename timeStamp value } " \
                    "closureSideBinLeftLocked { __typename timeStamp value } " \
                    "closureSideBinLeftClosed { __typename timeStamp value } " \
                    "closureSideBinRightLocked { __typename timeStamp value } " \
                    "closureSideBinRightClosed { __typename timeStamp value } " \
                    "closureTailgateLocked { __typename timeStamp value } " \
                    "closureTailgateClosed { __typename timeStamp value } " \
                    "closureTonneauLocked { __typename timeStamp value } " \
                    "closureTonneauClosed { __typename timeStamp value } " \
                    "wiperFluidState { __typename timeStamp value } " \
                    "powerState { __typename timeStamp value } " \
                    "batteryHvThermalEventPropagation { __typename timeStamp value } " \
                    "vehicleMileage { __typename timeStamp value } " \
                    "brakeFluidLow { __typename timeStamp value } " \
                    "gearStatus { __typename timeStamp value } " \
                    "tirePressureStatusFrontLeft { __typename timeStamp value } " \
                    "tirePressureStatusValidFrontLeft { __typename timeStamp value } " \
                    "tirePressureStatusFrontRight { __typename timeStamp value } " \
                    "tirePressureStatusValidFrontRight { __typename timeStamp value } " \
                    "tirePressureStatusRearLeft { __typename timeStamp value } " \
                    "tirePressureStatusValidRearLeft { __typename timeStamp value } " \
                    "tirePressureStatusRearRight { __typename timeStamp value } " \
                    "tirePressureStatusValidRearRight { __typename timeStamp value } " \
                    "batteryLevel { __typename timeStamp value } " \
                    "chargerState { __typename timeStamp value } " \
                    "batteryLimit { __typename timeStamp value } " \
                    "remoteChargingAvailable { __typename timeStamp value } " \
                    "batteryHvThermalEvent { __typename timeStamp value } " \
                    "rangeThreshold { __typename timeStamp value } " \
                    "distanceToEmpty { __typename timeStamp value } " \
                    "otaAvailableVersion { __typename timeStamp value } " \
                    "otaAvailableVersionWeek { __typename timeStamp value } " \
                    "otaAvailableVersionYear { __typename timeStamp value } " \
                    "otaCurrentVersion { __typename timeStamp value } " \
                    " otaCurrentVersionNumber { __typename timeStamp value } " \
                    "otaCurrentVersionWeek { __typename timeStamp value } " \
                    "otaCurrentVersionYear { __typename timeStamp value } " \
                    "otaDownloadProgress { __typename timeStamp value } " \
                    "otaInstallDuration { __typename timeStamp value } " \
                    "otaInstallProgress { __typename timeStamp value } " \
                    "otaInstallReady { __typename timeStamp value } " \
                    "otaInstallTime { __typename timeStamp value } " \
                    "otaInstallType { __typename timeStamp value } " \
                    "otaStatus { __typename timeStamp value } " \
                    "otaCurrentStatus { __typename timeStamp value } " \
                    "cabinClimateInteriorTemperature { __typename timeStamp value } " \
                    "cabinPreconditioningStatus { __typename timeStamp value } " \
                    "cabinPreconditioningType { __typename timeStamp value } " \
                    "petModeStatus { __typename timeStamp value } " \
                    "petModeTemperatureStatus { __typename timeStamp value } " \
                    "cabinClimateDriverTemperature { __typename timeStamp value } " \
                    "gearGuardVideoStatus { __typename timeStamp value } " \
                    "gearGuardVideoMode { __typename timeStamp value } " \
                    "gearGuardVideoTermsAccepted { __typename timeStamp value } " \
                    "defrostDefogStatus { __typename timeStamp value } " \
                    "steeringWheelHeat { __typename timeStamp value } " \
                    "seatFrontLeftHeat { __typename timeStamp value } " \
                    "seatFrontRightHeat { __typename timeStamp value } " \
                    "seatRearLeftHeat { __typename timeStamp value } " \
                    "seatRearRightHeat { __typename timeStamp value } " \
                    "chargerStatus { __typename timeStamp value } " \
                    "seatFrontLeftVent { __typename timeStamp value } " \
                    "seatFrontRightVent { __typename timeStamp value } " \
                    "chargerDerateStatus { __typename timeStamp value } " \
                    "driveMode { __typename timeStamp value } " \
                    "} }"

        query = {
            "operationName": "GetVehicleState",
            "query": query,
            "variables": {
                'vehicleID': vehicle_id,
            },
        }
        response = self.raw_graphql_query(url=RIVIAN_GATEWAY_PATH, query=query, headers=headers)
        return response

    def get_vehicle_last_connection(self, vehicle_id):
        headers = self.gateway_headers()
        query = {
            "operationName": "GetVehicleLastConnection",
            "query": "query GetVehicleLastConnection($vehicleID: String!) { vehicleState(id: $vehicleID) { __typename cloudConnection { __typename lastSync } } }",
            "variables": {
                'vehicleID': vehicle_id,
            },
        }
        response = self.raw_graphql_query(url=RIVIAN_GATEWAY_PATH, query=query, headers=headers)
        return response

    def get_ota_details(self, vehicle_id):
        headers = self.gateway_headers()
        query = {
            "operationName": "GetVehicle",
            "query": "query GetVehicle($vehicleId: String!) { getVehicle(id: $vehicleId) { availableOTAUpdateDetails { url version locale } currentOTAUpdateDetails { url version locale } } }",
            "variables": {
                'vehicleId': vehicle_id,
            },
        }
        response = self.raw_graphql_query(url=RIVIAN_GATEWAY_PATH, query=query, headers=headers)
        return response

    def check_by_rivian_id(self):
        headers = self.transaction_headers()
        query = {
            "operationName": "CheckByRivianId",
            "query": "query CheckByRivianId { chargepoint { checkByRivianId } }",
            "variables": {},
        }
        response = self.raw_graphql_query(url=RIVIAN_CHARGING_PATH, query=query, headers=headers)
        return response

    def get_linked_email_for_rivian_id(self):
        headers = self.transaction_headers()
        query = {
            "operationName": "getLinkedEmailForRivianId",
            "query": "query getLinkedEmailForRivianId { chargepoint { getLinkedEmailForRivianId { email } } }",
            "variables": {},
        }
        response = self.raw_graphql_query(url=RIVIAN_CHARGING_PATH, query=query, headers=headers)
        return response

    def get_parameter_store_values(self):
        headers = self.transaction_headers()
        query = {
            "operationName": "getParameterStoreValues",
            "query": "query getParameterStoreValues($keys: [String!]!) { getParameterStoreValues(keys: $keys) { key value } }",
            "variables": {
                "keys": ["FF_ACCOUNT_ESTIMATED_DELIVERY_WINDOW_STATIC_MSG"]
            },
        }
        response = self.raw_graphql_query(url=RIVIAN_ORDERS_PATH, query=query, headers=headers)
        return response

    def get_vehicle(self, vehicle_id):
        headers = self.gateway_headers()
        query = {
            "operationName": "GetVehicle",
            "query": "query GetVehicle($getVehicleId: String) { getVehicle(id: $getVehicleId) { invitedUsers { __typename ... on ProvisionedUser { devices { type mappedIdentityId id hrid deviceName isPaired isEnabled } firstName lastName email roles userId } ... on UnprovisionedUser { email inviteId status } } } }",
            "variables": {
                "getVehicleId": vehicle_id
            },
        }
        response = self.raw_graphql_query(url=RIVIAN_GATEWAY_PATH, query=query, headers=headers)
        return response

    def get_registered_wallboxes(self):
        headers = self.gateway_headers()
        query = {
            "operationName": "getRegisteredWallboxes",
            "variables": {},
            "query": "query getRegisteredWallboxes { getRegisteredWallboxes { __typename wallboxId userId wifiId name linked latitude longitude chargingStatus power currentVoltage currentAmps softwareVersion model serialNumber maxPower maxVoltage maxAmps } }"
        }
        response = self.raw_graphql_query(url=RIVIAN_CHARGING_PATH, query=query, headers=headers)
        return response

    def get_provisioned_camp_speakers(self):
        headers = self.gateway_headers()
        query = {
            "operationName": "GetProvisionedCampSpeakers",
            "query": "query GetProvisionedCampSpeakers { currentUser { __typename vehicles { __typename id connectedProducts { __typename ... on CampSpeaker { serialNumber id } } } } }",
            "variables": {},
        }
        response = self.raw_graphql_query(url=RIVIAN_GATEWAY_PATH, query=query, headers=headers)
        return response

    def get_vehicle_images(self):
        headers = self.gateway_headers()
        query = {
            "operationName": "getVehicleImages",
            "query": "query getVehicleImages($extension: String!, $resolution: String!) { getVehicleOrderMobileImages(resolution: $resolution, extension: $extension) { __typename orderId url resolution size design placement } getVehicleMobileImages(resolution: $resolution, extension: $extension) { __typename vehicleId url resolution size design placement } }",
            "variables": {
                "extension": "webp",
                "resolution": "hdpi"
            },
        }
        response = self.raw_graphql_query(url=RIVIAN_GATEWAY_PATH, query=query, headers=headers)
        return response

    def user(self):
        headers = self.gateway_headers()
        query = {
            "operationName": "user",
            # "query": "query user { user { email { email } phone { formatted } firstName lastName addresses { id type line1 line2 city state country postalCode } newsletterSubscription smsSubscription registrationChannels2FA userId vehicles {id highestPriorityRole __typename } orderSnapshots(filterTypes: [PRE_ORDER, VEHICLE]) { ...OrderSnapshotsFragment __typename } __typename }} fragment OrderSnapshotsFragment on OrderSnapshot { id total paidTotal subtotal state configurationStatus currency orderDate type fulfillmentSummaryStatus items { id total unitPrice quantity productDetails { ... on VehicleProduct { sku store { country __typename } __typename } ... on StandaloneProduct { sku store { country __typename } __typename } ... on ChildProduct { sku store { country __typename } __typename } __typename } configuration { basePrice ruleset { meta { locale currency country vehicle version rulesetId effectiveDate __typename } groups rules specs options defaults { basePrice initialSelection __typename } __typename } options { optionId groupId price optionDetails { name attrs price visualExterior visualInterior __typename } __typename } __typename } __typename } __typename } } } ",
            "query": "query user { user { email { email } phone { formatted } firstName lastName addresses { id type line1 line2 city state country postalCode } newsletterSubscription smsSubscription registrationChannels2FA userId vehicles {id highestPriorityRole __typename } invites (filterStates: [PENDING]) {id inviteState vehicleModel vehicleId creatorFirstName} orderSnapshots(filterTypes: [PRE_ORDER, VEHICLE, RETAIL]) { ...OrderSnapshotsFragment } }} fragment OrderSnapshotsFragment on OrderSnapshot { id total paidTotal subtotal state configurationStatus currency orderDate type fulfillmentSummaryStatus }",
            "variables": {},
        }
        response = self.raw_graphql_query(url=RIVIAN_ORDERS_PATH, query=query, headers=headers)
        return response
