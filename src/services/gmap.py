from typing import Tuple, Optional
from math import radians, cos, sin, asin, sqrt
import googlemaps
from datetime import datetime
from os import environ

KEY = environ["GOOGLE_MAPS_API_KEY"]
gmaps = googlemaps.Client(key=KEY)


def get_address(point: Tuple[float, float]) -> Optional[str]:
    result = gmaps.reverse_geocode(point, language='iw')
    if len(result) == 0:
        return None
    return result[0]['formatted_address']


def get_point(address: str) -> Optional[Tuple[float, float]]:
    result = gmaps.geocode(address, language='iw')
    if len(result) == 0:
        return None
    a = result[0]['geometry']['location']
    return a['lat'], a['lng']


def get_distance(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
    # GeekForGeeks code - https://www.geeksforgeeks.org/program-distance-two-points-earth/
    # The math module contains a function named
    # radians which converts from degrees to radians.
    lon1 = radians(point1[1])
    lon2 = radians(point2[1])
    lat1 = radians(point1[0])
    lat2 = radians(point2[0])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2

    c = 2 * asin(sqrt(a))

    # Radius of earth in kilometers. Use 3956 for miles
    r = 6371

    # calculate the result
    print(c * r)
    return c * r
