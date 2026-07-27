#!/usr/bin/env python
# coding: utf-8
# %%
#import the library pulp as p
import pulp as p
from pulp import *
import pandas as pd
import numpy as np
import math
from scipy.stats import norm
import random
import scipy.stats as si


# %%

def BS_call(stock, K, t, T, sigma, r):
    """
    Vectorised Black–Scholes call price.

    Parameters
    ----------
    stock : float                      # spot S_0   (can also be array-shaped)
    K     : float or ndarray           # strikes
    t     : float                      # valuation time
    T     : float                      # maturity
    sigma : float
    r     : float
    """
    K      = np.asarray(K, dtype=float)              # safe cast
    tau    = np.maximum(T - t, 0.0)                  # years to expiry
    out    = np.empty_like(K, dtype=float)           # allocate result array

    # Case 1: K > 0  (standard call)
    mask_pos = K > 0
    if tau > 0:
        d1 = (np.log(stock / K[mask_pos]) +
               (r + 0.5 * sigma**2) * tau) / (sigma * np.sqrt(tau))
        d2 = d1 - sigma * np.sqrt(tau)
        out[mask_pos] = (stock * norm.cdf(d1) -
                         K[mask_pos] * np.exp(-r * tau) * norm.cdf(d2))
    else:                                           # tau == 0
        out[mask_pos] = np.maximum(stock - K[mask_pos], 0.0)

    # Case 2: K == 0  → option worth the stock
    mask_zero = K == 0
    out[mask_zero] = stock

    # Case 3: K < 0  → pathological, set to 0
    mask_neg = K < 0
    out[mask_neg] = 0.0

    return out


# %%


# #function to get European call price
# def BS_call(stock,K,t,T,sigma,r):
#     if K > 0:
#         tau = T-t
#         if tau == 0:
#             call = np.maximum(stock-K,0)
#         else: 
#             d1 = (np.log(stock/K) + (r + 0.5 * ( sigma **2)) * tau)/ (sigma * np.sqrt(tau))
#             d2 = d1 - sigma * np.sqrt(tau)
#             call = stock * norm.cdf(d1) - K * np.exp(-r * tau) * norm.cdf(d2)
#     if K == 0:
#         call = stock
#     if K < 0:
#         call = 0
#     return call



# %%
def MJD_call(S0,strike,t,T,sigma,r,lmda,g,mu_j,sigma_j,div):
    if strike > 0:
        tau = T-t
        if tau == 0:
            callT =np.maximum(S0-strike,0)
        else:
            sum_n = 0
            for n in range(100):
                r_n = r - lmda * g + (n * ( mu_j +  0.5 *  sigma_j **2))/tau
                sigma_n = np.sqrt(sigma **2 + (n *  sigma_j **2)/tau )
                d_1n = np.divide(np.log(S0/strike) + (r_n -div + 0.5 * (sigma_n **2)) * tau,\
                         sigma_n * np.sqrt(tau))
                Pr_n = np.exp(-lmda * (tau)) * np.divide( ( lmda * tau)**n, math.factorial(n) )
                sum_n += Pr_n * (S0 * np.exp((r_n - div) * tau) * si.norm.cdf(d_1n) - \
                         strike * si.norm.cdf(d_1n - sigma_n * np.sqrt(tau)))
            callT= np.exp(-r * tau) * sum_n
    if strike == 0:
        callT = S0
    if strike < 0:
        callT = 0
    return callT


# %%
#non-uniform grid concentrated around K

import numpy as np
import matplotlib.pyplot as plt

def create_concentrated_grid(a, b, K, n_points, concentration_factor):
    """
    Generate a grid concentrated near K and sparser as we move away from K, within [a, b].

    Parameters:
    a (float): Start of the interval.
    b (float): End of the interval.
    K (float): Point to concentrate the grid around.
    n_points (int): Number of grid points.
    concentration_factor (float): Higher values mean more concentration near K.

    Returns:
    np.ndarray: A grid concentrated near K.
    """
    if not (a < K < b):
        raise ValueError("Ensure that a < K < b")

    # Generate a uniform grid on [0, 1]
    uniform_grid = np.linspace(0, 1, n_points)

    # Apply a non-linear transformation
    transformed_grid = np.sinh(concentration_factor * (uniform_grid - 0.5)) / np.sinh(concentration_factor / 2)

    # Map to [a, b] while concentrating around K
    grid = (transformed_grid + 1) / 2 * (b - a) + a

    # Shift the grid so it's centered around K
    midpoint = (a + b) / 2
    grid += (K - midpoint)

    # Clip to ensure the grid stays within [a, b]
    grid = np.clip(grid, a, b)
    
    grid = np.append(grid,[0])
    # Remove duplicate values
    unique_grid = np.unique(grid)

    return unique_grid
   




# %%


