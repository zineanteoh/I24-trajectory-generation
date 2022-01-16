# -*- coding: utf-8 -*-
"""
Created on Sun Jan 16 13:22:26 2022

@author: teohz

generate time and space windows with approx 1:1 frame:x ratio

description: 
    given a batch from benchmark_generator_zi.py, 
    
    split the _pollute.csv into smaller batches with #-of-frames:x-travelled
    approximately equal to 1:1
    
    output and save the timespace diagrams: 
        - TM_[batch_num]_[start_row]_[n_rows]_[x_start]_[x_end]_GT.csv
        - TM_[batch_num]_[start_row]_[n_rows]_[x_start]_[x_end]_pollute.csv
        - timespace_[start_row]_[n_rows]_[x_start]_[x_end].png
"""

from benchmark_generator_zi import *

def run_benchmark_TM(df, x_start, x_end):
    df.to_csv(zi_output_directory + "\TM_" + batch_and_row_info + str(x_start) + "_" + str(x_end) + "_GT.csv", index=False) # save the ground truth data
    return df

def pollute_data(df, x_start, x_end):
    df = pollute(df, AVG_CHUNK_LENGTH=30, OUTLIER_RATIO=0.2) # manually perturb (downgrade the data)
    df.to_csv(zi_output_directory + "\TM_" + batch_and_row_info + str(x_start) + "_" + str(x_end) + "_pollute.csv", index=False) # save the downgraded data
    print("saved.")
    return df

def plot_and_save_time_space(df, x_start, x_end):
    plot_time_space(df, lanes=[1], time="Frame #", space="x", ax=None, show =True)
    # code to output timespace to a folder
    zi_time_space_path = os.path.abspath(zi_output_directory + r"\timespace_windows")
    output_file = "timespace_" + batch_and_row_info + str(x_start) + "_" + str(x_end) + ".png"
    plt.savefig(os.path.join(zi_time_space_path, output_file))


# manually change this to generate mini batches
batch_and_row_info = "8000_56001_12000_"

#%%
if __name__ == "__main__":
    
    # path to benchmark folder that contains batches of files generated 
    # from benchmark_generator_zi.py
    path_to_benchmark = r"C:\Users\teohz\Desktop\Zi-benchmark-output\benchmark"
    
    # get GT of batch
    df = pd.read_csv(path_to_benchmark + "\TM_" + batch_and_row_info + "GT.csv")
    
    # get max frames
    max_frame = df['Frame #'].max()
    
    # get max x
    max_x = df['x'].max()
    
    # generate mini batches
    x_start = 0
    while x_start < max_x:
        mini_df = df
        # index mini_df s.t. frame:x = 1:1
        mini_df = mini_df[(mini_df['x'] > x_start) & (mini_df['x'] < x_start + max_frame)]
    
        # output the GT of mini batch
        mini_df = run_benchmark_TM(mini_df, x_start, x_start + max_frame)
        
        # pollute and output
        mini_df = pollute_data(mini_df, x_start, x_start + max_frame)
        
        # plot
        plot_and_save_time_space(mini_df, x_start, x_start + max_frame)
        
        x_start += max_frame
        
    