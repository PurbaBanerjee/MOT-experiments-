# %%
#import the library pulp as p
import pulp as p
from pulp import *
import pandas as pd
import numpy as np
import math
from scipy.stats import norm
from scipy.optimize import minimize

from Interpolation_functions_2 import *

# %%
import gurobipy as gp
print(gp.gurobi.version())
model = gp.Model()
print("License ID:", model.getParamInfo("LicenseID"))

# %%
#common parameters for all the experiments/GLOBAL VARIABLES
stock = 1 #initial stock price

K = 1 # target option's strike price

r = 0 #risk-free rate of interest

sigma = 0.2 #volatility of the stock price

T = 1 #target maturity

mu = 0 #return of the stock price

t = 0

timepoints = 2 #number of timesteps


T_GRID = [0,0.5,T]#times at which the marginals of the stock price are evaluated

short_maturity = T_GRID[1] # maturity of the options in the hedge portfolio


short_strike_range = [1,1.1,0.9,1.2,0.8,1.25]#range of short strikes for increasing number of options

# %%
#function to return the discretization points, call prices and the marginals for a given value of truncation range and number of discretization points and choice of uniform or nonuniform grid

def get_disc_points_and_marginals(truncation_range=None,n=None, N=None,choice="uniform"):
    """
       Generate the discretization points for the given problem depending on uniform or non-uniform grid
       Parameters: 
          Global variables: Stock, sigma, T,r,
          Local variables: n- (1/n) denotes the spacing between the discretization points
                        
    """
    if choice == "uniform":
        if truncation_range == None or n == None:
            return ("Need to provide n or truncation range")
        #return a uniform grid
        D = np.linspace(0, truncation_range, int(truncation_range*n)+1)
        
        
        #next we find the point where the interpolated line joining the last two strike points takes value zero
        R_0 = find_zero(BS_call,stock,D,T,sigma,r)
        
#         print(f"The interpolated line takes the value 0 at {R_0}")
        
        #print the corresponding call value
        print(f"Strike:{R_0},Interpolated call value:{interpolated_line(stock,D,T,sigma,r,R_0)}")
        
        
        #extending the truncation range to include the new points till the zero of the interpolated call value
        K1_new = append_numbers(D,D[-1],R_0,np.diff(D)[0])
        
#         print(f"Extended truncation range for time {t1[1]}:{K1_new}")
#         print(f"length of new truncation range :{len(K1_new)}")
#         print(f"previous length:{len(D)}")
        
        K2_new = append_numbers(D,D[-1],R_0,np.diff(D)[0])
#         print(f"Extended truncation range for time {t1[2]}:{K2_new}")
#         print(f"spacing:{K2_new[-2]/(len(K2_new)-2)},{D[-1]/(len(D)-1)}") 
        
        
        #getting the new discretization points
        disc_points_new = disc_points_new_1(K1_new,K2_new)
        print(f"The new discretization points are:{disc_points_new}")
        
        # store the call prices as a 2D array
        call_prices_array_new = np.vstack((call_prices(stock,D,K1_new,T_GRID[1],sigma,r),call_prices(stock,D,K2_new,T,sigma,r)))
#         print(call_prices_array_new)
        
        #getting the discrete marginal distributions

        marg = marginal_new(call_prices_array_new,disc_points_new,timepoints,T_GRID)
#         print(marginal_new(call_prices_array_new,disc_points_new,timepoints,t1))
        
        
        #returns the grid and the number of grid points
        return disc_points_new,call_prices_array_new,marg
    else:
        if N == None:
            return print("Need to provide N")
        np.random.seed(12)
        grid = np.random.normal(K,sigma,N-2)# creating a grid concentrated around the target strike
        
        grid = np.append([0,truncation_range],grid)# adding 0 and the final truncation point to the list
        
        grid = np.sort(grid)# sorting the grid in ascending order
        
        #next we find the point where the interpolated line joining the last two strike points takes value zero
        R_0 = find_zero(BS_call,stock, grid,T,sigma,r)
        
        print(f"The interpolated line takes the value 0 at {R_0}")
        
        #print the corresponding call value
        print(f"Strike:{R_0},Interpolated call value:{interpolated_line(stock,grid,T,sigma,r,R_0)}")
        
        new_grid = np.append(grid,[R_0])
        
        K1_new = K2_new = new_grid
        
        #getting the new discretization points
        disc_points_new = disc_points_new_1(K1_new,K2_new)
        print(f"The new discretization points are:{disc_points_new}")
        print(f"Number of discretization points are:{len(K1_new)}")
        
                
        # store the call prices as a 2D array
        call_prices_array_new = np.vstack((call_prices(stock,grid,K1_new,T_GRID[1],sigma,r),call_prices(stock,grid,K2_new,T,sigma,r)))
#         print(call_prices_array_new)
        
        #getting the discrete marginal distributions

        marg = marginal_new(call_prices_array_new,disc_points_new,timepoints,T_GRID)
#         print(marginal_new(call_prices_array_new,disc_points_new,timepoints,T_GRID))
        
        #returns the grid and the number of grid points
        return disc_points_new,call_prices_array_new,marg

# %%
def get_target_maturity_calls(marg,no_of_options_T,disc_points_new,short_strikes_T):
    """
    returns the price of the options with maturity T in the hedge portfolio
    Parameters:
       marg: marginal distributions, 
       disc_points_new: the discretization points 
    """
    
    short_call = np.zeros(no_of_options_T)
    
    N = len(disc_points_new[1]) #returns the number of discretization points corresponding to the target maturity
    
    for j in range(no_of_options_T):
        short_call[j] = sum(marg[1,i] * np.maximum(disc_points_new[1,i]- short_strikes_T[j],0) for i in range(N))
    return short_call
    


def get_short_call(t1,short_maturity,no_of_options,marg,disc_points_new,short_strikes):
    """
    returns the price of the the short-maturity options in the hedge portfolio
    Parameters:
      t1: list of the time-points given by [0,short_maturity,target_maturity]
      short_maturity: maturity of the options in the hedge portfolio
      no_of_options: numner of options in the hedge portfolio
      marg: marginal distributions
      disc_points_new: discretization points
      short_strikes: strikes of the options in the hedge portfolio
    """
    short_call = np.zeros(no_of_options)
    
    L = t1.index(short_maturity)
    
    N = len(disc_points_new[0])#returns the number of discretization points corresponding to the short maturity
    
    #Value of short maturity options at time 0
    # short_call = \sum_{i}\alpha_i(x_i-short_strike)^+
    for j in range(no_of_options):
        short_call[j] = sum(marg[L-1,i] * np.maximum(disc_points_new[L-1,i]-short_strikes[j],0) \
                            for i in range(N))
#         print("Short call value", str(j),"is:",short_call[j])
    return short_call





# %%
def Asian_option_payoff(stock_price_t1,stock_price_T,strike_price):
    return np.maximum(0.5*(stock_price_t1+stock_price_T)-strike_price,0)

# %% [markdown]
#  #### SOLVE THE PROBLEM WITHOUT BIG-M CONSTRAINTS ###

# %%
import gurobipy as gp
from gurobipy import GRB, quicksum
import numpy as np

def solve_max_problem_gurobi_without_M(M_bound,
    K1,
    K2,
    cash,
    Weights_t1, 
    Weights_T,
    short_strikes_t1, 
    short_call_t1, 
    short_strikes_T,   
    short_call_T,                                   
    target_strike,
    marg, Epsilon
):
    
    # Create a Gurobi model
    model = gp.Model("Upper-Bound-Problem-RowSpecificM")
    model.setParam('OutputFlag', 0)

    N = len(K1)
    
    no_of_options_t1 = len(short_strikes_t1)
    no_of_options_T = len(short_strikes_T)
    
    # Decision variables
    X = model.addVars(N, N, lb=0, ub=1, vtype=GRB.CONTINUOUS, name="X")
    P_slack = model.addVars(N, lb=0, vtype=GRB.CONTINUOUS, name="P_slack")
    B = model.addVars(N, vtype=GRB.BINARY, name="B")


    # Objective: Maximize sum of P_slack
    model.setObjective(quicksum(P_slack[i] for i in range(N)), GRB.MAXIMIZE)

    
  

   

     
    for i in range(N):
         # The hedging_error expression
        hedging_error = (quicksum(X[i, j] * (Asian_option_payoff(K1[i],K2[j],target_strike) 
                                            -  quicksum(
                                Weights_T[k] * max(K2[j] - short_strikes_T[k], 0)
                                for k in range(no_of_options_T) #options with maturity T 
                              )
                            )  for j in range(N))
                        - marg[0][i] * (
                            cash
                            + quicksum(
                                Weights_t1[l] * max(K1[i] - short_strikes_t1[l], 0)
                                for l in range(no_of_options_t1)
                            )#options with short maturity t1
                        )
                    )
        # -- Absolute value constraints:
        # a) hedging_error <= P_slack[i]
        model.addConstr(hedging_error <= P_slack[i], f"modulus_1_{i}")

        # b) hedging_error >= -P_slack[i]
        model.addConstr(hedging_error >= -P_slack[i], f"modulus_2_{i}")

        # d) hedging_error *(1 - 2*B[i]) == P_slack[i]
        model.addConstr(hedging_error *(1 - 2*B[i]) == P_slack[i], f"modulus_3_{i}")
   
   
    # Marginal constraints
    for i in range(N):
        model.addConstr(quicksum(X[i, j] for j in range(N)) == marg[0][i], f"time1_{i}")

    for j in range(N):
        model.addConstr(quicksum(X[i, j] for i in range(N)) == marg[1][j], f"time2_{j}")

    # Martingale constraints 
   
    for i in range(N):
        model.addConstr(quicksum(X[i, j]*(K2[j] - K1[i]) for j in range(N)) == 0, f"martingale_{i}")
    
    model.setParam('NonConvex', 2)

    # Solve the model
    model.optimize()

    if model.status != GRB.OPTIMAL:
        return {
            "call_value": float("inf"),
            "Status": model.status,
            "p_matrix": None,
            "P_slack": None,
            "B": None,
#             "Delta": None
        }
    
 
    # 6) Extract solution
    p_matrix = np.zeros((N, N))
    for i in range(N):
        for j in range(N):
            p_matrix[i, j] = X[i, j].X

    p_slack_array = np.array([P_slack[i].X for i in range(N)])
    b_array       = np.array([B[i].X          for i in range(N)])
#     delta_array   = np.array([Delta[i].X      for i in range(N)])
    call_value    = model.objVal

    return {
        "call_value": call_value,
        "Status": "Optimal",
        "p_matrix": p_matrix,
        "P_slack": p_slack_array,
        "B": b_array,
#         "Delta": delta_array,
       
    }


# %%
from scipy.optimize import dual_annealing
import numpy as np
import pulp

def min_max_optimization(
    solve_max_problem,
    M_bound,
    K1,
    K2,
    short_strikes_t1,
    short_strikes_T,
    no_of_options_t1,
    no_of_options_T,
    K,
    marg,
    short_call_t1,
    short_call_T,
    Epsilon,
    x0, #initial choice for weights
    seed,
    bounds
):
    """
    Returns the result of the min-max process for a given number of options
    in the hedge portfolio.
    """

    # Keep a log of intermediate values
    log = []

    n_timepoint_1 = len(marg[0])
    n_timepoint_2 = len(marg[1])

    def min_function_on_weights(Weights_with_cash):
        """
        Inner objective: given a set of hedge weights, solve the max problem
        and compute the "error" (sum of absolute differences).
        """

        # Solve the inner max problem
        cash = Weights_with_cash[0]
        Weights_without_cash = Weights_with_cash[1:]
        
        
        result = solve_max_problem(
            M_bound,
            K1,
            K2,
            cash,
            Weights_without_cash[:len(short_strikes_t1)],
            Weights_without_cash[len(short_strikes_t1):],
            short_strikes_t1,
            short_call_t1,
            short_strikes_T,
            short_call_T,
            K,
            marg,
            Epsilon,
        )
        Status = result["Status"]
        if Status != "Optimal":
            # If infeasible or not optimal, penalize heavily
            print(f"Warning: Status is {Status}, no solution found.")
            return float("inf")

        # Retrieve the numeric arrays from the solver result dictionary
        p_matrix = result["p_matrix"]      # shape: (n_timepoint_1, n_timepoint_2)
        P_slack  = result["P_slack"]       # shape: (n_timepoint_1,)
        B_array  = result["B"]             # shape: (n_timepoint_1,)
