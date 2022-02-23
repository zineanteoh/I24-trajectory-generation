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
output_directory = r"C:\Users\teohz\Desktop\Zi-benchmark-output\generation2_synthetic_data"
input_directory = r"E:\I24-postprocess\benchmark\TM_trajectory.csv"
# use this directory if full_df has been processed before
processed_input_directory = r"C:\Users\teohz\Desktop\Zi-benchmark-output\generation2_synthetic_data\TM_trajectory\x_12000-20000"

#%%
if __name__ == "__main__":
    
    # files to iterate
    processed_files = ["\TM_trajectory_processed_trajectory_0-12min.csv",
                       "\TM_trajectory_processed_trajectory_12-23min.csv",
                       "\TM_trajectory_processed_trajectory_23-34min.csv"]
    
    for file in processed_files:
        # Otherwise just run 3 to import the preprocessed file
        # 1. Read full file
        full_df = pd.read_csv(processed_input_directory + file)
        
        # (files already processed)
        #full_df = standardize(full_df)
        #full_df = calc_state(full_df)
        #full_df = preprocess(full_df)
        
        # (THIS IS FOR TM_TRAJ ONLY) slice window to just take the first 8000 meters
        full_df = full_df[(full_df['x'] >= 12000) & (full_df['x'] <= 20000)]
    
        # 2. update column
        full_df = update_column_to_schema(full_df)
        
        # smooth out position
        
        
        break
    
    
    #%%
    # 2. save preprocessed file to save time
    full_df.to_csv(output_directory + "\TM_trajectory\TM_trajectory_processed_trajectory_23-34min.csv", index=False)
    
    df = full_df
    
    #%% 
    # pollute data
    pollute_df = pollute(df, AVG_CHUNK_LENGTH=30, OUTLIER_RATIO=0.2) # manually perturb (downgrade the data)
    pollute_df.to_csv(output_directory + "\TM_trajectory\TM_trajectory_processed_trajectory_23-34min_pollute.csv", index=False)
    #%%
    # plot data
    for lane in range(1,5):
        plot_time_space(df, lanes=[lane], time="Frame #", space="x", ax=None, show =True)
        # code to output timespace to a folder
        zi_time_space_path = os.path.abspath(output_directory)
        output_file = "timespace_lane" + str(lane) + ".png"
        plt.savefig(os.path.join(zi_time_space_path, output_file))
    
    
    # start_row = 1
    # nrows = 5000
    # for batch_num in range(1,2):
    #     # skip batch0
    #     if batch_num == 0:
    #         continue
        
    #     start_row = 500*(batch_num**2) + 3500*batch_num - 3999
    #     nrows = 5000 + (1000 * (batch_num - 1))
    #     print(start_row, nrows)
    #     df = process_trajectory_file(start_row, nrows)
    #     # generate ground truth csv file (uncomment if not needed)
    #     df = run_benchmark_TM(df, batch_num, start_row, nrows)
            
    #     # genereate pollute csv file after polluting
    #     df = pollute_data(df, batch_num, start_row, nrows)
    #     df = plot_and_save_time_space(df, batch_num, start_row, nrows)