def interpolated_line(stock,K2,T,sigma,r,R):
    f=  ((K2[-1]-R)/(K2[-1]-K2[-2])) * BS_call(stock,K2[-2],0,T,sigma,r) \
          + ((R-K2[-2])/(K2[-1]-K2[-2])) * BS_call(stock,K2[-1],0,T,sigma,r)
    return f


# %%
def interpolated_line_MJD(stock,K2,T,sigma,r,R,lmda,g,mu_j,sigma_j,div):
    f=  ((K2[-1]-R)/(K2[-1]-K2[-2])) * MJD_call(stock,K2[-2],0,T,sigma,r,lmda,g,mu_j,sigma_j,div) \
          + ((R-K2[-2])/(K2[-1]-K2[-2])) *  MJD_call(stock,K2[-1],0,T,sigma,r,lmda,g,mu_j,sigma_j,div)
    return f


# %%


#we need R in [K2[N-1],infty] such that ((K2[N-1]-R)/(K2[N-1]-K2[N-2]))*C_{\nu}(K2[N-2]) + ((R-K2[N-2])/(K2[N-1]-K2[N-2]))*C_{\nu}(K2[N-1])=0

def find_first_x_close_to_zero(f, a, b, epsilon, step,stock,K2,T,sigma,r):
    """
    Find the first value of x in the range [a, b] such that f(x) is close to zero.

    Parameters:
    f (function): The function to evaluate.
    a (float): Start of the range.
    b (float): End of the range.
    epsilon (float): Threshold for f(x) to be considered close to zero.
    step (float): Step size for incrementing x.

    Returns:
    float: The first value of x such that |f(x)| < epsilon, or None if not found.
    """
    x = a
    while x <= b:
        if abs(f(stock,K2,T,sigma,r,x)) < epsilon:
            return x
        x += step
    return None  # Return None if no such x is found in the range




# %%


def append_numbers(array_to_append,a, b, l):
    """
    Append numbers to an array K1 based on the conditions:
    1. If b-a <= l, append b to K1.
    2. If b-a > l, append evenly spaced numbers a+l, a+2l, ..., a+nl such that b-(a+nl) < l.
    
    Parameters:
    a (float): Starting number.
    b (float): Ending number.
    l (float): Spacing between the numbers.
    
    Returns:
    list: The resulting list K1.
    """
    K1 =  array_to_append # Initialize the list
    print(f"spacing: {l}")
    
    if (b - a <= l) and (b != a):
        K1 = np.append(K1, b)  # Case 1: Append b if the difference is <= l
    else:
        # Case 2: Generate evenly spaced numbers
        n = int((b - a) / l)  # Compute the number of steps
        K1 = np.append(K1, [a + i * l for i in range(1, n + 1)])  # Append a+l, a+2l, ..., a+nl
        if (b - (a + n * l) < l) and b != (a + n * l):
            K1 = np.append(K1, b)   # Append b if it satisfies the condition
    
    return K1


# %%

def find_zero(BS_call,stock,K2,T,sigma,r):
    """
    Find the first value of x in the range [a, b] such that f(x) is close to zero.

    Parameters:
    f (function): The function to evaluate.
    a (float): Start of the range.
    b (float): End of the range.
    epsilon (float): Threshold for f(x) to be considered close to zero.
    step (float): Step size for incrementing x.

    Returns:
    float: The first value of x such that |f(x)| < epsilon, or None if not found.
    """
    num = K2[-1]* BS_call(stock,K2[-2],0,T,sigma,r) -K2[-2]* BS_call(stock,K2[-1],0,T,sigma,r)
    den = BS_call(stock,K2[-2],0,T,sigma,r) -BS_call(stock,K2[-1],0,T,sigma,r) 
    return num/den



# %%
def find_zero_MJD(MJD_call,stock,K2,T,sigma,r,lmda,g,mu_j,sigma_j,div):
    """
    Find the first value of x in the range [a, b] such that f(x) is close to zero.

    Parameters:
    f (function): The function to evaluate.
    a (float): Start of the range.
    b (float): End of the range.
    epsilon (float): Threshold for f(x) to be considered close to zero.
    step (float): Step size for incrementing x.

    Returns:
    float: The first value of x such that |f(x)| < epsilon, or None if not found.
    """
    num = K2[-1]* MJD_call(stock,K2[-2],0,T,sigma,r,lmda,g,mu_j,sigma_j,div) -K2[-2]* MJD_call(stock,K2[-1],0,T,sigma,r,lmda,g,mu_j,sigma_j,div)
    den = MJD_call(stock,K2[-2],0,T,sigma,r,lmda,g,mu_j,sigma_j,div) -MJD_call(stock,K2[-1],0,T,sigma,r,lmda,g,mu_j,sigma_j,div) 
    return num/den

# %%