#         Delta    = result["Delta"]         # shape: (n_timepoint_1,)
        call_val = result["call_value"]    # the objective in the solve_max_problem

        # Compute the "error" function f_w_pr:
        #    sum over i of | sum_{j} p_matrix[i,j]*(K2[j] - K)^+
        #                     - alpha_i*(hedge payoff at i) |
        alpha = marg[0]
        f_w_pr = 0.0
        
        
        
        
        #compute the objective value and hedge value
        hedge_value = 0
        for i in range(n_timepoint_1):
            payoff_target = sum(
                p_matrix[i,j] * Asian_option_payoff(K1[i],K2[j],K) 
                for j in range(n_timepoint_2)
            )
            

            payoff_hedge = (alpha[i] * (cash
                + sum(
                    Weights_without_cash[l] * max(K1[i] - short_strikes_t1[l], 0) #options with maturity t_1
                    for l in range(no_of_options_t1)
                )
                                      )
             +  sum(
                p_matrix[i,j] *  sum(
                                Weights_without_cash[no_of_options_t1 + k] * max(K2[j] - short_strikes_T[k], 0)
                                for k in range(no_of_options_T) #options with maturity T 
                              )
                for j in range(n_timepoint_2)                     
            )
                           )
            
            f_w_pr += abs(payoff_target - payoff_hedge)
            hedge_value += payoff_hedge
        
      
        #compute the target option price
        target_price = 0
        for i in range(n_timepoint_1):
            for j in range(n_timepoint_2):
                target_price +=  p_matrix[i,j] * Asian_option_payoff(K1[i],K2[j],K)
        
        
        
        
        
        # Record everything in our log
        log_entry = {
            "Weights_t1": Weights_without_cash[:len(short_call_t1)],
            "Weights_T" : Weights_without_cash[len(short_call_t1):],
            "cash": cash,
            "No_of_options_t1" : no_of_options_t1,
            "No_of_options_T" : no_of_options_T,
            "Objective value (outer)": f_w_pr,
            "p_matrix": p_matrix,
            "P_slack": P_slack,
            "B": B_array,
            "call_value (inner)": call_val,
            "Status": Status,
            "target_price": target_price,
            "hedge_value": hedge_value
        }
        log.append(log_entry)
        print(f"value from gurobi:{call_val}")
        print(f"val solving max LP:{f_w_pr}\n")
       
        return f_w_pr

    # 7) Set up bounds for each short position and run dual_annealing
    bounds = bounds * ( no_of_options_t1 + no_of_options_T + 1 )
    result_dual_annealing = dual_annealing(min_function_on_weights, bounds = bounds, x0 = x0, seed=seed)#,maxiter = 2000

    if result_dual_annealing.success:
        w_opt = result_dual_annealing.x
        final_value = result_dual_annealing.fun
        return w_opt, final_value, log
    else:
        print("Simulated annealing failed")
        return None, float("inf"), log


# %%
###############################################################################
#  MAIN DRIVER (run_experiment) 
###############################################################################
def run_experiment_no_M(solver=None,
    truncation_range=None,
    n=None,
    N=None,
    no_of_options_t1=None,
    no_of_options_T = None,
    short_strikes_t1 = None,
    short_strikes_T = None,
    epsilon=None,
    M_bound=None,
    choice=None,
    x0=None,
    seed=None,
    bounds = None                    
):
    """
    Orchestrates everything:
     1) Build discretization points & marginals
     2) Pick short strikes
     3) Compute target call & short calls
     4) Solve min-max
     5) Return final results
    """
    # Build grid & marginals
    disc_points_new, call_prices_array_new, marg = get_disc_points_and_marginals( truncation_range=truncation_range,\
                                                                                n=n,N=N,choice=choice)
    

    K1 = disc_points_new[0]
    
    K2 = disc_points_new[1]
   
    # Pick strikes for maturity t_1
    print(f"Strikes for maturity {T_GRID[1]}: {short_strikes_t1}")
    
    # Compute  short calls

    short_call_t1 = get_short_call(T_GRID, 
                                   T_GRID[1], 
                                   no_of_options_t1, 
                                   marg, 
                                   disc_points_new, 
                                   short_strikes_t1)
    
    print(f"length of short_call: {len(short_call_t1)}")

    
    #Pick strikes for maturity T
    print(f"Strikes for maturity {T}: {short_strikes_T}")
    
    short_call_T = get_target_maturity_calls( marg,
                                              no_of_options_T,
                                              disc_points_new,
                                              short_strikes_T)
    
    # pick solver function
    if solver.lower() == "pulp":
        solver_func = solve_max_problem_pulp
    else:
        solver_func = solve_max_problem_gurobi_without_M


    # solve the min_max
    w_opt, final_value, log_results = min_max_optimization(
        solver_func,
        M_bound,
        K1, 
        K2,
        short_strikes_t1,
        short_strikes_T,
        no_of_options_t1,
        no_of_options_T,
        K,
        marg,
        short_call_t1,
        short_call_T,
        epsilon,
        x0,
        seed,
        bounds
    )
    
    
    

    # Solve the max problem once more with final_weights
    final_solution = solver_func(
        M_bound,
        K1,
        K2,
        w_opt[0],
        w_opt[1:len(short_strikes_t1)+1],
        w_opt[len(short_strikes_t1)+1:],
        short_strikes_t1,
        short_call_t1,
        short_strikes_T,
        short_call_T,
        K,
        marg,
        epsilon
    )
    
 

    # Re-compute the target_call
   
    prob_matrix_final = final_solution["p_matrix"]
    target_call = 0
    n_timepoint_1 = len(K1)
    n_timepoint_2 = len(K2)
    
    for i in range(n_timepoint_1):
        for j in range(n_timepoint_2):
            target_call += prob_matrix_final[i][j]* Asian_option_payoff(K1[i],K2[j],K)
    
    
    #compute the price of hedge portfolio at time 0
    hedge_value = w_opt[0]+ np.dot(w_opt[1:len(short_strikes_t1)+1],short_call_t1)\
     + np.dot(w_opt[len(short_strikes_t1)+1:], short_call_T)

    # 8) Check constraints using the existing check_constraints_pulp_solution function
   
    if final_solution["Status"] =="Optimal" and final_solution["p_matrix"] is not None:
        all_satisfied, violations = check_constraints_pulp_solution_no_M(
            M_bound,
            K1, K2,
            w_opt,
            no_of_options_t1,
            no_of_options_T,
            short_strikes_t1,
            short_strikes_T,
            K,
            marg,
            epsilon,
            final_solution,
            tolerance=1e-8 
        )

        if all_satisfied:
            print("All constraints are satisfied at the final solution!")
        else:
            print("Constraint violations found at the final solution:")
            for v in violations:
                print("  -", v)
    else:
        print("Final solution wasn't optimal, so skipping constraint check.")

   
    # 9) Return final results
    return {
        "w_opt": w_opt,#weights with cash
        "cash": w_opt[0],
        "weights_t1": w_opt[1:len(short_strikes_t1)+1],
        "weights_T": w_opt[len(short_strikes_t1)+1:],
        "final_value": final_value,
        "log": log_results,
        "N_initial": N, #initial choice of discretization points
        "No_of_options_t1" : no_of_options_t1,
        "No_of_options_T" : no_of_options_T,
        "N": len(K1),#total number of discretization points after interpolation 
        "Value_inner":final_solution["call_value"],
        "p_matrix": final_solution["p_matrix"],
        "target_call_price": target_call,
        "K1": K1,
        "K2": K2,
        "short_strikes_t1": short_strikes_t1,
        "short-strikes_T": short_strikes_T,
        "Hedge_value":  hedge_value
    }

# %%
import numpy as np

def check_constraints_pulp_solution_no_M(
    M_bound,
    K1, K2,
    Weights,         # [cash, w1, w2, ...]
    no_of_options_t1,
    no_of_options_T,
    short_strikes_t1,
    short_strikes_T,
    target_strike,
    marg,
    epsilon,
    solution_dict,
    tolerance=1e-8
):
    """
    Re-checks constraints from solve_max_problem_gurobi_without_M.
    Returns (all_satisfied, violations).
    """

    # ============= 1) Basic Setup =============
    n_timepoint_1 = len(marg[0])  # alpha
    n_timepoint_2 = len(marg[1])  # beta

    # Extract final solution arrays
    p_matrix = solution_dict["p_matrix"]  # shape (n_timepoint_1, n_timepoint_2)
    P_slack  = solution_dict["P_slack"]   # shape (n_timepoint_1,)
    B_array  = solution_dict["B"]         # shape (n_timepoint_1,)

    # If solver not optimal or p_matrix is None -> skip
    if solution_dict["Status"] != "Optimal" or p_matrix is None:
        return (
            False,
            [f"Solver status {solution_dict['Status']} or p_matrix=None => skip check"]
        )

    violations = []

    # ============= 2) Timepoint 1 Constraints =============
    # sum_j p[i,j] == marg[0][i]
    for i in range(n_timepoint_1):
        lhs = np.sum(p_matrix[i,:])
        rhs = marg[0][i]
        if abs(lhs - rhs) > tolerance:
            msg = f"Row sum constraint violated at i={i}: LHS={lhs}, RHS={rhs}"
            violations.append(msg)

    # ============= 3) Timepoint 2 Constraints =============
    # sum_i p[i,j] == marg[1][j]
    for j in range(n_timepoint_2):
        lhs = np.sum(p_matrix[:, j])
        rhs = marg[1][j]
        if abs(lhs - rhs) > tolerance:
            msg = f"Column sum constraint violated at j={j}: LHS={lhs}, RHS={rhs}"
            violations.append(msg)

    # ============= 4) Martingale Constraints =============
    # sum_j p[i,j]*(K2[j] - K1[i]) = 0  for each i
    for i in range(n_timepoint_1):
        lhs = 0.0
        for j in range(n_timepoint_2):
            lhs += p_matrix[i, j]*(K2[j] - K1[i])
        if abs(lhs) > tolerance:
            msg = f"Martingale constraint violated at i={i}: LHS={lhs}"
            violations.append(msg)

    # ============= 5) Absolute Value (No Big M) Constraints =============
    # For each i, define:
    # hedging_error = sum_j p[i,j]*(K2[j]-target_strike)^+
    #               - alpha[i]*(cash + sum_l W[l+1]*(K1[i]-short_strikes[l])^+)
    # 1) hedging_error <= P_slack[i]
    # 2) hedging_error >= -P_slack[i]
    # 3) hedging_error*(1 - 2*B[i]) == P_slack[i]

    alpha = marg[0]
    cash  = Weights[0]
    w_opt_t1 = Weights[1:no_of_options_t1+1]  # the options with maturity t1
    w_opt_T = Weights[no_of_options_t1+1:] #the options with maturity T
    
      
    for i in range(n_timepoint_1):
        # payoff_target
        payoff_target_maturity = 0.0
        for j in range(n_timepoint_2):
            payoff_target_maturity += p_matrix[i,j] * (Asian_option_payoff(K1[i], K2[j], target_strike)
                           -  sum(
                w_opt_T[l] * max(K2[j] - short_strikes_T[l], 0)
                for l in range(no_of_options_T)   
                           )
                                             )

        # payoff_hedge
        payoff_short_maturity_hedge = alpha[i]*(
            cash + sum(
                w_opt_t1[l] * max(K1[i] - short_strikes_t1[l], 0)
                for l in range(no_of_options_t1)
            )
        )
                                              

        hedging_error = payoff_target_maturity - payoff_short_maturity_hedge

        # 1) hedging_error <= P_slack[i]
        if hedging_error - P_slack[i] > tolerance:
            msg = (f"Absolute-value constraint #1 violated i={i}: "
                   f"hedging_error={hedging_error}, P_slack={P_slack[i]}")
            violations.append(msg)

        # 2) hedging_error >= -P_slack[i]
        if hedging_error + P_slack[i] < -tolerance:
            msg = (f"Absolute-value constraint #2 violated i={i}: "
                   f"hedging_error={hedging_error}, P_slack={P_slack[i]}")
            violations.append(msg)

        # 3) hedging_error*(1-2*B[i]) == P_slack[i]
        lhs_3 = hedging_error * (1 - 2*B_array[i])
        if abs(lhs_3 - P_slack[i]) > tolerance:
            msg = (f"Absolute-value constraint #3 violated i={i}: "
                   f"lhs_3={lhs_3}, P_slack={P_slack[i]}, B={B_array[i]}")
            violations.append(msg)

    # ============= Finalize =============
    all_satisfied = (len(violations) == 0)
    return (all_satisfied, violations)


# %% [markdown]
# **SOLVE THE DUAL PROBLEM TO GET THE SUPERHEDGE**

# %%
# formulating the dual to the maximization problem
def inner_minimization(K1, K2, target_strike, marg,Asian_option_payoff):
    """
    Solve the dual problem
    """
    num_K1 = len(K1)
    num_K2 = len(K2)

    # Gurobi model
    model = gp.Model("Minimization")
