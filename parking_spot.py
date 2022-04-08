from scipy.stats import poisson, expon
import numpy as np
# np.random.seed(100)

'''
A spot can be - single
Can have subclasses - Single, Twin, Station (5)
- https://towardsdatascience.com/the-poisson-distribution-and-poisson-process-explained-4e2cb17d459
'''
class ParkingSpot(object):
    '''
    RATE - minute basis
    '''
    def __init__(self, location, geo_area, rate, time_limit):
        self.lat, self.lon = location['lat'], location['lon']
        self.location = location
        self.geo_area = geo_area
        
        self.meter_rate = rate/60 #Adjust for hourly rate
        self.time_limit = time_limit*60 #Adjust for hour
        
        self.capacity = None #Might change depending on #stations (twin or not)
        #Rate of departure/arrival of cars (per minute)
        self.lam_depart = None
        self.lam_arrive = None
    
    def form_models(self):
        assert self.lam_depart 
        assert self.lam_arrive
        self.arrival_model = poisson(self.lam_arrive)
        self.departure_model = poisson(self.lam_depart)
    
    def get_n_departures(self, num_minutes):
        return int(self.lam_depart * num_minutes)
    
    def get_n_arrivals(self, num_minutes):
        return  int(self.lam_arrive * num_minutes)
    
    def get_expected_state(self, num_minutes):
        n_out = self.get_n_departures(num_minutes)
        n_in = self.get_n_arrivals(num_minutes)
        print(f'out: {n_out} - in: {n_in}')
        flow = n_out - n_in #Positive flow means more cars out than in
        # return  min(flow, self.capacity) if flow > 0 else 0
        return self.capacity + flow if flow > 0 else 0
    
    def get_time_between_arrivals(self):
        return float(expon.stats(scale=1/self.lam_arrive, moments='m'))
    
    def get_time_between_departures(self):
        return float(expon.stats(scale=1/self.lam_depart, moments='m'))
        
    
class SingleSpot(ParkingSpot):
    def __init__(self, location, geo_area, rate, time_limit):
        super().__init__(location, geo_area, rate, time_limit)
        self.capacity = 1
        
        self.lam_depart = 1/np.random.randint(8, 20+1) # 1 car leaves every A...X minutes
        self.lam_arrive = 1/np.random.randint(20, 25+1) # 1 car arrives every A...X minutes
        self.form_models()

class DoubleSpot(ParkingSpot):
    def __init__(self, location, geo_area, rate, time_limit):
        super().__init__(location, geo_area, rate, time_limit)
        self.capacity = 2
        
        self.lam_depart = 1/np.random.randint(8, 15+1) # 1 car leaves every A...X minutes
        self.lam_arrive = 1/np.random.randint(20, 25+1) # 1 car arrives every A...X minutes
        self.form_models()