#defining call prices using interpolation

def call_interpolated(stock,K2,T,sigma,r,point):
    f=  ((K2[-1]-point)/(K2[-1]-K2[-2])) * BS_call(stock,K2[-2],0,T,sigma,r) \
          + ((point-K2[-2])/(K2[-1]-K2[-2])) * BS_call(stock,K2[-1],0,T,sigma,r)
    #if f is non-negative keep that else put it to be zero to ensure call prices are non-negative
    return max(f,0)


# %%
#defining call prices using interpolation

def call_interpolated_MJD(stock,K2,T,sigma,r,lmda,g,mu_j,sigma_j,div,point):
    f=  ((K2[-1]-point)/(K2[-1]-K2[-2])) * MJD_call(stock,K2[-2],0,T,sigma,r,lmda,g,mu_j,sigma_j,div) \
          + ((point-K2[-2])/(K2[-1]-K2[-2])) * MJD_call(stock,K2[-1],0,T,sigma,r,lmda,g,mu_j,sigma_j,div)
    #if f is non-negative keep that else put it to be zero to ensure call prices are non-negative
    return max(f,0)

# %%


#storing all the call prices

def call_prices(stock,disc_points_old,disc_points_new,T,sigma,r):
    #length of old truncation range
    length_old = len(disc_points_old)
    
    #length of new truncation range
    length_new = len(disc_points_new)
    
    
    call_price = np.zeros(length_new)
    
    if length_old == length_new:
        #defining call prices using Black-Scholes
        call_price = [BS_call(stock,disc_points_old[i],0,T,sigma,r) for i in range(length_old)]
    if length_old < length_new:
        #defining call prices in the earlier range using Black-Scholes
        call_price_old = [BS_call(stock,disc_points_old[i],0,T,sigma,r) for i in range(length_old)]
        
        #define the new call prices using interpolation
        call_price_new = [call_interpolated(stock,disc_points_old,T,sigma,r,disc_points_new[i])\
                          for i in range(length_old,length_new)]
        call_price = np.append(call_price_old,call_price_new)
    
    #last call price has to be zero
    call_price[-1] = 0
    return call_price


# %%
#storing all the call prices

def call_prices_new(stock,disc_points_old,disc_points_new,T,sigma,r):
    #length of old truncation range
    length_old = len(disc_points_old)
    
    #length of new truncation range
    length_new = len(disc_points_new)
    
    
    call_price = np.zeros(length_new)
    
    if length_old == length_new:
        #defining call prices using Black-Scholes
#         call_price = [BS_call(stock,disc_points_old[i],0,T,sigma,r) for i in range(length_old)]
        call_price = BS_call(stock,disc_points_old[:length_old],0,T,sigma,r) 
    if length_old < length_new:
        #defining call prices in the earlier range using Black-Scholes
#         call_price_old = [BS_call(stock,disc_points_old[i],0,T,sigma,r) for i in range(length_old)]
        call_price_old = BS_call(stock,disc_points_old[:length_old],0,T,sigma,r) 
        
        #define the new call prices using interpolation
#         call_price_new = [call_interpolated(stock,disc_points_old,T,sigma,r,disc_points_new[i])\
#                           for i in range(length_old,length_new)]
        call_price = np.append(call_price_old,0)
    
    #last call price has to be zero
    call_price[-1] = 0
    return call_price

# %%


#storing all the call prices

def call_prices_MJD(stock,disc_points_old,disc_points_new,T,sigma,r,lmda,g,mu_j,sigma_j,div):
    #length of old truncation range
    length_old = len(disc_points_old)
    
    #length of new truncation range
    length_new = len(disc_points_new)
    
    
    call_price = np.zeros(length_new)
    
    if length_old == length_new:
        #defining call prices using Black-Scholes
        call_price = [MJD_call(stock,disc_points_old[i],0,T,sigma,r,lmda,g,mu_j,sigma_j,div) for i in range(length_old)]
    if length_old < length_new:
        #defining call prices in the earlier range using Black-Scholes
        call_price_old = [MJD_call(stock,disc_points_old[i],0,T,sigma,r,lmda,g,mu_j,sigma_j,div) for i in range(length_old)]
        
        #define the new call prices using interpolation
        call_price_new = [call_interpolated_MJD(stock,disc_points_old,T,sigma,r,lmda,g,mu_j,sigma_j,div,disc_points_new[i])\
                          for i in range(length_old,length_new)]
        call_price = np.append(call_price_old,call_price_new)
    
    #last call price has to be zero
    call_price[-1] = 0
    return call_price

# %%


#storing all the call prices