#     model.setParam('OutputFlag', 0)  # Suppress solver output
    

    # Decision variables
    phi = model.addVars(num_K1, lb=-GRB.INFINITY,name="phi")
    zi = model.addVars(num_K2,lb=-GRB.INFINITY, name="zi")
    h = model.addVars(num_K1,lb=-GRB.INFINITY, name="h")

    # Objective function
    obj_expr = quicksum(phi[i] * marg[0][i] for i in range(num_K1)) + quicksum(zi[j] * marg[1][j] for j in range(num_K2))
    model.setObjective(obj_expr, GRB.MINIMIZE)
    
    
    model.update()#update the model to print the objective function
    # Print Objective Function
    print("\nObjective Function:")
    print(model.getObjective())  # Correct way to print the objective

    # Constraints
    print("\nConstraints:")
    for i in range(num_K1):
        for j in range(num_K2):
            constr_expr = phi[i] + zi[j] + h[i] * (K2[j] - K1[i]) >= Asian_option_payoff(K1[i], K2[j],target_strike)
            constr_name = f"Constraint_{i}_{j}"
            model.addConstr(constr_expr, name=constr_name)

            
    model.update()#update the model to get the constraints
    
#     for constr in model.getConstrs():
#         print(f"{constr.ConstrName}: {model.getRow(constr)} >= {constr.RHS}")  

    # Solve the model
    model.optimize()
    
    for constr in model.getConstrs():
        slack = constr.Slack  # Gurobi automatically computes LHS - RHS
#         print(f"{constr.ConstrName}: Slack = {slack:.12f}")
    if model.status == GRB.OPTIMAL:
        max_value = model.objVal
        Phi = np.array([phi[i].X for i in range(num_K1)])
        Zi = np.array([zi[i].X for i in range(num_K2)])
        H = np.array([h[i].X for i in range(num_K1)])
        return {"Objective":max_value,"Phi":Phi,"Zi":Zi,"H":H}
    else:
        raise ValueError("Maximization problem failed.")

# %%
#WE ALWAYS KEEP X) FIXED AS THE DUAL WEIGHTS SO CHANGE OF SEED WILL NOT AFFECT THE RESULTS

if __name__ == "__main__":
    N = 14
    seed_set = [17] # [136,17,990,10000,2]
    
    list_of_objectives = []
    list_of_dictionaries = []
    no_of_options=4
    truncation_range=2
    bounds = [(-0.5, 0.5)]
    
    results_for_varying_seed = []
    
    
    for seed in seed_set: 
        print(f"\n========== Running the experiment for seed={seed} ==========")
        truncation_range = 2
        disc_points_new, call_prices_array_new, marg = get_disc_points_and_marginals(
                    truncation_range=truncation_range, N=N, choice="non-uniform"
                )
        K1 = disc_points_new[0]
        K2 = disc_points_new[1]

        result_dual = inner_minimization(K1, K2, K, marg, Asian_option_payoff)

        #get the objective value
        print(f"The objective value using the dual:{result_dual['Objective']}")
        #get the hedge portfolio coefficients
        Phi = result_dual["Phi"]
        Zi = result_dual["Zi"]
        H = result_dual["H"]

        no_of_options = len(K1)
        short_strikes_t1 = K1 
        # no_of_options = 4
        # short_strikes_t1 = short_strike_range[:no_of_options]

        X = np.zeros((len(K1),no_of_options))


        for i in range(len(K1)):
            for j in range(len(short_strikes_t1)):
                    X[i][j] = np.maximum(K1[i] - short_strikes_t1[j],0)



        from sklearn.linear_model import LinearRegression

        model_regression =  LinearRegression()
        model_regression.fit(X, Phi)



        Weights_for_options_t1 = model_regression.coef_
        cash_t1 = model_regression.intercept_
        print("Coefficients:",Weights_for_options_t1)

        print("Intercept:",cash_t1)
        # plt.plot(K1,cash_t1+[np.dot(Weights_for_options_t1 ,X[i]) for i in range(X.shape[0])],label="Hedge portfolio")
        # plt.plot(K1,Phi,label='target')





        no_of_options = len(K2)
        short_strikes_T = K2 #short_strike_range[:no_of_options]

        X2 = np.zeros((len(K2),no_of_options))


        for i in range(len(K2)):
            for j in range(len(short_strikes_T)):
                    X2[i][j] = np.maximum(K2[i] - short_strikes_T[j],0)



        from sklearn.linear_model import LinearRegression

        model_regression2 =  LinearRegression()
        model_regression2.fit(X2, Zi)



        Weights_for_options_T = model_regression2.coef_
        cash_T = model_regression2.intercept_
        print("Coefficients:", Weights_for_options_T)

        print("Intercept:",cash_T )

#         plt.plot(K1,cash_T+[np.dot(Weights_for_options_T ,X[i]) for i in range(X.shape[0])],label="Hedge portfolio")
#         plt.plot(K1,Zi,label='target')
#         plt.legend()
#         plt.show()
#         plt.close()

        print(f"\n cash={cash_t1 + cash_T}")
        
        
        if seed != 136:
            x0 = None
        else: 
            x0 = list([cash_t1 + cash_T]) +list(Weights_for_options_t1)+list(Weights_for_options_T)
            
        if __name__ == "__main__":

            no_of_options_t1,no_of_options_T = len(Weights_for_options_t1), len(Weights_for_options_T)
            truncation_range = 2


            result_data_no_M = run_experiment_no_M(solver="gurobi",#"pulp"
                truncation_range=truncation_range,
                N=N,
                no_of_options_t1=no_of_options_t1,
                no_of_options_T=no_of_options_T,
                short_strikes_t1=short_strikes_t1,
                short_strikes_T=short_strikes_T,                                   
                epsilon= 0,#0.00000001
                M_bound= 0,
                choice="non-uniform",
                x0 = x0,  
                seed =seed,
                bounds = bounds                                       
            )



            # Make a similar dictionary
            run_dict_no_M = {
                "Solver": "gurobi",
                "M_coeff": "No_M",   # or 0, or None—some label
                "Truncation_range": truncation_range,
                "N_initial": result_data_no_M["N_initial"],
                "N": result_data_no_M["N"],
                "no_of_options_t1": result_data_no_M["No_of_options_t1"],
                "no_of_options_T": result_data_no_M["No_of_options_T"],
                "epsilon": 0.0,
                "Optimal_weights": result_data_no_M["w_opt"],
                "Final_value": result_data_no_M["final_value"],
                "P_matrix": result_data_no_M["p_matrix"],
                "Dual_weights": list([cash_t1 + cash_T]) + list(Weights_for_options_t1)+list(Weights_for_options_T)
             }
            print("========== Experiment Complete ==========")
            print("Optimal Weights:", result_data_no_M["w_opt"])
            print("Final Value from min-max:", result_data_no_M["final_value"])

        #plotting the conditional target option and hedge portfolio at short maturity
        price = np.zeros(len(K1))
        BS_price = np.zeros(len(K1))
        hedge = np.zeros(len(K1))
        tolerance = 1e-17
        Pr_opt = result_data_no_M["p_matrix"]
        weights_opt = result_data_no_M["w_opt"]


        #print(index)
        for i in range(len(K1)):
            #\sum_{j}p_{i,j}y_j/\alpha_i
            if marg[0][i] < tolerance:
                print(f"marginal below tolerance:{marg[0][i]}")
                print(sum(Pr_opt[i,j] * Asian_option_payoff(K1[i],K2[j],K) for j in range(len(K2)))/marg[0][i])
                price[i] = np.nan
                hedge_T_list = [sum(Pr_opt[i,j] * max(K2[j]-short_strikes_T[l],0) for j in range(len(K2)))/marg[0][i]
                           for l in range(len(short_strikes_T))]
                hedge_T_sum = np.dot(result_data_no_M["weights_T"],hedge_T_list)
            else:
                price[i] = sum(Pr_opt[i,j] * Asian_option_payoff(K1[i],K2[j],K)  for j in range(len(K2)))/marg[0][i]   
                hedge_T_list = [sum(Pr_opt[i,j] * max(K2[j]-short_strikes_T[l],0) for j in range(len(K2)))/marg[0][i]
                           for l in range(len(short_strikes_T))]
                hedge_T_sum = np.dot(result_data_no_M["weights_T"],hedge_T_list)    
            #Asian option price at short maturity t1 for the given asian option payoff can be computed using the Black-Scholes price


            if 2*K -K1[i] >= 0:
                    BS_price[i] = 0.5 * BS_call(K1[i],-K1[i] + 2 *K,T_GRID[1],T,sigma,r)
            else:
                    BS_price[i] = K1[i] - K



            hedge[i] =  weights_opt[0] + sum( weights_opt[_+1] * max(K1[i]-short_strikes_t1[_],0) 
                                             for _ in range(no_of_options_t1)) + hedge_T_sum   

        plt.plot(K1,price,label='target')
        plt.plot(K1,BS_price,label='BS target price')
        plt.plot(K1,hedge,label=f'hedge portfolio,')
        plt.xlabel('Stock price at short_maturity')
        plt.legend()
        #         plt.savefig(f"Plot_for_{no_of_options}_options_and_N_{N}.eps",format="eps",dpi =300)
        plt.show()
        plt.close()
      
        
        results_for_varying_seed.append(run_dict_no_M)
    
        print("======== Entire Experiment is Complete ======")
    
        #convert to dataframe
        df_varying_seed2 = pd.DataFrame( results_for_varying_seed)

# %%
df_varying_seed2

# %%
print(df_varying_seed)


# %%
pd.concat([df_varying_seed2])

# %%
import gurobipy as gp
from gurobipy import GRB, quicksum
import numpy as np

def solve_max_problem_for_superhedge(M_bound,
    K1,
    K2,
    cash,  #total cash position in the superhedge
    Weights_t1,  #weights corresponding to options with maturity t_1 
    Weights_T, #weights corresponding to options with maturity T 
    short_strikes_t1, 
    short_strikes_T,                                      
    target_strike,
    marg, Epsilon
):
    
    # Create a Gurobi model
    model = gp.Model("Upper-Bound-Problem-RowSpecificM")
    model.setParam('OutputFlag', 0)

    N = len(K1)
    
    no_of_options_t1 = len(short_strikes_t1)
    no_of_options_T = len(short_strikes_T)
    
    # Decision variables
    X = model.addVars(N, N, lb=0, ub=1, vtype=GRB.CONTINUOUS, name="X")
    P_slack = model.addVars(N, lb=0, vtype=GRB.CONTINUOUS, name="P_slack")
    B = model.addVars(N, vtype=GRB.BINARY, name="B")


    # Objective: Maximize sum of P_slack
    model.setObjective(quicksum(P_slack[i] for i in range(N)), GRB.MAXIMIZE)

    
  

    #Calculate the cash position value: it should be the difference between the target option price and the hedge_portfolio value at 0 with only options
   
    
     
    for i in range(N):
         # The hedging_error expression
        hedging_error = (quicksum(X[i, j] * (Asian_option_payoff(K1[i],K2[j],target_strike) 
                                            -  quicksum(
                                Weights_T[k] * max(K2[j] - short_strikes_T[k], 0)
                                for k in range(no_of_options_T) #options with maturity T 
                              )
                            )  for j in range(N))
                        - marg[0][i] * (
                            cash
                            + quicksum(
                                Weights_t1[l] * max(K1[i] - short_strikes_t1[l], 0)
                                for l in range(no_of_options_t1)
                            )#options with short maturity t1
                        )
                    )
        # -- Absolute value constraints:
        # a) hedging_error <= P_slack[i]
        model.addConstr(hedging_error <= P_slack[i], f"modulus_1_{i}")

        # b) hedging_error >= -P_slack[i]
        model.addConstr(hedging_error >= -P_slack[i], f"modulus_2_{i}")

        # d) hedging_error *(1 - 2*B[i]) == P_slack[i]
        model.addConstr(hedging_error *(1 - 2*B[i]) == P_slack[i], f"modulus_3_{i}")
   
   
    # Marginal constraints
    for i in range(N):
        model.addConstr(quicksum(X[i, j] for j in range(N)) == marg[0][i], f"time1_{i}")

    for j in range(N):
        model.addConstr(quicksum(X[i, j] for i in range(N)) == marg[1][j], f"time2_{j}")

    # Martingale constraints 
   
    for i in range(N):
        model.addConstr(quicksum(X[i, j]*(K2[j] - K1[i]) for j in range(N)) == 0, f"martingale_{i}")
    
    model.setParam('NonConvex', 2)

    # Solve the model
    model.optimize()

    if model.status != GRB.OPTIMAL:
        return {
            "call_value": float("inf"),
            "Status": model.status,
            "p_matrix": None,
            "P_slack": None,
            "B": None,
#             "Delta": None
        }
    
 
    # 6) Extract solution
    p_matrix = np.zeros((N, N))
    for i in range(N):
        for j in range(N):
            p_matrix[i, j] = X[i, j].X

    p_slack_array = np.array([P_slack[i].X for i in range(N)])
    b_array       = np.array([B[i].X          for i in range(N)])
