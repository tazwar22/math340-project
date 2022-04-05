import json
import sys
sys.path.append("..") # Adds higher directory to python modules path.
from config import * 
import pandas as pd
import geopy.distance as gd
from .tom_api import *
import time
from parking_spot import *

class Processor(object):
    '''
    Given an origin, dest, this class is responsible for finding all valid nearest-K parking spots
    '''
    def __init__(self, datapath, origin, dest, topK, stay_duration, parking_budget):
        self.datapath = datapath
        self.origin, self.dest = origin, dest
        self.topK = topK
        self.load_parking_meters_data()
        self.nearest = self.get_nearest()
        self.stay_duration = stay_duration
        self.p_budget = parking_budget

    def load_parking_meters_data(self):
        self.df = pd.read_csv(self.datapath, sep=';')
        print(self.df.shape)
        self.df = self.df.loc[self.df.METERHEAD.isin(['Single','Twin'])]
        if self.df.Geom.isna().any():
            self.df = self.df.loc[~self.df.Geom.isna()]
        self.df['latln'] = self.df['Geom'].apply(self.__get_latln)
        self.__merge_twins()
        self.df['dist_from_dest'] = self.df['latln'].apply(self.__compute_distances_to_dest)
        print(self.df.shape)

    def __get_latln(self, row):
        geom = json.loads(row)
        return geom['coordinates'][1], geom['coordinates'][0]

    def __compute_distances_to_dest(self, row):
        return gd.geodesic(self.dest, row).km

    def __merge_twins(self):
        #Find rest
        df_no_twins = self.df.loc[~(self.df.METERHEAD=='Twin')]
        df_no_twins.reset_index(inplace=True)
        #Find all twins
        twins = self.df.loc[self.df.METERHEAD=='Twin']
        twins.reset_index(inplace=True)
        #Make sure we are finding unique spots
        seen_twins = set()
        for i, row in twins.iterrows():
            #find the match
            pair = tuple(np.sort(np.where(twins.latln == row['latln'])[0]))
            if len(pair) != 2:
                continue
            if pair not in seen_twins:
                assert i == pair[0] #Current one is the first
                seen_twins.add(pair)
            else:
                continue
            # print(pair)
            check_columns = ['METERHEAD', 'Geo Local Area', 'latln']
            meter1, meter2 = twins.loc[pair[0]], twins.loc[pair[1]]
            for col in check_columns:
                v1, v2 = meter1[col], meter2[col]
                if not pd.isnull(v1) and not pd.isnull(v2):
                    assert v1 == v2
        print(f'Original #of separate twins: {len(twins)}')
        print(f'% retained after merging: {100*len(seen_twins)/len(twins)}')
    
        '''
        Use Twins
        for each pair, use first one's info to create a double spot
        '''
        merged_twins = []
        for pair in seen_twins:
            first, second = pair
            first_meter = twins.loc[first]
            merged_meter = first_meter
            merged_meter['METERID'] = (twins.loc[first]['METERID'], twins.loc[second]['METERID'])
            merged_twins.append(first_meter)
        merged_twins = pd.DataFrame(merged_twins)
        merged_twins.reset_index(inplace=True)

        self.df = pd.concat([df_no_twins, merged_twins])
        self.df.reset_index(inplace=True, drop=True)
        print(f'*** Data shape after merge: {self.df.shape} ***')

    def get_nearest(self):
        nearest_locs  = self.df.dist_from_dest.sort_values().index 
        nearest = self.df.loc[nearest_locs].head(n=self.topK)
        nearest.reset_index(inplace=True, drop=True)
        return nearest

    def form_variables_dict(self):
        ttapi = TomSearchAPI(API_KEY)
        variables = {}
        curr_i = 1

        #Iterate over all meters
        for i, meter in self.nearest.iterrows():
            print(f"IDX - {i}")
            '''
            Parse baisc info 
            '''
            location = meter.latln
            time_limit = int(meter['T_MF_9A_6P'].split(" ")[0])
            rate = float(meter['R_MF_9A_6P'].split("$")[1])
            print(f'Time limit: {time_limit} \t Rate: {rate}')
            if meter['METERHEAD'] == 'Single':
                spot = SingleSpot(location = {'lat':location[0], 'lon':location[1]},
                                geo_area = meter['Geo Local Area'], 
                                rate = rate, time_limit=time_limit)
            elif meter['METERHEAD'] == 'Twin':
                print("******************** Twin **********************")
                spot = DoubleSpot(location = {'lat':location[0], 'lon':location[1]},
                                geo_area = meter['Geo Local Area'], 
                                rate = rate, time_limit=time_limit)
            # print(spot.location)
            
            #FILTER OUT INVALID ONES
            parking_fee = self.stay_duration * spot.meter_rate
            if parking_fee > self.p_budget:
                print("Skipping due to fee constraint")
                continue
            if self.stay_duration > spot.time_limit:
                print("Skipping due to time limit")
                continue
                
            try:
                travel_et = ttapi.calculate_travel_time(HOME, spot.location, travel_mode='car')['travelTimeInSeconds']/60
                time.sleep(0.5)
                walk_time = round(ttapi.calculate_travel_time(spot.location, {'lat':self.dest[0], 'lon':self.dest[1]},
                                                            travel_mode='pedestrian')['travelTimeInSeconds']/60, 3)
                time.sleep(1.0)
                print(f'*** Travel time: {travel_et} ***')
                expected_status = spot.get_expected_state(travel_et)
                print(f'~~~ Parking Status: {expected_status} ~~~')

                if expected_status < 1:
                    print("SKIPPING! No spot will be available")
                    continue

                curr_key = f'y_{curr_i}'
                variables[curr_key] = {}

                '''
                Coefficients
                '''
                variables[curr_key][f'b_{curr_i}'] = 1.0 

                '''
                CONSTRAINTS DICT
                '''
                constraint_coeffs = {}
                
                constraint_coeffs['parking_fee'] = parking_fee
                constraint_coeffs['savings'] = self.p_budget - parking_fee
                constraint_coeffs['expected_avail'] = expected_status
                constraint_coeffs['et_next_out'] = spot.get_time_between_departures()
                constraint_coeffs['et_next_in'] = spot.get_time_between_arrivals()
                constraint_coeffs['walk_time'] = walk_time
                constraint_coeffs['travel_et'] = travel_et

                variables[curr_key]['constraint_coeffs'] = constraint_coeffs

                #Extra
                variables[curr_key]['meterid'] = meter.METERID
                variables[curr_key]['latln'] = meter.latln

                print(variables[f'y_{curr_i}'])
                curr_i += 1
            except:
                print(f"Error with {i}")
                print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        return variables