def call_prices_new_MJD(stock,disc_points_old,disc_points_new,T,sigma,r,lmda,g,mu_j,sigma_j,div):
    #length of old truncation range
    length_old = len(disc_points_old)
    
    #length of new truncation range
    length_new = len(disc_points_new)
    
    
    call_price = np.zeros(length_new)
    
    if length_old == length_new:
        #defining call prices using Black-Scholes
        call_price = [MJD_call(stock,disc_points_old[i],0,T,sigma,r,lmda,g,mu_j,sigma_j,div)
                      for i in range(length_old)]
    if length_old < length_new:
        #defining call prices in the earlier range using Black-Scholes
        call_price_old = [MJD_call(stock,disc_points_old[i],0,T,sigma,r,lmda,g,mu_j,sigma_j,div) 
                          for i in range(length_old)]
        
        #define the new call prices using interpolation
#         call_price_new = [call_interpolated_MJD(stock,disc_points_old,T,sigma,r,lmda,g,mu_j,sigma_j,div,disc_points_new[i])\
#                           for i in range(length_old,length_new)]
        call_price = np.append(call_price_old,0)
    
    #last call price has to be zero
    call_price[-1] = 0
    return call_price

# %%


#generate the new discretization points

def disc_points_new_1(K1_new,K2_new):
    # Create a 2D array with K1_new as the first row and K2_new as the second row
    C = np.vstack((K1_new, K2_new))
    return C


# %%


#generate the new marginals
#function to get the marginal distributions
#timepoints denote the number of timepoints at which the marginals are getting calculated

def marginal_new(call_prices_array_new,disc_points_new,timepoints,t1):
    
    marg = np.zeros_like(disc_points_new)
    
    for k in range(1,timepoints+1):
        print("timepoint:",t1[k])
        sum1 = 0
        N = len(disc_points_new[k-1])
        print(N)
        for i in range(N):
            if i == 0:
                #\mu(k_j) = (C(k_{j+1})-C(k_{j}))/(k_{j+1}-k_{j})+1
                marg[k-1,i] = np.divide(call_prices_array_new[k-1,i+1]-call_prices_array_new[k-1,i],\
                                          disc_points_new[k-1,i+1]-  disc_points_new[k-1,i])+1
            elif i == N-1:
                #mu_{k_{n})=-(C(k_{n})-C(k_{n-1}))/(k_{n}-k_{n-1})
                marg[k-1,i] = -np.divide(call_prices_array_new[k-1,i]-call_prices_array_new[k-1,i-1],\
                                       disc_points_new[k-1,i]-disc_points_new[k-1,i-1])
            
            else:
                #\mu(k_j) = (C(k_{j+1})-C(k_{j}))/(k_{j+1}-k_{j})-(C(k_{j})-C(k_{j-1}))/(k_{j}-k_{j-1})
                marg[k-1,i] = np.divide(call_prices_array_new[k-1,i+1]-call_prices_array_new[k-1,i],\
                                          disc_points_new[k-1,i+1]-  disc_points_new[k-1,i])\
                            - np.divide(call_prices_array_new[k-1,i]-call_prices_array_new[k-1,i-1],\
                                       disc_points_new[k-1,i]-disc_points_new[k-1,i-1])
               
            
            #marg[k-1,i] = np.round(marg[k-1,i],8)
            #marg[k-1,i] = max(marg[k-1,i],0)
            sum1 += marg[k-1,i]    
        print("Sum of marginals at",str(t1[k]),"is:",sum(marg[k-1,:]))
    return marg


# %%


def BS_marginal_from_calls(call_prices, strikes):
    """
    Vectorised conversion of a single row of call prices C(K)
    to the Breeden–Litzenberger density μ(K):

       μ(K_0)       =  (C_1 - C_0)/(K_1 - K_0) + 1
       μ(K_j)       =  (C_{j+1}-C_j)/(K_{j+1}-K_j)
                      -(C_j    -C_{j-1})/(K_j    -K_{j-1})   for 1≤j≤N-2
       μ(K_{N-1})   = -(C_{N-1}-C_{N-2})/(K_{N-1}-K_{N-2})
    """
    call_prices = np.asarray(call_prices, dtype=float)
    strikes     = np.asarray(strikes,     dtype=float)

    dC = np.diff(call_prices)              # C_{j+1}-C_j
    dK = np.diff(strikes)                  # K_{j+1}-K_j
    slope = dC / dK                        # first-forward differences

    marg = np.empty_like(call_prices)

    # first and last points
    marg[0]      = slope[0] + 1.0
    marg[-1]     = -slope[-1]

    # interior points (vectorised!)
    marg[1:-1] = slope[1:] - slope[:-1]

    return marg


# %%


# #payoff for Asian option
# def payoff_asian(X,Y,K):
#     F = max(0.5*(X+Y)-K,0)
#     #F = max(0.5*(X+Y)-5*Y,0)
#     #F =  max(X,Y) - Y
#     return F


# %%