#     delta_array   = np.array([Delta[i].X      for i in range(N)])
    call_value    = model.objVal

    return {
        "N_initial": N,
        "call_value": call_value,
        "Status": "Optimal",
        "p_matrix": p_matrix,
        "P_slack": p_slack_array,
        "B": b_array,
        
#         "Delta": delta_array,
       
    }


# %%
df_varying_N

# %%
df_results_N = pd.read_pickle("Results_for_varying_N_BS_Asian_T.pkl")
dual_weights_list = df_results_N["Dual_weights"].to_list()

df_varying_N_superhedge = []
for i, weights in enumerate(dual_weights_list):
    
    N = df_results_N["N_initial"][i]
    disc_points_new, call_prices_array_new, marg = get_disc_points_and_marginals(
                    truncation_range=truncation_range, N=N, choice="non-uniform"
                )
    K1 = disc_points_new[0]
    K2 = disc_points_new[1]
    M_bound = 0
    
    short_strikes_t1 = K1
    short_strikes_T = K2
    
    Weights_t1 = weights[:len(short_strikes_t1)]
    Weights_T = weights[len(short_strikes_t1):]
    
    cash = 0
    Epsilon = 0
    truncation_range = df_results_N["Truncation_range"][i]
    worst_error_for_superhedge = solve_max_problem_for_superhedge( M_bound,
        K1,
        K2,
        cash,
        Weights_t1,
        Weights_T,
        short_strikes_t1,
        short_strikes_T,
        K,
        marg, Epsilon
       )
    
   
    
    
    #plotting the conditional target option and hedge portfolio at short maturity
    price = np.zeros(len(K1))
    BS_price = np.zeros(len(K1))
    hedge = np.zeros(len(K1))
    tolerance = 1e-17
    Pr_opt = worst_error_for_superhedge["p_matrix"]
    
    
    
    #get the corresponding optimal weights from the min_max problem
    weights_opt_min_max = df_results_N["Optimal_weights"][i]
    
    weights_opt_options  = weights_opt_min_max[1:]
    
    print("Weights_min_max" ,  weights_opt_min_max)
    
    
    #compute the hedging error for our hedge portfolio with the worst p_ij's for the dual problem
    
    hedging_error = 0
    #print(index)
    for i in range(len(K1)):
        #\sum_{j}p_{i,j}y_j/\alpha_i
        if marg[0][i] < tolerance:
            print(f"marginal below tolerance:{marg[0][i]}")
            print(sum(Pr_opt[i,j] * Asian_option_payoff(K1[i],K2[j],K) for j in range(len(K2)))/marg[0][i])
            
            
            price[i] = np.nan
            
            hedge_T_list = [sum(Pr_opt[i,j] * max(K2[j]-short_strikes_T[l],0) for j in range(len(K2)))/marg[0][i]
                       for l in range(len(short_strikes_T))]
            
            
            hedge_T_sum = np.dot(weights_opt_options[len(short_strikes_t1):],hedge_T_list)
            
            
            
            hedge_T_list_2 = [sum(Pr_opt[i,j] * max(K2[j]-short_strikes_T[l],0) for j in range(len(K2)))
                       for l in range(len(short_strikes_T))]
            hedge_T_sum_2 = np.dot(weights_opt_options[len(short_strikes_t1):],hedge_T_list)
       
    
        else:
            price[i] = sum(Pr_opt[i,j] * Asian_option_payoff(K1[i],K2[j],K)  for j in range(len(K2)))/marg[0][i] 
            
            
            hedge_T_list = [sum(Pr_opt[i,j] * max(K2[j]-short_strikes_T[l],0) for j in range(len(K2)))/marg[0][i]
                       for l in range(len(short_strikes_T))]
            
            
            hedge_T_sum = np.dot(weights_opt_options[len(short_strikes_t1):],hedge_T_list)   
            
            
            
            hedge_T_list_2 = [sum(Pr_opt[i,j] * max(K2[j]-short_strikes_T[l],0) for j in range(len(K2)))
                       for l in range(len(short_strikes_T))]
            hedge_T_sum_2 = np.dot(weights_opt_options[len(short_strikes_t1):],hedge_T_list_2)
            
            
            price_2 = sum(Pr_opt[i,j] * Asian_option_payoff(K1[i],K2[j],K)  for j in range(len(K2)))
        #Asian option price at short maturity t1 for the given asian option payoff can be computed using the Black-Scholes price


        if 2*K -K1[i] >= 0:
             BS_price[i] = 0.5 * BS_call(K1[i],-K1[i] + 2 *K,T_GRID[1],T,sigma,r)
        else:
             BS_price[i] = K1[i] - K


       
        hedge[i] =  weights_opt_min_max[0] + sum( weights_opt_options[l] * max(K1[i]-short_strikes_t1[l],0) 
                                         for l in range(len(short_strikes_t1))) + hedge_T_sum 
        
        
        hedge2 =  weights_opt_min_max[0] + sum( weights_opt_options[l] * max(K1[i]-short_strikes_t1[l],0) 
                                         for l in range(len(short_strikes_t1)))
        
        
        hedging_error += abs(price_2 - hedge_T_sum_2 -  marg[0][i]* hedge2 )
        
     #compute the optimal cash position 
        
        
        
        
    plt.plot(K1,price,label='target')
    plt.plot(K1,BS_price,label='BS target price')
    plt.plot(K1,hedge,label=f'hedge portfolio,')
    plt.xlabel('Stock price at short_maturity')
    plt.legend()
    #         plt.savefig(f"Plot_for_{no_of_options}_options_and_N_{N}.eps",format="eps",dpi =300)
    plt.show()
    plt.close()
    worst_error_for_superhedge.update({"Hedge_error_minmax":hedging_error})
    df_varying_N_superhedge.append(worst_error_for_superhedge)
pd.DataFrame(df_varying_N_superhedge)
    


# %%
print(short_strikes_T)
for i in range(len(K1)):
        #\sum_{j}p_{i,j}y_j/\alpha_i
        if marg[0][i] < tolerance:
            print(f"marginal below tolerance:{marg[0][i]}")
            print(sum(Pr_opt[i,j] * Asian_option_payoff(K1[i],K2[j],K) for j in range(len(K2)))/marg[0][i])
            price[i] = np.nan
            hedge_T_list = [sum(Pr_opt[i,j] * max(K2[j]-short_strikes_T[l],0) for j in range(len(K2)))/marg[0][i]
                       for l in range(len(short_strikes_T))]
            hedge_T_sum = np.dot(result_data_no_M["weights_T"],hedge_T_list)
        else:
            price[i] = sum(Pr_opt[i,j] * Asian_option_payoff(K1[i],K2[j],K)  for j in range(len(K2)))/marg[0][i]   
            hedge_T_list = [sum(Pr_opt[i,j] * max(K2[j]-short_strikes_T[l],0) for j in range(len(K2)))/marg[0][i]
                       for l in range(len(short_strikes_T))]
            hedge_T_sum = np.dot(result_data_no_M["weights_T"],hedge_T_list)  

# %%
def compute_objective(cash, weights_t1,weights_T, p_matrix, K1, K2, short_strikes_t1, short_strikes_T, target_strike, alpha):
    """
    Computes the value of the objective function(hedging error) for given weights, p-matrix, short_strikes etc.
    """
    obj_val = 0.0
    n_timepoint_1 = len(K1)
    n_timepoint_2 = len(K2)

    for i in range(n_timepoint_1):
        payoff_target = 0.0
        for j in range(n_timepoint_2):
            payoff_target += p_matrix[i, j] * (Asian_option_payoff(K1[i], K2[j], target_strike)
                              -  sum(
                weights_T[l] * max(K2[j] - short_strikes_T[l], 0)
                for l in range(len(short_strikes_T))
                              )
                                              )

        # Hedge payoff
        payoff_hedge = alpha[i] * (
           cash + sum(
                weights_t1[l] * max(K1[i] - short_strikes_t1[l], 0)
                for l in range(len(short_strikes_t1))
            )
        )

        obj_val += abs(payoff_target - payoff_hedge)

    return obj_val


#compute the objective values with the intermediate weights and probability matrix from the MOT problem

objective_value_list = df_log_results["Objective value (outer)"]
p_matrix_list = df_log_results["p_matrix"]
Weights_t1_list = df_log_results["Weights_t1"]
Weights_T_list = df_log_results["Weights_T"]



def compute_cash(Weights_t1_list, Weights_T_list, p_matrix,K1,K2,short_call_t1,short_call_T):
    """
    Compute the cash position for a given set of weights without cash
    """
   
    n_timepoint_1 = len(K1)
    n_timepoint_2 = len(K2)
    cash = sum(p_matrix[i,j]* Asian_option_payoff(K1[i],K2[j],K)  for i in range(n_timepoint_1)
                                              for j in range(n_timepoint_2)) \
               - np.dot(Weights_t1_list, short_call_t1)\
              - np.dot(Weights_T_list, short_call_T)
    return cash

     
        


# %%


hedge_list_MOT = []

for i in range(len(Weights_t1_list)):
    
    cash_position = compute_cash(Weights_t1_list[i], Weights_T_list[i],p_matrix_list[i],K1,K2,
                                 short_call_t1, short_call_T)
    
    
    #compute the hedging error using the intermediate weights in the min-max problem and the probability matrix from MOT problem
    hedge_list_MOT.append(compute_objective(cash_position, Weights_t1_list[i],Weights_T_list[i],
                                            data_MOT['P_matrix'], K1, K2, short_strikes_t1, short_strikes_T, K, marg[0]))


# %% [markdown]
# **EXPERIMENT FOR CHECKING THE EFFECT OF INCREASING NUMBER OF DISCRETIZATION POINTS**

# %%
if __name__ == "__main__":
    N_values = [4,6,8,10,12,14,16,18,20]
    
    
    #choice of paramter values
    truncation_range=2
    no_of_options_t1=4
    no_of_options_T =4
    
    short_strikes_t1 = short_strike_range[:no_of_options_t1]
    short_strikes_T = short_strike_range[:no_of_options_T]
    #list to store the results
    results_for_varying_N = []
    
    for N in N_values:
        print(f"\n========== Running the experiment for N={N} ==========")
        result_data_no_M = run_experiment_no_M(solver="gurobi",#"pulp"
              truncation_range = truncation_range,
              N = N,
              no_of_options_t1 = no_of_options_t1,
              no_of_options_T =  no_of_options_T,
              short_strikes_t1 = short_strikes_t1,
              short_strikes_T = short_strikes_T,                                  
              epsilon = 0,
              M_bound = 0,
             choice="non-uniform"
              )
        
         # Make a dictionary for the entries
        run_dict_no_M = {
             "Solver": "gurobi",
             "M_coeff": "No_M",   
             "Truncation_range": truncation_range,
             "N_initial": result_data_no_M["N_initial"],
             "N": result_data_no_M["N"],
             "no_of_options_t1": result_data_no_M["No_of_options_t1"],
             "no_of_options_T": result_data_no_M["No_of_options_T"],
             "epsilon": 0.0,
             "Optimal_weights": result_data_no_M["w_opt"],
             "Final_value": result_data_no_M["final_value"],
             "P_matrix": result_data_no_M["p_matrix"]
              }
        print(f"\n ========== Experiment Complete for N_initial ={N}==========")
        print("Optimal Weights with cash:", result_data_no_M["w_opt"])
        print("Final Value from min-max:", result_data_no_M["final_value"])
        results_for_varying_N.append(run_dict_no_M)
    
    print("======== Entire Experiment is Complete ======")
    
    #convert to dataframe
    df_varying_N = pd.DataFrame( results_for_varying_N)
    
    #store in a pickle file
    
#     outfile = "Results_for_varying_N_Asian_option.pkl"
    
#     df_varying_N.to_pickle(outfile,index=False)
    
#     print(f"Results stored in {outfile}")    
        


# %%
#store in a pickle file
    
outfile = "Results_for_varying_N_Asian_option_T.pkl"
    
df_varying_N.to_pickle(outfile)
    
print(f"Results stored in {outfile}")    
        


# %%
#plotting the results of the min-max experiment

