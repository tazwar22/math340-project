import pulp
from pulp import *
import numpy as np
import pandas as pd

class Solver(object):

    '''
    @params: variables_dict should have the format:
    {'y_i': 
            {
                'b_i': 1.0,
                'constraint_coeffs':
                        {'parking_fee': value,
                        'savings':value,
                        'expected_avail': value,
                        'et_next_out': value,
                        'et_next_in': value,
                        'walk_time': value,
                        'travel_et': value
                        }
            }
    }
    '''
    def __init__(self, variables_dict):
        self.variables= variables_dict
        self.model = LpProblem("ParkingOptimizer", LpMinimize)
        #Decision variables
        self.var_idx = list(range(1, len(self.variables)+1))
        self.lp_vars = LpVariable.dicts('y', self.var_idx, lowBound=0, upBound=1)
        #Objective function!
        self.model += lpSum([self.variables[str(self.lp_vars[vi])][f'b_{vi}'] * self.lp_vars[vi] for vi in self.var_idx])
        self.__add_constraints()
        self.soln_status = None
        print(self.model)
    
    def solve_LP(self):
        #SOLVE
        self.model.solve()

        print("*"*30 + "STATUS" + "*"*30)
        print(f'Solution status: {LpStatus[self.model.status]}')
        self.soln_status = LpStatus[self.model.status]
        print("~~~ Values ~~~")
        for variable in self.model.variables():
                print(variable.name, " =", variable.varValue)
        print("*"*30 + "***" + "*"*30)

        if self.soln_status != 'Optimal':
            raise ValueError(f'Issue! Solution: {self.soln_status}')
    
    def get_soln_summary(self):
        optimal_weights = {}
        for variable in self.model.variables():
            optimal_weights[str(variable.name)] = variable.varValue
        
        cols = ['var','optimal_weight' ,'parking_fee', 'expected_avail','travel_et', 'walk_time', 'et_next_out', 'et_next_in']
        res = []
        for i in self.var_idx:
            res.append([f'y_{i}',optimal_weights[f'y_{i}'] , self.variables[f'y_{i}']['constraint_coeffs']['parking_fee'],
                                self.variables[f'y_{i}']['constraint_coeffs']['expected_avail'],
                                self.variables[f'y_{i}']['constraint_coeffs']['travel_et'],
                                self.variables[f'y_{i}']['constraint_coeffs']['walk_time'],
                                self. variables[f'y_{i}']['constraint_coeffs']['et_next_out'],
                                self.variables[f'y_{i}']['constraint_coeffs']['et_next_in']])

        res = pd.DataFrame(res, columns=cols)
        res.sort_values(by=['optimal_weight','travel_et', 'expected_avail'],
                        ascending = [False, True, False], inplace=True)
        return res


    def __add_constraints(self):
        '''
        Spot availability
        '''
        self.model += lpSum([self.variables[str(self.lp_vars[v_i])]['constraint_coeffs'][f'expected_avail'] * self.lp_vars[v_i]
                                 for v_i in self.var_idx]) >= np.mean([self.variables[str(self.lp_vars[v_i])]['constraint_coeffs'][f'expected_avail'] 
                                 for v_i in self.var_idx])
            
        '''
        Savings (according to given budget)
        '''
        self.model += lpSum([1 * self.variables[str(self.lp_vars[v_i])]['constraint_coeffs'][f'savings'] * self.lp_vars[v_i]
                                for v_i in self.var_idx]) >= np.mean([self.variables[str(self.lp_vars[v_i])]['constraint_coeffs'][f'savings'] 
                                for v_i in self.var_idx])

        '''
        Travel times
        '''
        self.model += lpSum([-1 * self.variables[str(self.lp_vars[v_i])]['constraint_coeffs'][f'travel_et'] * self.lp_vars[v_i]
                                 for v_i in self.var_idx]) >= -np.mean([self.variables[str(self.lp_vars[v_i])]['constraint_coeffs'][f'travel_et'] 
                                 for v_i in self.var_idx])

        self.model += lpSum([-1 * self.variables[str(self.lp_vars[v_i])]['constraint_coeffs'][f'walk_time'] * self.lp_vars[v_i] 
                                for v_i in self.var_idx]) >= -np.mean([self.variables[str(self.lp_vars[v_i])]['constraint_coeffs'][f'walk_time'] 
                                for v_i in self.var_idx])

        '''
        Time until next spot opens up
        '''
        self.model += lpSum([-1 * self.variables[str(self.lp_vars[v_i])]['constraint_coeffs'][f'et_next_out'] * self.lp_vars[v_i] 
                                for v_i in self.var_idx]) >= -np.mean([self.variables[str(self.lp_vars[v_i])]['constraint_coeffs'][f'et_next_out']
                                for v_i in self.var_idx])

        self.model += lpSum([1 * self.lp_vars[v_i] 
                            for v_i in self.var_idx]) == 1