def Asian_call_MC(stock, K, t1, t2,sigma,r,payoff_asian):
    tau = t1 
    tau2 = t2 - t1
    M = 100000
    S1 = np.zeros((M))
    S2 = np.zeros((M))
    random.seed(10)
    sum1 = 0
    for i in range(M):
        #simulating stock paths at time u
        S1[i] = stock * np.exp((r - 0.5 * sigma**2) * tau + sigma * np.sqrt(tau) * random.gauss(0,1))
        
        #simulating stock paths at time v
        S2[i] = S1[i] * np.exp((r - 0.5 * sigma**2) * tau2 + sigma * np.sqrt(tau2) * random.gauss(0,1))
            
        #payoff for the hedge portfolio with short maturity options 
        #sum1 += multiperiod_payoff(S1[i],S2[i],Strike_1,Strike_2,weight_1,weight_2,K)
        sum1 += payoff_asian( S1[i], S2[i],K)
        #sum1 += max(0.5*(S1[i]+S2[i])-K,0)
    call = np.exp(-r * t2) * (sum1/M)
    return call


# %%
# def weights(weight_0,weight_1,short_call,target_call):
#     w_1 = weight_1
#     w_0 = weight_0
    
#     w_2 = np.divide(target_call - w_1* short_call[0] -w_0, short_call[1])
    
#     return w_0,w_1,w_2



# %%
# payoff for hedging portfolio
def multiperiod_payoff(S1, S2, weights, target_strike, short_strikes):
    # |(y_j-K)^{+}-w0-w1(x_i-K1)^{+}-w2(x_i-K2)^{+}|
  
    c = abs(
        max(S2 - target_strike, 0)
        - weights[0]-sum(w * max(S1 - strikes, 0) for w,strikes in zip(weights[1:],short_strikes))
    )
    return c


# %%
#maximization problem for expected error at time T

def solve_max_problem(K1, K2, weights, short_strikes, target_strike, marg, epsilon):
    num_disc_points = len(K1)

    # model initialisation for P
    model = LpProblem("Upper-Bound-Problem", LpMaximize)

    # Create problem Variables
    n_timepoint_1 = n_timepoint_2 = num_disc_points

    DV_variables = LpVariable.matrix(
        "X", (range(n_timepoint_1), range(n_timepoint_2)), lowBound=0, upBound=1
    )

    allocation = np.array(DV_variables).reshape(num_disc_points, num_disc_points)
    # print("Decision Variable/Allocation Matrix: ")
    # print(allocation)

    # formulating the objective function

    # cost function
    cost = [
        multiperiod_payoff(K1[i], K2[j], weights, target_strike, short_strikes)
        for i in range(0, num_disc_points)
        for j in range(0, num_disc_points)
    ]

    # cost = [payoff_asian(K1[i],K2[j]) for i in range(0,N) for j in range(0,N)]
    # objective function
    cost_matrix = np.array(cost).reshape(num_disc_points, num_disc_points)
    obj_func = lpSum(allocation * cost_matrix)
    # print(obj_func)kdrjlap

    model += obj_func
    # print(model)

    # time point 1 Constraints
    for i in range(n_timepoint_1):
        # print(lpSum(allocation[i][j] for j in range(n_timepoint_2)) == marg[0][i])
        model += lpSum(allocation[i][j] for j in range(n_timepoint_2)) == marg[0][
            i
        ], "time 1 Constraint " + str(i)

    # time point 2 Constraints
    for j in range(n_timepoint_2):
        # print(lpSum(allocation[i][j] for i in range(n_timepoint_1)) == marg[1][j])
        model += lpSum(allocation[i][j] for i in range(n_timepoint_1)) == marg[1][
            j
        ], "time 2 Constraint " + str(j)

    Slack_variables = LpVariable.matrix("Delta", range(n_timepoint_1), lowBound=0)

    delta = np.array(Slack_variables).reshape(num_disc_points, 1)

    for i in range(n_timepoint_1):

        # epsilon-martingale constraints
        # time point 1 Constraints with delta
        # \sum_{j}p(i,j)*(y_j -x_i) <= delta_i
        model += lpSum(
            allocation[i][j] * (K2[j] - K1[i]) for j in range(n_timepoint_2)
        ) <= delta[i], " Time 1 Epsilon-Martingale Constraint " + str(i + 1)

        # epsilon-martingale constraints
        # time point 2 Constraints
        # sum_{j} p(i,j)(y_j -x_i) +delta_i >=0
        model += 0 <= lpSum(
            allocation[i][j] * (K2[j] - K1[i]) for j in range(n_timepoint_2)
        ) + delta[i], "Time 2 Epsilon-Martingale Constraint " + str(i + 1)

    # time 1 delta constraint
    # sum_{i} delta_i <= epsilon_n
    model += (
        lpSum(delta[i] for i in range(n_timepoint_1)) - epsilon <= 0,
        "Delta Constraint ",
    )

    model.solve(PULP_CBC_CMD())
    status = LpStatus[model.status]

    # print(f"status: {model.status}, {LpStatus[model.status]}")

    # output the optimal values of the objective function and the decision variables
    print("Upper bound:", model.objective.value())
    call_value = model.objective.value()

    result = {"call_value": call_value, "Q": DV_variables}
    return result