plt.plot(df_varying_N["N_initial"],df_varying_N["Final_value"])
plt.xlabel("No of discretization points")
plt.ylabel("Objective value")
plt.title("Effect of no. of discretization points on the objective value")
plt.show()
plt.close()

# %% [markdown]
# **EXPERIMENT TO STUDY THE EFFECT OF THE OPTIMAL WEIGHTS FOR INCREASING NUMBER OF DISCRETIZATION POINTS**

# %%
pd.read_pickle("Results_for_varying_N_Asian_option_T.pkl")

# %%
#### SIMULATE STOCK PATHS TO COMPUTE THE QUANTILES ####
if __name__ == "__main__" : 
    Nsim = 10000
    Nsteps = timepoints * 10
    delta_t = 1/Nsteps

    stock_paths = np.zeros([Nsim,Nsteps+1])
    stock_paths[:,0] = stock
    np.random.seed(2)
    Z1 = np.random.normal(size=[Nsim,Nsteps])

    time_indices = [] # list to store the corresponding time-points at which the stock paths are beong calculated
    time_indices.append(0)

    for i in range(Nsteps):
        stock_paths[:,i+1] = stock_paths[:,i] * np.exp((r - 0.5 * (sigma **2)) * delta_t \
            + sigma * np.sqrt(delta_t) * Z1[:,i])
    
        time_indices.append(delta_t * (i + 1))

    
    index1 = time_indices.index(T_GRID[1]) #index corresponding to short maturity
    index2 = time_indices.index(T) #index corresponding to target maturity

    print(f"Index corresponding to short maturity {time_indices[index1]} :{index1}")
    
    print(f"Index corresponding to target maturity {time_indices[index2]} :{index2}")
    
    #plot the stock paths
    t_paths = np.linspace(0, Nsteps, Nsteps+1)
    plt.plot(t_paths,stock_paths.transpose())
    plt.show()
    plt.close()
    
    #print the intermediate time points
    print(f"Time indices:\n {time_indices}")
    

#COMPUTE THE L2 norm of the difference between the hedge portfolio values with the last hedge portfolio value

results_list_for_varying_N = pd.read_pickle("Results_for_varying_N_Asian_option.pkl")

optimal_weights_N_list = results_list_for_varying_N["Optimal_weights"].to_list()
print(optimal_weights_N_list)
value = []

for entry in optimal_weights_N_list:
    short_strikes = short_strike_range[:len(entry)-1]
    
    #compute the hedge portfolio value for the given weight combinations
    hedge_portfolio = entry[0] + np.sum([entry[i+1] * np.maximum(stock_paths[:,index1]-short_strikes[i],0)
                                         for i in range(len(short_strikes))],axis=0)
    value.append(hedge_portfolio)

def l_2_norm(x):
    """
    Compute the l_2_norm of a vectore x
    """
    sum_of_squares = 0
    for i in x:
        sum_of_squares += i**2
    norm = np.sqrt(sum_of_squares)
    return norm

np.shape(np.array(value))
rows,columns = np.shape(np.array(value))


#list to store the L2 norm of the differences
l_2_norm_of_difference_list = []
for i in range(rows):
    #compute the L2 norm of the difference between the hedge portfolio with first optimal weights and the other combinations
    l_2_norm_of_difference_list.append(l_2_norm(value[i]-value[-1]))

# %%
N_list = results_list_for_varying_N["N_initial"].to_list()
plt.plot(N_list,l_2_norm_of_difference_list,'b-*')
plt.xlabel("Number of discretization points")
plt.xticks(N_list)
plt.ylabel("L2 norm of the difference")
# plt.legend()
plt.show()
plt.close()



# %%
if __name__ == "__main__":
    N_values = [4,6,8,10,12,14,16,18,20]
    
    
    #choice of paramter values
    truncation_range=2
    no_of_options_t1=len(K1)
    no_of_options_T =len(K2)
    
    short_strikes_t1 = K1
    short_strikes_T = K2
    #list to store the results
    results_for_varying_N = []
    
    for N in N_values:
        print(f"\n========== Running the experiment for N={N} ==========")
        result_data_no_M_disc = run_experiment_no_M(solver="gurobi",#"pulp"
              truncation_range = truncation_range,
              N = N,
              no_of_options_t1 = no_of_options_t1,
              no_of_options_T =  no_of_options_T,
              short_strikes_t1 = short_strikes_t1,
              short_strikes_T = short_strikes_T,                                  
              epsilon = 0,
              M_bound = 0,
             choice="non-uniform"
              )
        
         # Make a dictionary for the entries
        run_dict_no_M_disc = {
             "Solver": "gurobi",
             "M_coeff": "No_M",   
             "Truncation_range": truncation_range,
             "N_initial": result_data_no_M["N_initial"],
             "N": result_data_no_M["N"],
             "no_of_options_t1": result_data_no_M["No_of_options_t1"],
             "no_of_options_T": result_data_no_M["No_of_options_T"],
             "epsilon": 0.0,
             "Optimal_weights": result_data_no_M["w_opt"],
             "Final_value": result_data_no_M["final_value"],
             "P_matrix": result_data_no_M["p_matrix"]
              }
        print(f"\n ========== Experiment Complete for N_initial ={N}==========")
        print("Optimal Weights with cash:", result_data_no_M["w_opt"])
        print("Final Value from min-max:", result_data_no_M["final_value"])
        results_for_varying_N.append(run_dict_no_M)
    
    print("======== Entire Experiment is Complete ======")
    
    #convert to dataframe
    df_varying_N = pd.DataFrame( results_for_varying_N)
    
    #store in a pickle file
    
#     outfile = "Results_for_varying_N_Asian_option.pkl"
    
#     df_varying_N.to_pickle(outfile,index=False)
    
#     print(f"Results stored in {outfile}")    
        


# %%
#helper function
def run_one_experiment_for_given_N(N=None,
              truncation_range = None,
              no_of_options_t1 = None,
              no_of_options_T =  None,
              short_strikes_t1 = None,
              short_strikes_T = None,                                  
              epsilon = None,
              M_bound = None,
             choice= None ):
    
    result_data_no_M = run_experiment_no_M(solver="gurobi",#"pulp"
              truncation_range = truncation_range,
              N = N,
              no_of_options_t1 = no_of_options_t1,
              no_of_options_T =  no_of_options_T,
              short_strikes_t1 = short_strikes_t1,
              short_strikes_T = short_strikes_T,                                  
              epsilon = 0,
              M_bound = 0,
             choice="non-uniform"
              )
        
         # Make a dictionary for the entries
    run_dict_no_M = {
             "Solver": "gurobi",
             "M_coeff": "No_M",   
             "Truncation_range": truncation_range,
             "N_initial": result_data_no_M["N_initial"],
             "N": result_data_no_M["N"],
             "no_of_options_t1": result_data_no_M["No_of_options_t1"],
             "no_of_options_T": result_data_no_M["No_of_options_T"],
             "epsilon": 0.0,
             "Optimal_weights": result_data_no_M["w_opt"],
             "Final_value": result_data_no_M["final_value"],
             "P_matrix": result_data_no_M["p_matrix"]
              }
        print(f"\n ========== Experiment Complete for N_initial ={N}==========")
        print("Optimal Weights with cash:", result_data_no_M["w_opt"])
        print("Final Value from min-max:", result_data_no_M["final_value"])
        return run_dict_no_M


# %%
def run_one_experiment_for_N(N, solver="gurobi", truncation_range=2,
                             no_of_options_t1=None, no_of_options_T=None,
                             short_strikes_t1=None, short_strikes_T=None,
                             epsilon=0, M_bound=0, choice="non-uniform"):
    """
    Runs run_experiment_no_M for one value of N, returning a dictionary
    with all relevant results (w_opt, final_value, etc.) plus the chosen N.
    """
    
    result_data = run_experiment_no_M(
        solver=solver,
        truncation_range=truncation_range,
        N=N,
        no_of_options_t1=no_of_options_t1,
        no_of_options_T=no_of_options_T,
        short_strikes_t1=short_strikes_t1,
        short_strikes_T=short_strikes_T,
        epsilon=epsilon,
        M_bound=M_bound,
        choice=choice
    )

    # Build a dictionary
    run_dict = {
        "Solver": solver,
        "M_coeff": "No_M",
        "Truncation_range": truncation_range,
        "N_initial": result_data["N_initial"],
        "N": result_data["N"],
        "no_of_options_t1": result_data["No_of_options_t1"],
        "no_of_options_T": result_data["No_of_options_T"],
        "epsilon": epsilon,
        "Optimal_weights": result_data["w_opt"],
        "Final_value": result_data["final_value"],
        "P_matrix": result_data["p_matrix"]
    }

    print(f"\n=== Completed run_experiment_no_M for N={N} ===")
    print("Final Weights (with cash):", result_data["w_opt"])
    print("Final Value from min-max:", result_data["final_value"])
    return run_dict


# %%
if __name__ == "__main__":
    import pandas as pd

#     N_values = [4, 6, 8, 10, 12, 14, 16, 18, 20]
    N_values = [6, 8, 10, 12, 14, 16, 18]
    # Choice of parameter values (these are global)
    truncation_range = 2
    no_of_options_t1 = len(K1)
    no_of_options_T  = len(K2)
    short_strikes_t1 = K1
    short_strikes_T  = K2

    results_for_varying_N = []

    for N in N_values:
        print(f"\n=== Running experiment for N={N} ===")
        run_dict = run_one_experiment_for_N(
            N=N,
            solver="gurobi",
            truncation_range=truncation_range,
            no_of_options_t1=no_of_options_t1,
            no_of_options_T=no_of_options_T,
            short_strikes_t1=short_strikes_t1,
            short_strikes_T=short_strikes_T,
            epsilon=0,
            M_bound=0,
            choice="non-uniform"
        )
        results_for_varying_N.append(run_dict)

    print("=== All N experiments complete ===")
#     from joblib import Parallel, delayed
#     results_for_varying_N = Parallel(n_jobs=-1)(
#     delayed(run_one_experiment_for_N)(N=n, no_of_options_t1= no_of_options_t1, no_of_options_T= no_of_options_T,
#                              short_strikes_t1=short_strikes_t1, short_strikes_T=short_strikes_T)
#     for n in N_values
#      )
    # Convert to DataFrame
    df_varying_N = pd.DataFrame(results_for_varying_N)
    # df_varying_N.to_pickle("Results_for_varying_N_Asian_option.pkl", index=False)
    # print("Saved results to Results_for_varying_N_Asian_option.pkl")

    # Optional: Display the DataFrame
    print(df_varying_N[["N", "Final_value"]])


# %%
#plot the conditional target price function and the corresponding hedge portfolio for each of the discretization points

N_initial_list = df_varying_N["N_initial"].to_list()
P_matrix_list = df_varying_N["P_matrix"].to_list()
Optimal_weights_list = df_varying_N["Optimal_weights"].to_list()
No_of_options_t1_list = df_varying_N["no_of_options_t1"].to_list()
No_of_options_T_list = df_varying_N["no_of_options_T"].to_list()

for l in range(len(N_initial_list)):
    disc_points_new, call_prices_array_new, marg = get_disc_points_and_marginals( truncation_range=2,\
                                                                                N=N_initial_list[l],choice="non-uniform")
    

    K1 = disc_points_new[0]
    K2 = disc_points_new[1]
    
    price = np.zeros(len(K1))
    BS_price = np.zeros(len(K1))
    hedge = np.zeros(len(K1))
    tolerance = 1e-17
    Pr_opt = P_matrix_list[l]
    current_optimal_weights = Optimal_weights_list[l] 
    short_strikes_t1 = K1
    short_strikes_T = K2
    no_of_options
    #print(index)
    print(f"\n =========Plot for N_initial = {N_initial_list[l]} disc points=========\n")
    for i in range(len(K1)):
        #\sum_{j}p_{i,j}y_j/\alpha_i
        if marg[0][i] < tolerance:
            print(f"marginal below tolerance:{marg[0][i]}")
            print(sum(Pr_opt[i,j] * Asian_option_payoff(K1[i],K2[j],K) for j in range(len(K2)))/marg[0][i])
            price[i] = np.nan
            hedge_T_list = [sum(Pr_opt[i,j] * max(K2[j]-short_strikes_T[l],0) for j in range(len(K2)))/marg[0][i]
                   for l in range(len(short_strikes_T))]
            hedge_T_sum = np.dot(current_optimal_weights[No_of_options_t1:],hedge_T_list)
        else:
            price[i] = sum(Pr_opt[i,j]*Asian_option_payoff(K1[i],K2[j],K)  for j in range(len(K2)))/marg[0][i]   
            hedge_T_list = [sum(Pr_opt[i,j] * max(K2[j]-short_strikes_T[l],0) for j in range(len(K2)))/marg[0][i]
                   for l in range(len(short_strikes_T))]
            hedge_T_sum = np.dot(current_optimal_weights[No_of_options_t1:],hedge_T_list)
        #Asian option price at short maturity t1 for the given asian optionpayoff can be computed using the Black-Scholes price
            
        if 2*K -K1[i] >= 0:
            BS_price[i] = 0.5 * BS_call(K1[i],-K1[i] + 2 *K,T_GRID[1],T,sigma,r)
        else:
            BS_price[i] = K1[i] - K
          
          
        hedge[i] =  current_optimal_weights[0] + sum( current_optimal_weights[_+1] * 
                                                     max(K1[i]-short_strikes[_],0) for _ in range(no_of_options_t1))\
              + hedge_T_sum

    plt.plot(K1[2:-3],price[2:-3],label='target')
    plt.plot(K1[2:-3],BS_price[2:-3],label='BS target price')
    plt.plot(K1[2:-3],hedge[2:-3],label=f'hedge portfolio,')
    plt.xlabel('Stock price at short_maturity')
    plt.legend()
