# -*- coding: utf-8 -*-
"""
Created on Fri Dec 17 12:39:34 2021

@author: teohz
"""

from benchmark_TM import *

# directory to output TM_XXXX_GT.py and TM_XXXX_pollute.py
zi_output_directory = r"C:\Users\teohz\Desktop\Zi-benchmark-output\benchmark"


def process_trajectory_file(start_row, row_per_batch):
    '''
    Processes the trajectory file once and return the dataframe
    starting from row = start_row, for row_per_batch number of rows
    Header row (row=0) is included in the dataframe. 
    '''
    data_path = r"E:\I24-postprocess\benchmark\TM_trajectory.csv"
    df = pd.read_csv(data_path, skiprows=[i for i in range(1, start_row)], nrows=row_per_batch)
    print("inside process_trajectory: " + str(len(df.index)))
    print(len(df))
    df = standardize(df)
    df = calc_state(df)
    df = preprocess(df)
    
    return df

def run_benchmark_TM(df, batch):
    # you can select some time-space window such that the trajectory lengths are similar (run plot_time_space to visualize)
    #df = df[df["x"]>1000]
    #df = df[df["Frame #"]>1000]
    
    df.to_csv(zi_output_directory + "\TM_" + str(batch * 1000) + "_GT.csv", index=False) # save the ground truth data
    return df

def pollute_data(df, batch):
    df = pollute(df, AVG_CHUNK_LENGTH=30, OUTLIER_RATIO=0.2) # manually perturb (downgrade the data)
    df.to_csv(zi_output_directory + "\TM_" + str(batch * 1000) + "_pollute.csv", index=False) # save the downgraded data
    print("saved.")
    return df

def plot_and_save_time_space(df, batch):
    plot_time_space(df, lanes=[1], time="Frame #", space="x", ax=None, show =True)
    # code to output timespace to a folder
    zi_time_space_path = os.path.abspath(zi_output_directory)
    output_file = "timespace_" + str(batch * 1000) + ".png"
    plt.savefig(os.path.join(zi_time_space_path, output_file))

#%%
if __name__ == "__main__":
    
    # the number of rows to read TM_trajectory each loop
    row_per_batch = 5000
    for batch_num in range(10):
        start_row = row_per_batch * batch_num + 1
        print("first loop: " + str(start_row))
        df = process_trajectory_file(start_row, row_per_batch)
        # set df_batch 
        df_batch = df
        for i in range(1):
            df_batch = run_benchmark_TM(df_batch, batch_num + 1)
            df_batch = pollute_data(df_batch, batch_num + 1)
            df_batch = plot_and_save_time_space(df_batch, batch_num + 1)