# %%
#function to get the marginal distributions using log-normal distribution
#timepoints denote the number of timepoints at which the marginals are getting calculated


def marginal1(n,timepoints,N,t1,r,sigma,stock,disc_points):
    marg1 = np.zeros((timepoints, N))
    for k in range(1,timepoints+1):
        print("timepoint:",t1[k])
        sum1 = 0
        for i in range(N):
            if i != (N-1):
                num = np.power(np.log(disc_points[k-1,N-1-i]/stock)- (r - 0.5 * (sigma**2))*t1[k],2)
                marg1[k-1,N-1-i] = np.divide(np.exp(np.divide(-num,2 * (sigma**2) * t1[k])),\
                                            np.sqrt(2 * np.pi * t1[k]) * disc_points[k-1,N-1-i] * sigma)
                marg1[k-1,N-1-i] = marg1[k-1,N-1-i]/n
                sum1 += marg1[k-1,N-1-i]
                
            else:
                print("sum", sum1)
                marg1[k-1,N-1-i] = 0
                print(k-1, marg1[k-1,N-1-i]+sum1)
        for i in range(N):
            if i ==0:
                marg1[k-1,i]= 1- sum1
        print("Sum of marginals at",str(t1[k]),"is:",sum(marg1[k-1,:]))
    return marg1



# %%
#function to get the marginal distributions using log-normal distribution
#timepoints denote the number of timepoints at which the marginals are getting calculated


def marginal1_NUG(n,timepoints,N,t1,r,sigma,stock,disc_points):
    marg1 = np.zeros((timepoints, N))
    for k in range(1,timepoints+1):
        print("timepoint:",t1[k])
        sum1 = 0
        for i in range(N):
            if i != (N-1):
                num = np.power(np.log(disc_points[k-1,N-1-i])- (r - 0.5 * (sigma**2))*t1[k],2)
                marg1[k-1,N-1-i] = np.divide(np.exp(np.divide(-num,2 * (sigma**2) * t1[k])),\
                                            np.sqrt(2 * np.pi * t1[k]) * disc_points[k-1,N-1-i] * sigma)
                marg1[k-1,N-1-i] = marg1[k-1,N-1-i]* (disc_points[k-1,i+1]-  disc_points[k-1,i])
                sum1 += marg1[k-1,N-1-i]
                
            else:
                print("sum", sum1)
                marg1[k-1,N-1-i] = 0
                print(k-1, marg1[k-1,N-1-i]+sum1)
        for i in range(N):
            if i ==0:
                marg1[k-1,i]= 1- sum1
        print("Sum of marginals at",str(t1[k]),"is:",sum(marg1[k-1,:]))
    return marg1


# %%
def get_short_call(t1,short_maturity,no_of_options,marg,disc_points,short_strikes):
    L = t1.index(short_maturity)
    N = len(disc_points[0])
    print(f"index of short maturity:{L}")
    #Value of short maturity options at time 0
    # short_call = \sum_{i}\alpha_i(x_i-short_strike)^+
    short_call = np.zeros(no_of_options)
    for j in range(no_of_options):
        short_call[j] = sum(marg[L-1,i] * max(disc_points[L-1,i]-short_strikes[j],0) \
                            for i in range(N))
        print("Short call value", str(j),"is:",short_call[j])
    return short_call



# %%
def get_short_put(t1,short_maturity,no_of_options,marg,disc_points,short_strikes):
    L = t1.index(short_maturity)
    N = len(disc_points[0])
    print(f"index of short maturity:{L}")
    #Value of short maturity options at time 0
    # short_call = \sum_{i}\alpha_i(x_i-short_strike)^+
    short_put = np.zeros(no_of_options)
    for j in range(no_of_options):
        short_put[j] = sum(marg[L-1,i] * max(short_strikes[j]-disc_points[L-1,i],0) \
                            for i in range(N))
        print("Short put value", str(j),"is:",short_put[j])
    return short_put


# %%
def weights(weight_0,weight_1,short_call,target_call):
    w_1 = weight_1
    w_0 = weight_0
    
    w_2 = np.divide(target_call - w_1* short_call[0] -w_0, short_call[1])
    
    return w_0,w_1,w_2

# %%
# def weights_new(short_call, target_call):
#     """
#     Compute weights given the short_call values and target_call value.
    
#     Parameters:
#     - short_call (list or np.array): List of short call values of length N.
#     - target_call (float): Target call value.