#         plt.savefig(f"Plot_for_{no_of_options}_options_and_N_{N}.eps",format="eps",dpi =300)
    plt.show()
    plt.close()
        


# %%
#plotting the conditional target option and hedge portfolio at short maturity
price = np.zeros(len(K1))
BS_price = np.zeros(len(K1))
hedge = np.zeros(len(K1))
tolerance = 1e-17
Pr_opt = result_data_no_M["p_matrix"]
short_strikes_t1 = short_strike_range[:no_of_options_t1]
short_strikes_T = short_strike_range[:no_of_options_T]
weights_opt = result_data_no_M["w_opt"]


#print(index)
for i in range(len(K1)):
    #\sum_{j}p_{i,j}y_j/\alpha_i
    if marg[0][i] < tolerance:
        print(f"marginal below tolerance:{marg[0][i]}")
        print(sum(Pr_opt[i,j] * Asian_option_payoff(K1[i],K2[j],K) for j in range(len(K2)))/marg[0][i])
        price[i] = np.nan
        hedge_T_list = [sum(Pr_opt[i,j] * max(K2[j]-short_strikes_T[l],0) for j in range(len(K2)))/marg[0][i]
                   for l in range(len(short_strikes_T))]
        hedge_T_sum = np.dot(result_data_no_M["weights_T"],hedge_T_list)
    else:
        price[i] = sum(Pr_opt[i,j] * Asian_option_payoff(K1[i],K2[j],K)  for j in range(len(K2)))/marg[0][i]   
        hedge_T_list = [sum(Pr_opt[i,j] * max(K2[j]-short_strikes_T[l],0) for j in range(len(K2)))/marg[0][i]
                   for l in range(len(short_strikes_T))]
        hedge_T_sum = np.dot(result_data_no_M["weights_T"],hedge_T_list)    
    #Asian option price at short maturity t1 for the given asian option payoff can be computed using the Black-Scholes price
            
    
    if 2*K -K1[i] >= 0:
            BS_price[i] = 0.5 * BS_call(K1[i],-K1[i] + 2 *K,T_GRID[1],T,sigma,r)
    else:
            BS_price[i] = K1[i] - K
    
           
            
    hedge[i] =  weights_opt[0] + sum( weights_opt[_+1] * max(K1[i]-short_strikes_t1[_],0) 
                                     for _ in range(no_of_options_t1)) + hedge_T_sum   

plt.plot(K1,price,label='target')
plt.plot(K1,BS_price,label='BS target price')
plt.plot(K1,hedge,label=f'hedge portfolio,')
plt.xlabel('Stock price at short_maturity')
plt.legend()
#         plt.savefig(f"Plot_for_{no_of_options}_options_and_N_{N}.eps",format="eps",dpi =300)
plt.show()
plt.close()
        

# %% [markdown]
# **EXPERIMENT WITH INCREASING NUMBER OF OPTIONS**

# %%
#EXPERIMENT FOR DIFFERENT NUMBER OF OPTIONS

import pandas as pd
import pickle

if __name__ == "__main__": 
    # Range of values for n
    N = 16
    
    log_for_inc_no_of_options = []  # Stores all results
    
    # Initial choices for parameters
    truncation_range = 2
    
    epsilon = 0
    
    
    M_bound = 0
    
    
    solver_choice = "gurobi"
    
    # 1) Build grid & marginals
    disc_points_new, call_prices_array_new, marg = get_disc_points_and_marginals(
            truncation_range=truncation_range, N=N, choice="non-uniform"
        )
    K1 = disc_points_new[0]
    K2 = disc_points_new[1]
   
    for no_of_options in range(1, len(short_strike_range)):
        print(f"\n=== Running the experiment for no_of_options = {no_of_options} ===")
        # 2) Pick short strikes
        short_strikes = short_strike_range[:no_of_options]
        print(f"Short strikes: {short_strikes}")

        # 3) Compute target call & short calls
#         target_call = get_target_call(marg, disc_points_new, K)
        short_call = get_short_call(T_GRID, T_GRID[1], no_of_options, marg, disc_points_new, short_strikes)
    
    
    
        
        result_data = run_experiment_no_M(solver="gurobi",#"pulp"
              truncation_range = truncation_range,
              N = N,
              no_of_options = no_of_options,
              epsilon = epsilon,
              M_bound = M_bound,
             choice="non-uniform"
              )
       
        print("========== Experiment Complete ==========")
        print("Optimal Weights:", result_data["w_opt"])
        print("Final Value from min-max:", result_data["final_value"])
    
        # Extract the final objective value and optimal weights
        current_objective_value = result_data["final_value"]
        current_optimal_weights = result_data["w_opt"]

        # If this is not the first iteration, compare with the previous n
        if len( log_for_inc_no_of_options) > 0:
            previous_log = log_for_inc_no_of_options[-1]  # Get last entry
            previous_objective_value = previous_log["Objective_value"]
            previous_optimal_weights = previous_log["Optimal_weights"]

            # If previous objective value is lower, use previous weights and append a zero
            if previous_objective_value < current_objective_value:
                print(f"\nObjective value for {no_of_options-1} options was lower\n")
                
                #compute the objective value with previous combination of weights and current p_{i,j}
                objective_value_with_prev_weights_and_current_p_ij = compute_objective( previous_optimal_weights,
                                                                     result_data["p_matrix"],
                                                                     K1,
                                                                     K2,
                                                                     short_strikes[:-1],
                                                                     K,
                                                                     marg[0])
                print(f"Objective value for previous weights and current p_ij:{objective_value_with_prev_weights_and_current_p_ij }")
                current_objective_value = previous_objective_value  # Keep the lower value
                current_optimal_weights = list(previous_optimal_weights) + [0]  # remove the cash and append 0 to weights 
     
        # Store the results
        log_final_values = {
            "Truncation_range": truncation_range,
            "N_initial": result_data["N_initial"],
            "N": result_data["N"],
            "no_of_options": no_of_options,
            "Short_strikes": short_strikes,
            "Epsilon": 0,
            "M_bound": "No_M",
            "Optimal_weights": current_optimal_weights,  # Updated with appended zero if needed
            "Objective_value": current_objective_value,  # Updated with min value
            "Target_call_value": result_data["target_call_price"]
           }
        

        log_for_inc_no_of_options.append(log_final_values)  # Append to log
        
        
        
        ####PLOT###
        result = solve_max_problem_gurobi_without_M(M_bound, K1, K2, current_optimal_weights[1:] , short_strikes,
                                   short_call, K, marg, epsilon)  #remove the cash    
        
        #plotting the conditional target option and hedge portfolio at short maturity
        price = np.zeros(len(K1))
        BS_price = np.zeros(len(K1))
        hedge = np.zeros(len(K1))
        tolerance = 1e-17
        Pr_opt = result["p_matrix"]
        
        #print(index)
        for i in range(len(K1)):
             #\sum_{j}p_{i,j}y_j/\alpha_i
            if marg[0][i] < tolerance:
                print(f"marginal below tolerance:{marg[0][i]}")
                print(sum(Pr_opt[i,j] * Asian_option_payoff(K1[i],K2[j],K) for j in range(len(K2)))/marg[0][i])
                price[i] = np.nan
            else:
                price[i] = sum(Pr_opt[i,j]*Asian_option_payoff(K1[i],K2[j],K)  for j in range(len(K2)))/marg[0][i]   
            
            #Asian option price at short maturity t1 for the given asian option payoff can be computed using the Black-Scholes price
            
            if 2*K -K1[i] >= 0:
                BS_price[i] = 0.5 * BS_call(K1[i],-K1[i] + 2 *K,T_GRID[1],T,sigma,r)
            else:
                BS_price[i] = K1[i] - K
           
            
            hedge[i] =  current_optimal_weights[0] + sum( current_optimal_weights[_+1] * max(K1[i]-short_strikes[_],0) for _ in range(no_of_options))

        plt.plot(K1,price,label='target')
        plt.plot(K1,BS_price,label='BS target price')
        plt.plot(K1,hedge,label=f'hedge portfolio,')
        plt.xlabel('Stock price at short_maturity')
        plt.legend()
#         plt.savefig(f"Plot_for_{no_of_options}_options_and_N_{N}.eps",format="eps",dpi =300)
        plt.show()
        plt.close()
        
        #compute the

    # **Convert to a Pandas DataFrame**
    df_results = pd.DataFrame(log_for_inc_no_of_options)

#     # **Save as a Pickle File**
#     df_results.to_pickle("results_for_different_options_NUG_Asian.pkl")

#     print("Results saved as a DataFrame in results_for_different_options_NUG.pkl")


# %%
# **Save as a Pickle File**
df_results.to_pickle("results_for_different_options_NUG_Asian.pkl")

print("Results saved as a DataFrame in results_for_different_options_NUG.pkl")


# %%
# asian_price = 0

# for i in range(len(K1)):
#     for j in range(len(K2)):
#         asian_price += Pr_opt[i,j]*Asian_option_payoff(K1[i],K2[j],K)
        
# print(asian_price)

# %%
# Save as a Pickle File
outfile  = "results_for_different_options_NUG_Asian.pkl"
df_results.to_pickle(outfile)

print(f"Results saved as a DataFrame in {outfile}")


# %%
pd.read_pickle("results_for_different_options_NUG_Asian.pkl")

# %% [markdown]
# **COMPARE THE HEDGING ERROR FOR THE DIFFERENT OPTIONS WITH THE HEDGING ERROR USING THE WORST PROBABILITIES FROM THE MOT PRICING PROBLEM**

# %%
results_for_increasing_options = pd.read_pickle("results_for_different_options_NUG_Asian.pkl")

for entry in results_for_increasing_options["Optimal_weights"]:
    print(entry)

hedge_list_MOT_diff_options = []

for entry in results_for_increasing_options["Optimal_weights"]:
    short_strikes = short_strike_range[:len(entry)-1]
    #compute the hedging error using the optimal weights in the min-max problem and the probability matrix from MOT problem
    hedge_list_MOT_diff_options.append(compute_objective(entry, data_MOT['P_matrix'], K1, K2, short_strikes, K, marg[0]))
    

# %%
plt.plot(results_for_increasing_options["no_of_options"],hedge_list_MOT_diff_options,label="Hedge value using MOT")
plt.plot(results_for_increasing_options["no_of_options"],results_for_increasing_options["Objective_value"],
         label="Hedge value using min-max")
plt.xticks(results_for_increasing_options["no_of_options"])
plt.xlabel("Number of options")
plt.ylabel("Hedge values")
plt.legend()
plt.show()
plt.close()

# %% [markdown]
# **COMPUTE THE TARGET OPTION PRICE FOR THE HEDGING PORTFOLIOS WITH THE PRICE OF THE ASIAN OPTION USING THE MOT PROBLEM**

# %%
#compute the target Asian price for different options in the hedge portfolio

target_price_list_diff_options = []

for entry in results_for_increasing_options["Optimal_weights"]:
    
    short_strikes = short_strike_range[:len(entry)-1]
    
    #get the corresponding prices of the options in the hedge portfolio
    short_call = get_short_call(T_GRID,
    T_GRID[1],
    len(short_strikes),
    marg,
    disc_points_new,
    short_strikes,
    )
    
    target_price = entry[0] + np.dot(short_call,entry[1:])
    
    target_price_list_diff_options.append(target_price)
    

# %%
print(f"Price of Asian option using MOT:{data_MOT['Final_value']}")


