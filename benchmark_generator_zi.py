# -*- coding: utf-8 -*-
"""
Created on Fri Dec 17 12:39:34 2021

@author: teohz
"""

from benchmark_TM import *

# directory to output TM_XXXX_GT.py and TM_XXXX_pollute.py
zi_output_directory = r"C:\Users\teohz\Desktop\Zi-benchmark-output\benchmark"
# directory to output timespace_XXXX.png
zi_timespace_directory = r"C:\Users\teohz\Desktop\Zi-benchmark-output\timespace"


def process_trajectory_file(row_start, row_end):
    '''
    Processes the trajectory file once and return the dataframe
    where row = row_start (inclusive) to row_end (exclusive)
    Header row (row=0) is included in the dataframe. 
    '''
    data_path = r"E:\I24-postprocess\benchmark\TM_trajectory.csv"
    df = pd.read_csv(data_path, nrows=5000)

    print(len(df))
    df = standardize(df)
    df = calc_state(df)
    df = preprocess(df)
    
    return df

def run_benchmark_TM(df):
    
    
    # you can select some time-space window such that the trajectory lengths are similar (run plot_time_space to visualize)
    df = df[df["x"]>1000]
    df = df[df["Frame #"]>1000]
    
    df.to_csv(zi_output_directory + "\TM_1000_GT.csv", index=False) # save the ground truth data

def pollute_data(df):
    df = pollute(df, AVG_CHUNK_LENGTH=30, OUTLIER_RATIO=0.2) # manually perturb (downgrade the data)
    df.to_csv(zi_output_directory + "\TM_1000_pollute.csv", index=False) # save the downgraded data
    print("saved.")

def plot_and_save_time_space(df):
    plot_time_space(df, lanes=[1], time="Frame #", space="x", ax=None, show =True)
    # code to output timespace to a folder
    zi_time_space_path = os.path.abspath(zi_timespace_directory)
    output_file = "timespace_1000.png"
    plt.savefig(os.path.join(zi_time_space_path, output_file))

#%%
if __name__ == "__main__":
    df = process_trajectory_file(1, 5000)
    for i in range(1):
        run_benchmark_TM(df)
        pollute_data(df)
        plot_and_save_time_space(df)
        