#     Returns:
#     - weights (list): A list of weights [w_0, w_1, ..., w_N].
#     """
#     N = len(short_call)
#     if N < 2:
#         raise ValueError("short_call must have at least two elements.")
    
#     # Initialize weights
#     w_0 = 0  # w_0 is set to 0
#     w = [0]  # Start with w_0 in the weights list
    
#     # Set weights w_1 to w_(N-1) to 1 / (N - 2)
#     w_1_to_N_minus_1 = [1 / (N - 2) for _ in range(1, N - 1)]
#     w.extend(w_1_to_N_minus_1)
    
#     # Compute w_N
#     w_N = np.divide(
#         target_call - sum(w[i+1] * short_call[i] for i in range(N - 1))-w[0], 
#         short_call[-1]
#     )
#     w.append(w_N)
    
#     return w


# %%
def weights_new(short_call, target_call):
    """
    Compute weights given the short_call values and target_call value.

    Parameters:
    - short_call (list or np.array): List of short call values of length N.
    - target_call (float): Target call value.

    Returns:
    - weights (list): A list of weights [w_0, w_1, ..., w_N].
    """
    N = len(short_call)
    if N < 1:
        raise ValueError("short_call must have at least one element.")
    
    # Initialize weights
    w_0 = 0  # w_0 is set to 0
    w = [w_0]  # Start with w_0 in the weights list

    if N == 1:
        # Special case where N = 1
        w_N = np.divide(target_call - w[0], short_call[-1])
        w.append(w_N)
    else:
        # Case where N > 1
        # Set weights w_1 to w_(N-1) to 1 / (N - 1)
        w_1_to_N_minus_1 = [ 0.989899 for _ in range(1, N)]#[1 / (N - 2) for _ in range(1, N - 1)]
        w.extend(w_1_to_N_minus_1)
        
        # Compute w_N
        w_N = np.divide(
            target_call - sum(w[i + 1] * short_call[i] for i in range(N - 1)) - w[0], 
            short_call[-1]
        )
        w.append(w_N)
    
    return w



# %%
def weights_multiple_options(short_call,weights, target_call):
    """
    Compute weights given the short_call values and target_call value.

    Parameters:
    - short_call (list or np.array): List of short call values of length N.
    - target_call (float): Target call value.

    Returns:
    - weights (list): A list of weights [w_0, w_1, ..., w_N].
    """
    N = len(short_call)
    if N < 1:
        raise ValueError("short_call must have at least one element.")
    
    # Initialize weights
    w_0 = 0  # w_0 is set to 0
    w = [w_0]  # Start with w_0 in the weights list

    if N == 1:
        # Special case where N = 1
        w_N = np.divide(target_call - w[0], short_call[-1])
        w.append(w_N)
    else:
        # Case where N > 1
        # Set weights w_1 to w_(N-1) to 1 / (N - 1)
        w_1_to_N_minus_1 = weights#[1 / (N - 2) for _ in range(1, N - 1)]
        w.extend(w_1_to_N_minus_1)
        
        # Compute w_N
        w_N = np.divide(
            target_call - sum(w[i + 1] * short_call[i] for i in range(N - 1)) - w[0], 
            short_call[-1]
        )
        w.append(w_N)
    
    return w

# %%


def Asian_call_MJD(stock, K, t1, t2,lmda,mu_j,sigma_j,g,sigma,r,payoff_asian):
    """
    Computing the price of an Asian Option whose payofff is given by the arithmetic 
    average of the stock price at times t1 and t2
    Parameters:
    t1: first time point 
    t2:second time point
    
    """
    tau = t1 
    tau2 = t2 - t1
    M = 100000
    S1 = np.zeros((M))
    S2 = np.zeros((M))
    
    np.random.seed(10)
    sum1 = 0
    for i in range(M):
        #simulating stock paths at time u
        Poisson1 =  np.random.poisson(lmda*tau)
        
        S1[i] = stock * np.exp((r-lmda * g - 0.5 * sigma **2)* tau + sigma * np.sqrt(tau) * np.random.normal(0,1)\
                               + mu_j * Poisson1 +  np.sqrt(Poisson1) * sigma_j * np.random.normal(0,1))
                                                  
        #simulating stock paths at time v
        Poisson2 = np.random.poisson(lmda*tau2)
        
        S2[i] = S1[i] * np.exp((r-lmda * g - 0.5 * sigma **2) * tau2 + sigma * np.sqrt(tau2) * np.random.normal(0,1)\
                               + mu_j * Poisson2 +  np.sqrt(Poisson2) * sigma_j * np.random.normal(0,1))
            
        #payoff for the hedge portfolio with short maturity options 
        #sum1 += multiperiod_payoff(S1[i],S2[i],Strike_1,Strike_2,weight_1,weight_2,K)
        sum1 += payoff_asian( S1[i], S2[i],K)
        #sum1 += max(0.5*(S1[i]+S2[i])-K,0)
    call = np.exp(-r * t2) * (sum1/M)
    return call





