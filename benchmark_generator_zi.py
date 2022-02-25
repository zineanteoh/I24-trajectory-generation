# -*- coding: utf-8 -*-
"""
Created on Fri Dec 17 12:39:34 2021

@author: teohz

generate batches of synthetic TransModeler (TM) simulation data for benchmark

description:
    split the input file TM_trajectory.csv into batches, with startrow & nrows,
    such that each batch outputs:
        TM_[batch_num]_[startrow]_[nrows]_GM.csv
        TM_[batch_num]_[startrow]_[nrows]_pollute.csv
        timespace_[batch_num]_[startrow]_[nrows].png
        
note on implementation:
    row_per_batch starts from 5000 and increments by 1000 every batch
    to yield approximately 700 to 1000 frames (not necessarily exact) 
"""

from benchmark_TM import *
from graph_trajectory import *
from datetime import datetime

def process_trajectory_file(start_row, nrows):
    '''
    Processes the trajectory file once and return the dataframe
    starting from row = start_row, for nrows number of rows
    Header row (row=0) is included in the dataframe. 
    '''
    data_path = input_directory
    df = pd.read_csv(data_path, skiprows=[i for i in range(1, start_row)], nrows=nrows)
    print("inside process_trajectory: " + str(len(df.index)))
    print(len(df))
    df = standardize(df)
    df = calc_state(df)
    df = preprocess(df)
    
    return df

def run_benchmark_TM(df, batch_num, start_row, nrows):
    # you can select some time-space window such that the trajectory lengths are similar (run plot_time_space to visualize)
    #df = df[df["x"]>2500]
    #df = df[df["Frame #"]>1000]
    
    df.to_csv(output_directory + "\TM_" + str(batch_num * 1000) + "_" + str(start_row) + "_" + str(nrows) + "_GT.csv", index=False) # save the ground truth data
    return df

def pollute_data(df, batch_num, start_row, nrows):
    df = pollute(df, AVG_CHUNK_LENGTH=30, OUTLIER_RATIO=0.2) # manually perturb (downgrade the data)
    df.to_csv(output_directory + "\TM_" + str(batch_num * 1000) + "_" + str(start_row) + "_" + str(nrows) + "_pollute.csv", index=False) # save the downgraded data
    print("saved.")
    return df

def plot_and_save_time_space(df, batch_num, start_row, nrows):
    plot_time_space(df, lanes=[1], time="Frame #", space="x", ax=None, show =True)
    # code to output timespace to a folder
    zi_time_space_path = os.path.abspath(output_directory)
    output_file = "timespace_" + str(batch_num * 1000) + "_" + str(start_row) + "_" + str(nrows) + ".png"
    plt.savefig(os.path.join(zi_time_space_path, output_file))

def modify_vehicle_class(df_column):
    '''
    Given a column of vehicle class, return an array where class is mapped to
    an integer corresponding to the class
    
    sedan -> 1
    SUV -> 2
    bus -> 3
    truck -> 4
    trailer -> 5
    '''
    vehicle_class_conditions = [
        df_column.eq("sedan"), 
        df_column.eq("SUV"), 
        df_column.eq("bus"), 
        df_column.eq("truck"), 
        df_column.eq("trailer")]
    choices = [1, 2, 3, 4, 5]
    return np.select(vehicle_class_conditions, choices)
    
def update_column_to_schema(full_df, timestamp_offset = 0):
    '''
    @brief  Renames the df's column to match the db schema
            and add the relevant columns
    '''
    # rename and populate columns according to db schema
    full_df = full_df.rename({'Timestamp': 'timestamp', 
                    'Object class': 'Coarse_vehicle_class', 
                    'x': 'x_position',
                    'y': 'y_position'}, axis='columns')
    
    # add configuration id (1 for now)
    full_df['configuration_ID'] = 1
    
    # add timestamp for subsequent generated data files? 
    # full_df['timestamp'] = full_df['timestamp'] + timestamp_offset
    
    # add road segment id (-1 for now)
    full_df['road_segment_ID'] = -1
    
    # height to 0 for now
    full_df['height'] = 0
    
    # map vehicle class to number (eg 1 for truck, 2 for SUV)
    full_df['Coarse_vehicle_class'] = modify_vehicle_class(full_df['Coarse_vehicle_class'])
    
    return full_df


