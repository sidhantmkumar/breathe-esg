import json
import math
from decimal import Decimal

AIRPORT_COORDS = {
    'BOM': (19.0896, 72.8656), 'DEL': (28.5562, 77.1000),
    'LHR': (51.4700, -0.4543), 'JFK': (40.6413, -73.7781),
    'DXB': (25.2532, 55.3657), 'SIN': (1.3644, 103.9915),
    'HKG': (22.3080, 113.9185), 'CDG': (49.0097, 2.5479),
    'FRA': (50.0379, 8.5622), 'SYD': (-33.9399, 151.1753),
    'LAX': (33.9425, -118.4081), 'ORD': (41.9742, -87.9073),
    'NRT': (35.7720, 140.3929), 'ICN': (37.4602, 126.4407),
    'AMS': (52.3086, 4.7639), 'MAD': (40.4936, -3.5668),
    'BCN': (41.2974, 2.0833), 'BLR': (13.1986, 77.7066),
    'HYD': (17.2313, 78.4298), 'MAA': (12.9941, 80.1709),
}

CABIN_FACTORS = {
    'economy': Decimal('0.19085'),
    'business': Decimal('0.38170'),
    'first': Decimal('0.76340'),
}

HOTEL_CO2E_PER_NIGHT = Decimal('20.8')
TAXI_CO2E_PER_KM = Decimal('0.14930')
RAIL_CO2E_PER_KM = Decimal('0.03549')

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def parse_travel(file_content):
    data = json.loads(file_content)
    if isinstance(data, dict):
        trips = data.get('trips', [data])
    else:
        trips = data

    rows = []
    for trip in trips:
        for flight in trip.get('flights', []):
            origin = flight.get('departure_airport', '').upper()
            dest = flight.get('arrival_airport', '').upper()
            cabin = flight.get('cabin_class', 'economy').lower()
            date_str = flight.get('travel_date')

            if origin in AIRPORT_COORDS and dest in AIRPORT_COORDS:
                lat1, lon1 = AIRPORT_COORDS[origin]
                lat2, lon2 = AIRPORT_COORDS[dest]
                dist_km = Decimal(str(haversine(lat1, lon1, lat2, lon2)))
            else:
                dist_km = Decimal('800')

            factor = CABIN_FACTORS.get(cabin, CABIN_FACTORS['economy'])
            co2e = dist_km * factor * Decimal('1.891')

            rows.append({
                'scope': 3,
                'category': 'air_travel',
                'raw_value': dist_km,
                'raw_unit': 'km',
                'normalized_co2e': co2e,
                'period_start': date_str,
                'period_end': date_str,
                'raw_payload': flight,
            })

        for hotel in trip.get('hotels', []):
            nights = Decimal(str(hotel.get('nights', 1)))
            co2e = nights * HOTEL_CO2E_PER_NIGHT
            rows.append({
                'scope': 3,
                'category': 'hotel_stay',
                'raw_value': nights,
                'raw_unit': 'nights',
                'normalized_co2e': co2e,
                'period_start': hotel.get('check_in'),
                'period_end': hotel.get('check_out'),
                'raw_payload': hotel,
            })

        for ground in trip.get('ground_transport', []):
            dist = Decimal(str(ground.get('distance_km', 0)))
            mode = ground.get('mode', 'taxi').lower()
            factor = RAIL_CO2E_PER_KM if 'rail' in mode else TAXI_CO2E_PER_KM
            co2e = dist * factor
            rows.append({
                'scope': 3,
                'category': 'ground_transport',
                'raw_value': dist,
                'raw_unit': 'km',
                'normalized_co2e': co2e,
                'period_start': ground.get('date'),
                'period_end': ground.get('date'),
                'raw_payload': ground,
            })

    return rows