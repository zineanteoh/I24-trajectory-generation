# -*- coding: utf-8 -*-
"""
Created on Fri Jan 28 11:15:36 2022

@author: teohz

@brief: this program graphs the computed trajectory against 
        a smoothing spline fit
        
        the trajectory's derivatives are computed up to jerk
        using discrete-time derivatives. 
        
        the smoothing fit used is interpolated univariate
        spline fit. 
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
from random import randint
from scipy.interpolate import *

def get_derivative(function, time):
    '''
    Parameters
    ----------
    function : list of N points at time t
    time : list of N points corresponding to function at time t

    Returns
    -------
    f_prime : list of df/dt at time t, the midpoint of two adjacent points
                in the original function
    t_prime : list of (N - 1) points corresponding to f_prime at time t
    '''
    #f_prime = np.diff(function)/np.diff(time)
    #t_prime = []
    #for i in range(len(f_prime)):
    #    t_temp = (time[i + 1] + time[i]) / 2
    #    t_prime = np.append(t_prime, t_temp)
    #return f_prime, time[:-1]
    df = np.diff(function)
    dt = np.diff(time)
    dfdt = df/dt
    return dfdt, time[:-1]

def plot_figure(title, 
                plot_infos,
                xlabel, 
                ylabel, 
                alpha,
                output_file_name = "figure.png"):
    plt.figure()
    for plot_info in plot_infos:
        plt.plot(plot_info["x_list"], 
                 plot_info["y_list"], 
                 color = plot_info["color"],
                 alpha = alpha,
                 label = plot_info["label"],
                 markersize = 0.5)
    plt.ticklabel_format(useOffset=False, style='plain')
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.legend()
    if SAVE_PLOT_TO_FILE:
        plt.savefig(os.path.join(main_folder, output_file_name))

def smooth_trajectory(df):
    '''
    @brief  smooth out the trajectory by grouping rows by car ID, then
            applying a smoothing function to each car, then combining the
            car trajectories into one dataframe and sorting by Frame # to
            retain row orders
    '''
    unique_IDs = df['ID'].unique()
    output_df = []
    for carId in unique_IDs:
        # print(carId)
        df_car = df[df['ID'] == carId]
        df_car = smooth_car(df_car)
        output_df.append(df_car)
    
    if len(output_df) != 0:
        return pd.concat(output_df, ignore_index=True)

def smooth_car(df_car, plot_graph = False):
    '''
    @brief  smooth out one individual car's x and y position and returns a
            df with x_velocity, y_velocity, x_acceleration, y_acceleration, 
            x_jerk, y_jerk columns populated
    '''
    
    # variables for indexing the columns of df_car
    col_x = 'x_position'
    col_y = 'y_position'
    col_timestamp = 'timestamp'
    
    # reset index
    df = df_car.reset_index()
    
    # x & y position
    x = df[col_x]
    y = df[col_y]
    time_x = df[col_timestamp]
    time_y = df[col_timestamp]
    # spline fit on position (smooth out)
    spl_x = UnivariateSpline(time_x, x, k=3, s=100000)
    spl_y = interp1d(time_y, y, kind='zero')
    #spl_time_x = np.linspace(min(time_x), max(time_x), 100)
    spl_time_x = time_x
    spl_x = spl_x(spl_time_x)
    #spl_time_y = np.linspace(min(time_y), max(time_y), 100)
    spl_time_y = time_y
    spl_y = spl_y(spl_time_y)
    
    # velocity
    v_x, time_v_x = get_derivative(x, time_x)
    v_x = -v_x
    spl_v_x, spl_time_v_x = get_derivative(spl_x, spl_time_x)
    spl_v_x = -spl_v_x
    v_y, time_v_y = get_derivative(y, time_y)
    v_y = -v_y
    spl_v_y, spl_time_v_y = get_derivative(spl_y, spl_time_y)
    spl_v_y = -spl_v_y
    
    # acceleration
    a_x, time_a_x = get_derivative(v_x, time_v_x)
    spl_a_x, spl_time_a_x = get_derivative(spl_v_x, spl_time_v_x)
    a_y, time_a_y = get_derivative(v_y, time_v_y)
    spl_a_y, spl_time_a_y = get_derivative(spl_v_y, spl_time_v_y)
    
    # jerk
    j_x, time_j_x = get_derivative(a_x, time_a_x)
    spl_j_x, spl_time_j_x = get_derivative(spl_a_x, spl_time_a_x)
    j_y, time_j_y = get_derivative(a_y, time_a_y)
    spl_j_y, spl_time_j_y = get_derivative(spl_a_y, spl_time_a_y)
    
    if plot_graph:
        # x position
        # plot position
        car_id = df['ID'][0]
        plot_title = "Position (in x): Car_id: " + str(car_id)
        plot_infos = [{"x_list": time_x, "y_list": x, "color": "tab:olive", "label": "Position (in x)"},
                      {"x_list": spl_time_x, "y_list": spl_x, "color": "tab:green", "label": "Spline Fit Position"}]
        output_file_name = "car" + str(car_id) + "_1_position.png"
        plot_figure(plot_title, plot_infos, "time (seconds)", "position, x", 1, output_file_name)
        
        # plot velocity
        plot_title = "Velocity (in x): Car_id: " + str(car_id)
        plot_infos = [{"x_list": time_v_x, "y_list": v_x, "color": "tab:olive", "label": "Velocity (in x)"}, 
                      {"x_list": spl_time_v_x, "y_list": spl_v_x, "color": "tab:green", "label": "Spline Fit Velocity"}]
        output_file_name = "car" + str(car_id) + "_2_velocity.png"
        plot_figure(plot_title, plot_infos, "time (seconds)", "velocity, dx/dt", 0.9, output_file_name)
        
        # plot acceleration
        plot_title = "Acceleration (in x): Car_id: " + str(car_id)
        plot_infos = [{"x_list": time_a_x, "y_list": a_x, "color": "tab:olive", "label": "Accleration (in x)"},
                      {"x_list": spl_time_a_x, "y_list": spl_a_x, "color": "tab:green", "label": "Spline Fit Acceleration"}]
        output_file_name = "car" + str(car_id) + "_3_acceleration.png"
        plot_figure(plot_title, plot_infos, "time (seconds)", "acceleration, dv/dt", 0.9, output_file_name)
        
        # plot jerk
        plot_title = "Jerk (in x): Car_id: " + str(car_id)
        plot_infos =  [{"x_list": time_j_x, "y_list": j_x, "color": "tab:olive", "label": "Jerk (in x)"},
                        {"x_list": spl_time_j_x, "y_list": spl_j_x, "color": "tab:green", "label": "Spline Fit Jerk"}]
        output_file_name = "car" + str(car_id) + "_4_jerk.png"
        plot_figure(plot_title, plot_infos, "time (seconds)", "jerk, da/dt", 1, output_file_name)
        
        # y position
        # plot position
        car_id = df['ID'][0]
        plot_title = "Position (in y): Car_id: " + str(car_id)
        plot_infos = [{"x_list": time_y, "y_list": y, "color": "tab:olive", "label": "Position (in y)"},
                      {"x_list": spl_time_y, "y_list": spl_y, "color": "tab:green", "label": "Spline Fit Position"}]
        output_file_name = "car" + str(car_id) + "_1_position.png"
        plot_figure(plot_title, plot_infos, "time (seconds)", "position, y", 1, output_file_name)
    
        # plot velocity
        plot_title = "Velocity (in y): Car_id: " + str(car_id)
        plot_infos = [{"x_list": time_v_y, "y_list": v_y, "color": "tab:olive", "label": "Velocity (in y)"}, 
                      {"x_list": spl_time_v_y, "y_list": spl_v_y, "color": "tab:green", "label": "Spline Fit Velocity"}]
        output_file_name = "car" + str(car_id) + "_2_velocity.png"
        plot_figure(plot_title, plot_infos, "time (seconds)", "velocity, dy/dt", 0.9, output_file_name)
        
        # plot acceleration
        plot_title = "Acceleration (in y): Car_id: " + str(car_id)
        plot_infos = [{"x_list": time_a_y, "y_list": a_y, "color": "tab:olive", "label": "Accleration (in y)"},
                      {"x_list": spl_time_a_y, "y_list": spl_a_y, "color": "tab:green", "label": "Spline Fit Acceleration"}]
        output_file_name = "car" + str(car_id) + "_3_acceleration.png"
        plot_figure(plot_title, plot_infos, "time (seconds)", "acceleration, dv/dt", 0.9, output_file_name)
        
        # plot jerk
        plot_title = "Jerk (in y): Car_id: " + str(car_id)
        plot_infos =  [{"x_list": time_j_y, "y_list": j_y, "color": "tab:olive", "label": "Jerk (in y)"},
                       {"x_list": spl_time_j_y, "y_list": spl_j_y, "color": "tab:green", "label": "Spline Fit Jerk"}]
        output_file_name = "car" + str(car_id) + "_4_jerk.png"
        plot_figure(plot_title, plot_infos, "time (seconds)", "jerk, da/dt", 1, output_file_name)
    
    # return dataframe
    df['x_velocity'] = [*spl_v_x, 0]
    df['y_velocity'] = [*spl_v_y, 0]
    df['x_acceleration'] = [*spl_a_x, 0, 0]
    df['y_acceleration'] = [*spl_a_y, 0, 0]
    df['x_jerk'] = [*spl_j_x, 0, 0, 0]
    df['y_jerk'] = [*spl_j_y, 0, 0, 0]
    return df
    
    

main_folder = r"C:\Users\teohz\Desktop\smoothness-visualizer"
trajectory_path = main_folder + "\TM_GT_5000rows.csv"

SAVE_PLOT_TO_FILE = False
SAVE_TRAJECTORY_TO_CSV = False
ANIMATE_TRAJECTORY = False
#%%
if __name__ == "__main__":
    
    # read file
    # df_orig = pd.read_csv(trajectory_path)
    
    for i in range(1):
        # lane_changing_cars =[33, 58, 92, 98, 100, 109, 110, 111, 121, 131, 138, 140, 144, 163, 167, 183]
        car_id =  33
        # get specific car_id (comment out if no id column in trajectory file)
        df = full_df[full_df['ID'] == car_id]
        if not df.empty and df['lane'].nunique() > 1:
            new_df = smooth_car(df)
            