# directory to output TM_XXXX_GT.py and TM_XXXX_pollute.py
output_directory = r"E:\I24-postprocess\benchmark\data_for_mongo_zi\TM_trajectory"
#%%
if __name__ == "__main__":
    '''
    Part A: 
        This part takes in raw trajectory generated by TransModeler as input
        X number of rows at a time. Each chunk of sub trajectory is processed
        using standardize(), calc_state(), and preprocess() algorithm from
        benchmark_TM. 
        
    Part B:
        This part assumes subtrajectories from TM_trajectory has been 
        processed using standardize(), calc_state(), and preprocess(), and saved
        into processed_input_directorty with the file names included in the 
        processed_files list. This part will smoothen each trajectory and save
        to a csv file as GroundTruth. (GT_XXXX)
        
    Part C:
        This part takes in the dataframes from part B and apply pollute() and
        output to a csv file as pollute. (TM_xxxx)
    '''
    
    # Step A Begins:
    verbose = True
    input_trajectory = r"E:\I24-postprocess\benchmark\TM_trajectory.csv"
    simulation_time = 0 # in minutes
    #%%
    start_row = 1500001 # default is 1
    rows_per_chunk = [1000000, 1000000, 1000000, 1000000, 1000000, 1000000, 1000000]
    plot_timespace = True
    #%%
    # list of file names for Part B
    processed_files = []
    processed_simulation_range = []
    #%%
    for index, chunk in enumerate(rows_per_chunk):
        # read raw input file (super big file)
        raw_pd = pd.read_csv(input_trajectory, 
                      skiprows=[i for i in range(1, start_row)], 
                      nrows = chunk)
        if verbose:
            print(datetime.now().strftime("%H:%M:%S"))
            print('> Inputted file starting at row ' + str(start_row) + " for " + str(chunk) + "rows.")
        
        if raw_pd.empty:
            print(datetime.now().strftime("%H:%M:%S"))
            print('> Reached end of file at index:' + str(index))
            break
        
        # process
        raw_pd = standardize(raw_pd)
        raw_pd = calc_state(raw_pd)
        processed_pd = preprocess(raw_pd)
        if verbose:
            print(datetime.now().strftime("%H:%M:%S"))
            print('> Processing trajectory complete')
        
        # get duration & generate file name
        duration = round(processed_pd['Timestamp'].max() / 60)
        simulation_range = str(simulation_time) + "-" + str(simulation_time + duration)
        file_name = "\\" + simulation_range + "min.csv"
        
        # output to csv
        processed_pd.to_csv(output_directory + file_name, index=False)
        if verbose:
            print(datetime.now().strftime("%H:%M:%S"))
            print('> Outputted processed traj to csv file')
        
        # update start_row, update simulation time, remember file name & simulation range
        start_row += chunk
        simulation_time += duration
        processed_files.append(file_name)
        processed_simulation_range.append(simulation_range)
    
    
    # Part B begins: 
    if verbose:
        print(datetime.now().strftime("%H:%M:%S"))
        print('> Part B BEGIN')
    
    for index, file in enumerate(processed_files):
        # get simulation range (i.e. "0-10" in mins)
        simulation_range = processed_simulation_range[index]
        
        # 1. Read full file
        full_df = pd.read_csv(output_directory + file)
        if verbose:
            print(datetime.now().strftime("%H:%M:%S"))
            print('> Inputted processed file: ' + file)
        
        # (THIS IS FOR TM_TRAJ ONLY) slice window to just take the first 8000 meters
        # full_df = full_df[(full_df['x'] >= 12000) & (full_df['x'] <= 20000)]
        
        # 2. update column
        full_df = update_column_to_schema(full_df)
        
        # smooth out position
        full_df = smooth_trajectory(full_df)
        
        # re-order by timestamp
        full_df = full_df.sort_values(by=['timestamp'])
        
        if verbose:
            print(datetime.now().strftime("%H:%M:%S"))
            print('> Smoothed trajectory')
        
        # plot timespace to output directory
        if plot_timespace:
            for lane in range(1, 5):
                plot_time_space(processed_pd, lanes=[lane], time="Frame #", space="x", ax=None, show =True)
                timespace_path = os.path.abspath(output_directory)
                output_file = "timespace_lane" + str(lane) + "_" + simulation_range + "min.png"
                plt.savefig(os.path.join(timespace_path, output_file))
        
        # 3. save as GT
        full_df.to_csv(output_directory + "\GT" + file, index=False)
        
        if verbose:
            print(datetime.now().strftime("%H:%M:%S"))
            print('> Outputted csv to GT')
        
        # pollute data
        pollute_df = pollute(full_df, AVG_CHUNK_LENGTH=30, OUTLIER_RATIO=0.2) # manually perturb (downgrade the data)
        pollute_df.to_csv(output_directory + "\pollute" + file, index=False)

        if verbose:
            print(datetime.now().strftime("%H:%M:%S"))
            print('> Outputted csv to pollute')
