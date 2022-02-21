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

# directory to output TM_XXXX_GT.py and TM_XXXX_pollute.py
output_directory = r"C:\Users\teohz\Desktop\Zi-benchmark-output\generation2_synthetic_data\scenario8"
input_directory = r"E:\I24-postprocess\benchmark\TM_trajectory.csv"
# use this directory if full_df has been processed before
processed_input_directory = r"C:\Users\teohz\Desktop\Zi-benchmark-output\generation2_synthetic_data"

#%%
if __name__ == "__main__":
    simulation_range = "0-15min"
    
    # Read straight from processed_trajectory
    orig_df = pd.read_csv(processed_input_directory + "\scenario8\processed_trajectory_" + simulation_range + ".csv")
    
    #%%
    
    # Slice t_range and x_range
    t_range = [0, 5000]
    x_range = [3000, 4000]
    
    df = orig_df[(orig_df['Frame #'] >= t_range[0]) & (orig_df['Frame #'] <= t_range[1])]
    df = df[(df['x'] >= x_range[0]) & (df['x'] <= x_range[1])]
    
    #%% 
    # pollute data
    
    df = pollute(df, AVG_CHUNK_LENGTH=30, OUTLIER_RATIO=0.2) # manually perturb (downgrade the data)
    df.to_csv(output_directory + "\pollute_" + simulation_range + "_" + ".csv", index=False)
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


