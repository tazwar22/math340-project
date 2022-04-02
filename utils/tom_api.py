import requests

class TomSearchAPI(object):
    def __init__(self, API_KEY):
        self.baseURL = "api.tomtom.com"
        self.versionNumber = str(2)
        self.ext = 'json'
        self.typeahead = 'false'
        self.country='CAN'
        self.API_KEY = API_KEY
        
    def find_location(self, query):
        '''
        https://developer.tomtom.com/search-api/documentation/search-service/fuzzy-search
        This function finds a place by name
        @param: query - the name of a loctaion
        @returns: location + more
        '''
        url = f'https://{self.baseURL}/search/{self.versionNumber}/search/{query}.{self.ext}?key={self.API_KEY}&typeahead={self.typeahead}&countrySet={self.country}'
        res = requests.get(url)
        if res:
            res = res.json()
            top = res['results'][0]
            # print(top)
            street_address = top['address']['freeformAddress']
            location = top['position']
            ret = {'poi_name':top['poi']['name'], 'address':street_address, 'location':location}
            return ret
        else:
            print("Something went wrong")
            return None
        
    def calculate_travel_time(self, origin, dest, travel_mode):
        '''
        https://developer.tomtom.com/routing-api/documentation/routing/calculate-route
        @params: origin, dest - Two Python dicts with lat/lon
        @params: travel_mode - can specify 'car' or 'pedestrian'
        @returns: travelTime
        '''
        lat, lon = origin['lat'], origin['lon']
        lat2, lon2 = dest['lat'], dest['lon']
        journey = f"{lat},{lon}:{lat2},{lon2}"
        url = f"https://{self.baseURL}/routing/1/calculateRoute/{journey}/json?key={self.API_KEY}&travelMode={travel_mode}"
        res = requests.get(url).json()
        best_route = res['routes'][0]
        summary = best_route['summary']
        return summary

    