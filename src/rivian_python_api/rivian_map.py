import os
import json
import math
import polyline
import plotly.graph_objects as go
from geopy.geocoders import Nominatim

# Initialize Nominatim geocoder
geolocator = Nominatim(user_agent="rivian_cli")

def decode_and_map(planned_trip):
    # route response is a json object embedded as a string so parse it out
    route_response = json.loads(planned_trip['data']['planTrip']['routes'][0]['routeResponse'])

    # decode polyline from geometry 
    route_path = polyline.decode(route_response['geometry'], 6)

    show_map(route_path, planned_trip['data']['planTrip']['routes'][0]['waypoints'])

def show_map(route, waypoints=[]):
    MAPBOX_API_KEY = os.getenv('MAPBOX_API_KEY')
    
    if MAPBOX_API_KEY is None:
        print("Missing MAPBOX_API_KEY, please set .env")
        return

    fig = go.Figure()
    filtered_waypoints = []

    # Filter waypoints to only include objects with waypointType equal to 'DC_CHARGE_STATION'
    if waypoints is not None:
        filtered_waypoints = list(filter(lambda waypoint: waypoint['waypointType'] == 'DC_CHARGE_STATION', waypoints))

    fig.add_trace(go.Scattermapbox(
        mode = "lines",
        hoverinfo = "none",
        lon = [wp[1] for wp in route],
        lat = [wp[0] for wp in route],
        marker = {'size': 10},
        name='Route'
    ))

    fig.add_trace(go.Scattermapbox(
        mode = "markers",
        lat = [wp['latitude'] for wp in filtered_waypoints],
        lon = [wp['longitude'] for wp in filtered_waypoints],
        customdata=[charger_hover_info(wp) for wp in filtered_waypoints],
        hovertemplate='%{customdata}',
        marker = {'size': 20, 'color': 'green'},
        name='Charge Stops'
    ))

    if waypoints is not None:
        fig.add_trace(go.Scattermapbox(
            mode = "markers",
            lat = [waypoints[-1]['latitude']],
            lon = [waypoints[-1]['longitude']],
            customdata=[destination_hover_info(waypoints[-1])],
            hovertemplate='%{customdata}',
            marker = {'size': 20},
            name='Destination'
        ))

    # Find the bounding box of the polyline
    min_lat, max_lat = min(lat for lat, lng in route), max(lat for lat, lng in route)
    min_lng, max_lng = min(lng for lat, lng in route), max(lng for lat, lng in route)

    # # Calculate the center of the bounding box
    center_lat = (min_lat + max_lat) / 2
    center_lng = (min_lng + max_lng) / 2

    fig.update_layout(
    mapbox = {
        'accesstoken': MAPBOX_API_KEY,
        'center': {'lon': center_lng, 'lat': center_lat},
        # this is pretty arbitrary 
        'zoom': 6 - 0.3 * ((max_lng - min_lng) / (max_lat - min_lat))
        })

    # Show the map
    fig.show()

def charger_hover_info(charger):
    info = (f"<b> {charger['name']}</b><br><br>"
            f"Charge for {math.ceil(charger['chargeDuration']/60)} minutes:<br>"
            f"{str(math.floor(charger['arrivalSOC']))}% → {str(math.floor(charger['departureSOC']))}%<br>"
            )
    return info

def destination_hover_info(dest):
    info = (f"<b> Destination</b><br><br>"
            f"Arrival SOC: {str(math.floor(dest['arrivalSOC']))}%"
            )
    return info

# Define function to extract latitude and longitude from input field
def extract_lat_long(input_field):
    location = geolocator.geocode(input_field)
    lat = location.latitude
    long = location.longitude
    return lat, long