plt.plot(results_for_increasing_options["no_of_options"], target_price_list_diff_options,'b.',alpha=0.5,label='Target price using hedging problem')
plt.plot(results_for_increasing_options["no_of_options"],data_MOT["Final_value"]*np.ones_like(target_price_list_diff_options),'r',lw=2,label='Target price from MOT')
plt.xticks(results_for_increasing_options["no_of_options"])
plt.xlabel("Number of options")
plt.ylabel("Target price")
plt.legend()
plt.show()
plt.close()

# %%
import pandas as pd
from docx import Document

# Step 1: Load the pickle file (assumes it contains a DataFrame)
df = pd.read_pickle("results_for_different_options_NUG_Asian.pkl")

# Step 2: Create a new Word document and add a table
document = Document()

# Add a table: one extra row for header, columns = number of columns in df
table = document.add_table(rows=df.shape[0] + 1, cols=df.shape[1])
table.style = 'Light Grid'  # You can choose a style or omit this

# Fill in the header row with column names
hdr_cells = table.rows[0].cells
for j, col in enumerate(df.columns):
    hdr_cells[j].text = str(col)

# Fill in the rest of the table with data
for i, row in df.iterrows():
    # Create a new row (or use table.rows[i+1] if already created)
    row_cells = table.add_row().cells if i >= df.shape[0] else table.rows[i+1].cells
    for j, value in enumerate(row):
        row_cells[j].text = str(value)

# Step 3: Save the document
document.save("output.docx")


# %%
#### SIMULATE STOCK PATHS TO COMPUTE THE QUANTILES ####
if __name__ == "__main__" : 
    Nsim = 1000
    Nsteps = timepoints * 10
    delta_t = 1/Nsteps

    stock_paths = np.zeros([Nsim,Nsteps+1])
    stock_paths[:,0] = stock
    np.random.seed(2)
    Z1 = np.random.normal(size=[Nsim,Nsteps])

    time_indices = [] # list to store the corresponding time-points at which the stock paths are beong calculated
    time_indices.append(0)

    for i in range(Nsteps):
        stock_paths[:,i+1] = stock_paths[:,i] * np.exp((r - 0.5 * (sigma **2)) * delta_t \
            + sigma * np.sqrt(delta_t) * Z1[:,i])
    
        time_indices.append(delta_t * (i + 1))

    
    index1 = time_indices.index(T_GRID[1]) #index corresponding to short maturity
    index2 = time_indices.index(T) #index corresponding to target maturity

    print(f"Index corresponding to short maturity {time_indices[index1]} :{index1}")
    
    print(f"Index corresponding to target maturity {time_indices[index2]} :{index2}")
    
    #plot the stock paths
    t_paths = np.linspace(0, Nsteps, Nsteps+1)
    plt.plot(t_paths,stock_paths.transpose())
    plt.show()
    plt.close()
    
    #print the intermediate time points
    print(f"Time indices:\n {time_indices}")
    
## GET QUANTILES AT THE SHORT MATURITY AND TARGET MATURITY 


def hedge_payoff_intermediate_time(stock_value,time_point,weights,short_strikes):
    """
     Computes the payoff of the hedge portfolio at intermediate time-points(<= short_maturity) 
    """
    if time_point < T_GRID[1]: # if time_point < short-maturity
        payoff_arrays =  [weights[l+1] * BS_call(stock_value, short_strikes[l], time_point,
                                                                    T_GRID[1], sigma, r) #creates a list of dimension 1000 x len(short_strikes)
                          for l in range(len(short_strikes))]
        payoff_hedge =  weights[0] + np.sum(payoff_arrays, axis = 0)
            
        
        
    if time_point == T_GRID[1]: # if time_point =  short maturity
        payoff_arrays = [weights[l+1] * np.maximum(stock_value - short_strikes[l],0)
                                            for l in range(len(short_strikes))]   
        payoff_hedge =  weights[0] + np.sum(payoff_arrays, axis = 0)
        
    return payoff_hedge
            
           

                            

           
    

        
        

            





# %%
def target_payoff_intermediate_time(stock_value,time_point,T_GRID,target_strike):
    """
     Computes the payoff of the target option at intermediate time-points(less than or equal to the target maturity) 
     """
    target_value = 0
    if time_point < T_GRID[1]:# if time_point < short_maturity
        #first simulate the stock_paths at the short_maturity and T given the current stock price
        np.random.seed(5)
        N_sim_2 = 1000
        N_steps_2 = 2
        
        Z_normal = np.random.normal(size=[N_sim_2,N_steps_2])
        
        #time left to short maturity
        delta_t1 = T_GRID[1] - time_point
        
        stock_paths_initial = stock_value * np.ones(N_sim_2)
        
        #compute the stock prices at short maturity
        stock_paths_T1 = stock_paths_initial * np.exp((r - 0.5 * (sigma **2)) * delta_t1 \
            + sigma * np.sqrt(delta_t1) * Z_normal[:,0])
        
        #time difference between short maturity and target maturity
        delta_t2 = T_GRID[2] - T_GRID[1]
        
        #compute the stock prices at target maturity
        stock_paths_T =  stock_paths_T1 *   np.exp((r - 0.5 * (sigma **2)) * delta_t2 \
            + sigma * np.sqrt(delta_t2) * Z_normal[:,1])
        
        #compute the means
#         print(f"Average of the stock price values:{np.mean(stock_paths_T1),np.mean(stock_paths_T)}")
        
        #compute the payoff at maturity for the stock price paths
        target_value = np.mean([Asian_option_payoff(stock_paths_T1[i], stock_paths_T[i],target_strike) 
                               for i in range(N_sim_2)]) 

    elif time_point == T_GRID[1]: # if time_point = short_maturity
        
        if 2 * target_strike - stock_value >= 0:
            target_value = 0.5 * BS_call(stock_value,-stock_value + 2 * target_strike,T_GRID[1],T,sigma,r)
        else:
            target_value = stock_value - target_strike
    return target_value

# %%
results_for_different_options = results_for_increasing_options

# %%
No_of_options_list = results_for_different_options["no_of_options"].to_list()
optimal_weights_list = results_for_different_options["Optimal_weights"].to_list()

objective_value_list = results_for_different_options["Objective_value"].to_list()






#COMPUTE THE OBJECTIVE VALUE AT INTERMEDIATE TIME POINTS FOR DIFFERENT WEIGHTS FOR EACH STOCK PRICE SIMULATION

#Define a function to compute the objective value

def objective_value_for_stock_paths(time_point,stock_price_values, optimal_weights,T_GRID,K,short_strikes):
    """
    Compute the objective value for the stock price paths at a given time-point
    """
    
    short_strikes = short_strike_range[:len(optimal_weights)-1]
    
#     print(f"The short strikes are:{short_strikes}")
    
    objective_value = (target_payoff_intermediate_time(stock_price_values ,time_point,T_GRID,K) - 
           hedge_payoff_intermediate_time(stock_price_values, time_point, optimal_weights, short_strikes)
                      )

    return objective_value


#list to store the objective values

objective_value_full_list_for_weights=[]

for optimal_weights in optimal_weights_list:
    #store the objective value for each stock path simulation till short maturity i.e. time_indices[index1]
    objective_value_list_intermediate_time  = np.zeros((index1+1,Nsim))
    
    print(f"The optimal Weights are:{optimal_weights}\n")
    
    #the corresponding short strikes
    short_strikes = short_strike_range[:len(optimal_weights)-1]

    for i in range(index1+1):
        value = []
        for j in range(len(stock_paths[:,i])):
             #objective value at the intermediate time points
            value.append(objective_value_for_stock_paths(time_indices[i],stock_paths[j,i],optimal_weights,T_GRID,K,short_strikes))
        objective_value_list_intermediate_time[i] = value
        
    
    objective_value_full_list_for_weights.append(objective_value_list_intermediate_time )    


# %%
#Compute the maximum/peak PFEs with respect to each weight combination till short maturity



peak_PFE_99_list = []
peak_PFE_95_list = []
peak_PFE_5_list = []
peak_PFE_1_list = []
mean_absolute_error_list = []

    
for i,element in enumerate(objective_value_full_list_for_weights):#get the index and the corresponding element from the list
    
    print(f"The optimal weights for {i+1} options are:{optimal_weights_list[i]}")
    
    #print the shape of the the ith element: should be index1 x Nsim
    print(f"Shape of the {i}th element:{element.shape}")
    
    #compute the PFEs at each time point till short maturity
    ninety_nine_percentile_list = np.percentile(element,99, axis=1)
    ninety_fifth_percentile_list = np.percentile(element,95,axis=1) 
    fifth_percentile_list = np.percentile(element,5,axis=1)
    first_percentile_list = np.percentile(element,1,axis=1) 
    mean_of_absolute_error = np.mean(np.abs(element),axis=1) 
    
    #compute the peak PFEs
    peak_PFE_99 = np.max(ninety_nine_percentile_list)
    peak_PFE_95 = np.max(ninety_fifth_percentile_list)
    peak_PFE_5 = np.min(fifth_percentile_list)
    peak_PFE_1 = np.min(first_percentile_list)
    peak_mean_absolute_error = mean_of_absolute_error[-1] 
    
#     print(f"Peak mean absolute error is: {peak_mean_absolute_error}")
#     print(mean_of_absolute_error[-1])
   
    peak_PFE_99_list.append(peak_PFE_99)
    peak_PFE_95_list.append(peak_PFE_95)
    peak_PFE_5_list.append(peak_PFE_5)
    peak_PFE_1_list.append(peak_PFE_1)
    mean_absolute_error_list.append(mean_of_absolute_error[-1])
    
    

# %%
# No_of_options_list = results_for_different_options["no_of_options"].to_list()
# optimal_weights_list = results_for_different_options["Optimal_weights"].to_list()


# #COMPUTE THE OBJECTIVE VALUE AT SHORT MATURITY AND TARGET MATURITY FOR DIFFERENT WEIGHTS

# #Define a function to compute the objective value

# # def objective_value_for_stock_paths(time_point,stock_price_values, optimal_weights):
# #     """
# #     Compute the objective value for the stock price paths at a given time-point
# #     """
    
# #     short_strikes = short_strike_range[:len(optimal_weights)-1]
    
# #     print(f"The short strikes are:{short_strikes}")
    
# #     objective_value = (target_payoff_intermediate_time(stock_price_values ,time_point) - 
# #            hedge_payoff_intermediate_time(stock_price_values, time_point, optimal_weights, short_strikes)
# #                       )

# #     return objective_value




# #list to store the objective values at short maturity T1 and target maturity T for different combinations of weights
# objective_value_list_at_T1 = []
# objective_value_list_at_T = []


# #list to store the objective values at target maturity T for d
# for optimal_weights in optimal_weights_list:
    
#     print(f"The optimal Weights are:{optimal_weights}\n")
    
#     #the corresponding short strikes
#     short_strikes = short_strike_range[:len(optimal_weights)-1]
    
#     #compute the objective value at short-maturity
#     objective_value_list_T1 = objective_value_for_stock_paths(time_indices[index1],stock_paths[:,index1],optimal_weights)

#     #     print(f"Length:{len(objective_value_list_at_T1)}")

#     objective_value_list_at_T1.append(objective_value_list_T1)
    
#     #compute the objective value at target maturity
#     objective_value_list_T = (target_payoff_intermediate_time(stock_paths[:,index2] ,time_indices[index2]) \
#                                  - (optimal_weights[0] + np.sum([optimal_weights[l+1] * 
#                                                              np.maximum(stock_paths[:,index2] -short_strikes[l],0)
#                                                             for l in range(len(short_strikes))],axis=0)
#                                    )
#                                 )
#      #     print(f"Length at T:{len( objective_value_list_at_T)}")

#     objective_value_list_at_T.append(objective_value_list_T)

# objective_value_array_at_T1 = np.array(objective_value_list_at_T1)
# objective_value_array_at_T = np.array(objective_value_list_at_T)

# rows,columns = objective_value_array_at_T1.shape
# print(rows, columns)

# [np.percentile( objective_value_array_at_T1[i] ,99) for i in range(rows)]


# rows,columns = objective_value_array_at_T1.shape
# print(rows, columns)

# plt.plot(results_for_different_options["no_of_options"].to_list(),results_for_different_options["Objective_value"].to_list(), label='min-max')
# plt.plot(results_for_different_options["no_of_options"].to_list(),[np.percentile( objective_value_array_at_T1[i] ,99) for i in range(rows)],label='99th percentile')
# plt.plot(results_for_different_options["no_of_options"].to_list(),[np.percentile( objective_value_array_at_T1[i] ,95) for i in range(rows)],label='95th percentile')
# plt.plot(results_for_different_options["no_of_options"].to_list(),[np.percentile( objective_value_array_at_T1[i] ,5) for i in range(rows)],label='5th percentile')
# plt.plot(results_for_different_options["no_of_options"].to_list(),[np.percentile( objective_value_array_at_T1[i] ,1) for i in range(rows)],label='1st percentile')
# plt.plot(results_for_different_options["no_of_options"].to_list(),[np.mean( objective_value_array_at_T1[i]) for i in range(rows)], label = 'mean')
# plt.xlabel("Number of options")
# plt.title(f"PFEs at short_maturity {T_GRID[1]}")
# plt.legend()
# plt.show()