# %%


def Forward_nonabs_MJD(stock, K, t1, t2,lmda,mu_j,sigma_j,g,sigma,r,payoff_forward):
    """
    Computing the price of an Asian Option whose payofff is given by the arithmetic 
    average of the stock price at times t1 and t2
    Parameters:
    t1: first time point 
    t2:second time point
    
    """
    tau = t1 
    tau2 = t2 - t1
    M = 100000
    S1 = np.zeros((M))
    S2 = np.zeros((M))
    
    np.random.seed(10)
    sum1 = 0
    for i in range(M):
        #simulating stock paths at time u
        Poisson1 =  np.random.poisson(lmda*tau)
        
        S1[i] = stock * np.exp((r-lmda * g - 0.5 * sigma **2)* tau + sigma * np.sqrt(tau) * np.random.normal(0,1)\
                               + mu_j * Poisson1 +  np.sqrt(Poisson1) * sigma_j * np.random.normal(0,1))
                                                  
        #simulating stock paths at time v
        Poisson2 = np.random.poisson(lmda*tau2)
        
        S2[i] = S1[i] * np.exp((r-lmda * g - 0.5 * sigma **2) * tau2 + sigma * np.sqrt(tau2) * np.random.normal(0,1)\
                               + mu_j * Poisson2 +  np.sqrt(Poisson2) * sigma_j * np.random.normal(0,1))
            
        #payoff for the hedge portfolio with short maturity options 
        #sum1 += multiperiod_payoff(S1[i],S2[i],Strike_1,Strike_2,weight_1,weight_2,K)
        sum1 += payoff_forward( S1[i], S2[i],K)
        #sum1 += max(0.5*(S1[i]+S2[i])-K,0)
    call = np.exp(-r * t2) * (sum1/M)
    return call





# %%

def MJD_call_vectorized(S0, strike, t, T, sigma, r, lmda, g, mu_j, sigma_j, div):
    """
    A vectorized version of MJD_call that handles S0 as an array, shape (N,) or (N,1).
    'strike', 't', 'T', etc. can remain scalars.
    """
    tau = T - t  # time to maturity
    # We'll produce a result array callT with the same shape as S0
    # Make sure S0 is at least 1D
    S0 = np.array(S0, ndmin=1, dtype=float)  
    strike = np.array(strike, ndmin=1, dtype=float)  
    
    out = np.where(strike < 0, 0.0, np.where(strike == 0, S0, np.where(strike == 0, S0, np.nan)) )
    
#     # 1) Cases for strike
#     if strike < 0:
        
#         # Return an array of zeros
#         return np.zeros_like(S0)
#     elif strike == 0:
#         # call payoff is S0
#         return S0.copy()
    mask = strike > 0
    
    if not mask.any():
        return out

    S = S0[mask]
    K = strike[mask]

    # tau == 0 shortcut
    if tau == 0:
        out[mask] = np.maximum(S - K, 0.0)
        return out

    if not mask.any():
        return out
    
    S = S0[mask]
    # If we reach here, strike > 0
    if tau == 0:
        # simply compute max(S0 - strike, 0) in a vector sense
        return np.maximum(S0 - strike, 0)

    # 2) For tau > 0, we do the Merton Jump Diffusion sum
    # Initialize sum_n as an array of zeros with shape S0
    sum_n = np.zeros_like(S0, dtype=float)

    for n in range(100):
        r_n = r - lmda*g + (n*(mu_j + 0.5*(sigma_j**2)))/tau
        sigma_n = np.sqrt(sigma**2 + (n*(sigma_j**2))/tau)

        # d_1n is shape (N,) if S0 is shape (N,)
        # we do np.log(S0/strike) -- S0/strike is shape (N,), so np.log is shape (N,)
        d_1n = ( np.log(S0/strike) + (r_n - div + 0.5*sigma_n**2)*tau ) / ( sigma_n*np.sqrt(tau) )

        # Pr_n is a scalar for each n
        Pr_n = np.exp(-lmda*tau) * ((lmda*tau)**n / math.factorial(n))

        cdf_d1n = si.norm.cdf(d_1n)
        cdf_d2n = si.norm.cdf(d_1n - sigma_n*np.sqrt(tau))

        # The expression is shape (N,) because S0 is shape (N,)
        # each operation yields an array
        term = (
            S0*np.exp((r_n - div)*tau)*cdf_d1n
            - strike*cdf_d2n
        )  # shape (N,)

        sum_n += Pr_n * term  # sum_n is shape (N,)

    callT = np.exp(-r*tau)*sum_n  # shape (N,)

    return callT


# %%