# %%
plt.plot(results_for_different_options["no_of_options"].to_list(),results_for_different_options["Objective_value"].to_list(), label='min-max')
plt.plot(results_for_different_options["no_of_options"].to_list(),mean_absolute_error_list, label = 'mean absolute error')
plt.xticks(results_for_different_options["no_of_options"])
plt.xlabel("Number of options")
plt.ylabel("Mean error")
plt.title(f"Min-max versus mean absolute error" )
plt.legend()
plt.show()
plt.close()

plt.plot(results_for_different_options["no_of_options"].to_list(),peak_PFE_99_list,label='99th percentile')
plt.plot(results_for_different_options["no_of_options"].to_list(),peak_PFE_95_list,label='95th percentile')
plt.plot(results_for_different_options["no_of_options"].to_list(),peak_PFE_5_list,label='5th percentile')
plt.plot(results_for_different_options["no_of_options"].to_list(),peak_PFE_1_list,label='1st percentile')
plt.xticks(results_for_different_options["no_of_options"])
plt.xlabel("Number of options")
plt.title(f"Peak PFEs till short_maturity {T_GRID[1]}")
plt.legend()
plt.show()
plt.close()

# %% [markdown]
# **Solve the dual problem to the get the superhedge corresponding to the Asian Option**

# %%
N = 16 
disc_points_new, call_prices_array_new, marg = get_disc_points_and_marginals(
            truncation_range=truncation_range, N=N, choice="non-uniform"
        )
K1 = disc_points_new[0]
K2 = disc_points_new[1]

# %%
# formulating the dual to the maximization problem
def inner_minimization(K1, K2, short_strikes, target_strike, marg,Asian_option_payoff):
    """
    Solve the dual problem
    """
    num_K1 = len(K1)
    num_K2 = len(K2)

    # Gurobi model
    model = gp.Model("Minimization")
#     model.setParam('OutputFlag', 0)  # Suppress solver output
    

    # Decision variables
    phi = model.addVars(num_K1, name="phi")
    zi = model.addVars(num_K2, name="zi")
    h = model.addVars(num_K1, name="h")

    # Objective function
    obj_expr = quicksum(phi[i] * marg[0][i] for i in range(num_K1)) + quicksum(zi[j] * marg[1][j] for j in range(num_K2))
    model.setObjective(obj_expr, GRB.MINIMIZE)
    
    
    model.update()#update the model to print the objective function
    # Print Objective Function
    print("\nObjective Function:")
    print(model.getObjective())  # Correct way to print the objective

    # Constraints
    print("\nConstraints:")
    for i in range(num_K1):
        for j in range(num_K2):
            constr_expr = phi[i] + zi[j] + h[i] * (K2[j] - K1[i]) >= Asian_option_payoff(K1[i], K2[j],target_strike)
            constr_name = f"Constraint_{i}_{j}"
            model.addConstr(constr_expr, name=constr_name)

            
    model.update()#update the model to get the constraints
    
    for constr in model.getConstrs():
        print(f"{constr.ConstrName}: {model.getRow(constr)} >= {constr.RHS}")  

    # Solve the model
    model.optimize()
    
    for constr in model.getConstrs():
        slack = constr.Slack  # Gurobi automatically computes LHS - RHS
        print(f"{constr.ConstrName}: Slack = {slack:.12f}")
    if model.status == GRB.OPTIMAL:
        max_value = model.objVal
        Phi = np.array([phi[i].X for i in range(num_K1)])
        Zi = np.array([zi[i].X for i in range(num_K2)])
        H = np.array([h[i].X for i in range(num_K1)])
        return {"Objective":max_value,"Phi":Phi,"Zi":Zi,"H":H}
    else:
        raise ValueError("Maximization problem failed.")

# %%
result_dual = inner_minimization(K1, K2, short_strikes, K, marg, Asian_option_payoff)

# %%
#get the objective value
print(f"The objective value using the dual:{result_dual['Objective']}")

# %%

#get the hedge portfolio coefficients
Phi = result_dual["Phi"]
Zi = result_dual["Zi"]
H = result_dual["H"]

# %%
print(H)

# %%
#get the worst possible p_{i,j} corresponding to our min-max problem
short_strikes = results_for_different_options["Short_strikes"][2]
weights = results_for_different_options["Optimal_weights"][2]
no_of_options = len(short_strikes)

# %%
short_call = get_short_call(T_GRID, T_GRID[1], no_of_options, marg, disc_points_new, short_strikes)

# %%
result_max = solve_max_problem_gurobi_without_M( M_bound,
    K1,
    K2,
    weights[1:],
    short_strikes,
    short_call,
    K,
    marg,
    0,
)

# %%
p_minmax = result_max["p_matrix"]

# %%

obj = 0
obj2 = 0
for i in range(len(K1)):
    inner_sum = 0
    inner_sum2 = 0
    for j in range(len(K2)):
        #compute the inner sum for the options which mature at T
        inner_sum += p_minmax[i,j] * (Zi[j] - Asian_option_payoff(K1[i],K2[j],K))
        inner_sum2 += p_minmax[i,j] * (Asian_option_payoff(K1[i],K2[j],K))
    obj += marg[0][i] * Phi[i] + inner_sum
    obj2 += marg[0][i] * Phi[i] - inner_sum2

print(f"The expected hedging error at {T_GRID[1]} using the superhedge and min-max p_ij : {obj}\n")  

print(f"The expected hedging error at {T_GRID[1]} using the superhedge restricted to short maturity options and min-max p_ij : {obj2}")    

# %%
print(f"the expected hedging error using 4 options and min-max problem :{result_max['call_value']}")

# %%
short_strike_range

# %%
no_of_options = len(K1)
short_strikes_t1 = K1 
# no_of_options = 4
# short_strikes_t1 = short_strike_range[:no_of_options]

X = np.zeros((len(K1),no_of_options))


for i in range(len(K1)):
    for j in range(len(short_strikes_t1)):
            X[i][j] = np.maximum(K1[i] - short_strikes_t1[j-1],0)
    
   
    
from sklearn.linear_model import LinearRegression

model_regression =  LinearRegression()
model_regression.fit(X, Phi)



Weights_for_options_t1 = model_regression.coef_

print("Coefficients:",Weights_for_options_t1)


plt.plot(K1,[np.dot(Weights_for_options_t1 ,X[i]) for i in range(X.shape[0])],label="Hedge portfolio")
plt.plot(K1,Phi,label='target')




# %%
no_of_options = len(K2)
short_strikes_T = K2 #short_strike_range[:no_of_options]

X = np.zeros((len(K2),no_of_options))


for i in range(len(K2)):
    for j in range(len(short_strikes_T)):
            X[i][j] = np.maximum(K2[i] - short_strikes_T[j-1],0)
    
   
    
from sklearn.linear_model import LinearRegression

model_regression2 =  LinearRegression()
model_regression2.fit(X, Zi)



Weights_for_options_T = model_regression2.coef_

print("Coefficients:", Weights_for_options_T)

print("Intercept:",model_regression.intercept_)

plt.plot(K1,[np.dot(Weights_for_options_T ,X[i]) for i in range(X.shape[0])],label="Hedge portfolio")
plt.plot(K1,Zi,label='target')
plt.legend()
plt.show()
plt.close()

# %%
def dual_hedge_payoff_intermediate_time(stock_value,time_point,weights_t1,weights_T,short_strikes_t1, short_strikes_T):
    """
     Computes the payoff of the hedge portfolio at intermediate time-points(<= short_maturity) 
    """
    payoff_arrays_T =  [weights_T[l] * BS_call(stock_value, short_strikes_T[l], time_point,
                                                                    T, sigma, r) 
                          for l in range(len(short_strikes_T))]
        
    
    if time_point < T_GRID[1]: # if time_point < short-maturity
        payoff_arrays_t1 =  [weights_t1[l] * BS_call(stock_value, short_strikes_t1[l], time_point,
                                                                    T_GRID[1], sigma, r) 
                          for l in range(len(short_strikes_t1))]
        
       
        payoff_hedge =  np.sum(payoff_arrays_t1, axis = 0) + np.sum(payoff_arrays_T, axis = 0)
            
        
        
    if time_point == T_GRID[1]: # if time_point =  short maturity
        payoff_arrays_t1 = [weights_t1[l] * np.maximum(stock_value - short_strikes_t1[l],0)
                                            for l in range(len(short_strikes_t1))]   
        
        payoff_hedge =  np.sum(payoff_arrays_t1, axis = 0) + np.sum(payoff_arrays_T, axis = 0)
            
    return payoff_hedge

# %%
stock_paths.shape

# %%
#COMPUTE THE OBJECTIVE VALUE AT INTERMEDIATE TIME POINTS FOR DIFFERENT WEIGHTS FOR EACH STOCK PRICE SIMULATION

#Define a function to compute the objective value

def objective_value_for_stock_paths_for_dual_portfolio(time_point,stock_price_values, weights_t1,weights_T,
                                                       short_strikes_t1, 
                                                       short_strikes_T,
                                                       T_GRID,K):
    """
    Compute the objective value for the stock price paths at a given time-point
    """
    
    short_strikes = short_strike_range[:len(optimal_weights)-1]
    
#     print(f"The short strikes are:{short_strikes}")
    
    objective_value = (target_payoff_intermediate_time(stock_price_values ,time_point,T_GRID,K) - 
            dual_hedge_payoff_intermediate_time(stock_price_values,time_point,weights_t1,
                                                weights_T,short_strikes_t1, short_strikes_T))

    return objective_value


#list to store the objective values




#store the objective value for each stock path simulation till short maturity i.e. time_indices[index1]
objective_value_dual_list  = np.zeros((index1+1,Nsim))
print(f"The optimal weights for {T_GRID[1]} maturity options are:{Weights_for_options_t1}")
print(f"The optimal weights for {T} maturity options are:{Weights_for_options_T}")
    
#the corresponding short strikes
short_strikes = short_strikes

for i in range(index1+1):
    value = []
    for j in range(len(stock_paths[:,i])):
             #objective value at the intermediate time points
                
        value.append(objective_value_for_stock_paths_for_dual_portfolio(time_indices[i],stock_paths[j,i], 
                                                       Weights_for_options_t1,
                                                       Weights_for_options_T,
                                                       short_strikes_t1, 
                                                       short_strikes_T,
                                                       T_GRID,K))
           
    objective_value_dual_list[i] = value
        

    
#print the shape of the the ith element: should be index1 x Nsim
print(f"Shape of the hedging error simulations list:{objective_value_dual_list.shape}")
    
#compute the PFEs at each time point till short maturity
ninety_nine_percentile_list = np.percentile(objective_value_dual_list,99, axis=1)
ninety_fifth_percentile_list = np.percentile(objective_value_dual_list,95,axis=1) 
fifth_percentile_list = np.percentile(objective_value_dual_list,5,axis=1)
first_percentile_list = np.percentile(objective_value_dual_list,1,axis=1) 
mean_of_absolute_error = np.mean(np.abs(objective_value_dual_list),axis=1) 
        
peak_PFE_99 = np.max(ninety_nine_percentile_list)
peak_PFE_95 = np.max(ninety_fifth_percentile_list)
peak_PFE_5 = np.min(fifth_percentile_list)
peak_PFE_1 = np.min(first_percentile_list)
peak_mean_absolute_error = mean_of_absolute_error[-1]    

# %%
print(f"The peak 99th PFE till short maturity for the dual portfolio: {peak_PFE_99 } ")
print(f"The peak 95th PFE till short maturity for the dual portfolio: {peak_PFE_95 } ")
print(f"The peak 5th PFE till short maturity for the dual portfolio: {peak_PFE_5 }")
print(f"The peak 1st PFE till short maturity for the dual portfolio: {peak_PFE_1 }")

# %%
print(f"The peak 99 PFE using 5 options and min-max hedging:{peak_PFE_99_list[-1]}")
print(f"The peak 95 PFE using 5 options and min-max hedging:{peak_PFE_95_list[-1]}")
print(f"The peak 5 PFE using 5 options and min-max hedging:{peak_PFE_5_list[-1]}")
print(f"The peak 1 PFE using 5 options and min-max hedging:{peak_PFE_1_list[-1]}")

# %%


