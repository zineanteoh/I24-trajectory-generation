# -----------------------------
__file__ = 'stitcher.py'
__doc__ = """
Operates the trajectory fragment stitcher, continuously consuming raw trajectory fragments as they are
written to the database.
"""

# -----------------------------
import multiprocessing
import stitcher_parameters
import db_parameters
import logging
# TODO: check and test database implementation
import pymongo
import pymongo.errors
from db_reader import DBReader
from db_writer import DBWriter
from collections import deque, OrderedDict
from utils.stitcher_module import min_nll_cost
from utils.data_structures import Fragment, PathCache

# helper functions
def _first(dict):
    try:
        key,val = next(iter(dict.items()))
        return key, val
    except StopIteration:
        raise StopIteration


def stitch_raw_trajectory_fragments(fragment_queue,
                                    stitched_trajectory_queue,
                                    log_queue):
    """
    fragment_queue is sorted by last_timestamp
    :param fragment_queue: fragments sorted in last_timestamp
    :param stitched_trajectory_queue: to store stitched trajectories result
    :param log_queue:
    :return: None
    """
    # Get parameters
    TIME_WIN = stitcher_parameters.TIME_WIN
    VARX = stitcher_parameters.VARX
    VARY = stitcher_parameters.VARY
    THRESH = stitcher_parameters.THRESH
    IDLE_TIME = stitcher_parameters.IDLE_TIME
    
    # Initialize some data structures
    curr_fragments = deque()  # fragments that are in current window (left, right), sorted by last_timestamp
    past_fragments = dict()  # set of ids indicate end of fragment ready to be matched, insertion ordered
    P = PathCache() # an LRU cache of Fragment object (see utils.data_structures)

    # Make database connection for writing
    dbw = DBWriter(host=db_parameters.DEFAULT_HOST, port=db_parameters.DEFAULT_PORT, username=db_parameters.DEFAULT_USERNAME,   
                   password=db_parameters.DEFAULT_PASSWORD,
                   database_name=db_parameters.DB_NAME, server_id=1, process_name=1, process_id=1, session_config_id=1)
    
    print("** Stitching starts. fragment_queue size: ", fragment_queue.qsize())
    # while True: 
    while fragment_queue.qsize() > 0:
        # print("*** getting fragment")  
        fragment = Fragment(fragment_queue.get()) # make object
        fragment.curr = True
        P.add_node(fragment)
        
        if fragment.ID == 100166:
            print('here')
        
        # specify time window for curr_fragments
        right = fragment.last_timestamp # right pointer: current end time
        left = min(fragment.first_timestamp, right - TIME_WIN)
        print("left, right: ", left, right)
        
        # compute fragment statistics (1d motion model)
        fragment.compute_stats()
        print("Curr_fragments size: ", len(curr_fragments))
        
        # remove out of sight fragments 
        if curr_fragments:
            while P.get_fragment(curr_fragments[0]).last_timestamp < left: 
                past_id = curr_fragments.popleft()
                past_fragment = P.get_fragment(past_id)
                past_fragment.curr = False
                past_fragment.past = True
                past_fragments[past_id] = past_fragment # could use keys only: past_fragments[past_id] = None if memory is an issue 
        print("Past_fragments size: ", len(past_fragments))
        
        # compute score from every fragment in curr to fragment, update Cost
        for curr_id in curr_fragments:
            curr_fragment = P.get_fragment(curr_id)
            cost = min_nll_cost(curr_fragment, fragment, TIME_WIN, VARX, VARY)
            if cost > THRESH:
                curr_fragment.add_conflict(fragment)
            elif cost > -999:
                curr_fragment.add_suc(cost, fragment)
                fragment.add_pre(cost, curr_fragment)
         
        
        prev_size = 0
        curr_size = len(past_fragments)
        
        # start iterative matching
        while curr_size > 0 and curr_size != prev_size:
            prev_size = len(past_fragments)
            gone_ids = set()
            for id, ready in past_fragments.items(): # all fragments in past_fragments are ready to be matched to tail
                best_head = ready.get_first_suc()
                if not best_head or not best_head.pre: # if ready has no match or best head already matched to other fragment-> go to the next ready
                    # past_fragments.pop(ready.id)
                    gone_ids.add(id)
                
                else:
                    try: best_tail = best_head.get_first_pre()
                    except: 
                        best_tail = None
                        continue
                    if not best_head.tail_matched and best_tail.id == ready.id and best_tail.id not in ready.conflicts_with:
                        print("** match tail of {} to head of {}".format(best_tail.ID, best_head.ID))
                        
                        P.union(best_tail.id, best_head.id)
                        gone_ids.add(ready.id)
                        Fragment.match_tail_head(best_tail, best_head)

            # bookkeep cleanup
            for gone_id in gone_ids:
                past_fragment = past_fragments.pop(gone_id)
                past_fragment.past = False
                past_fragment.gone = True
                
            curr_size = len(past_fragments)

        curr_fragments.append(fragment.id)    
        
        # write paths from P if time out is reached
        while True:
            try:
                root = P.first_node()
                if root.gone and root.tail_time < left - IDLE_TIME:
                    print("root's tail time: {:.2f}, current time window: {:.2f}-{:.2f}".format(root.tail_time, left, right))
                    path = P.pop_first_path()  
                    print("write to db: root {}, last_modified {:.2f}, path length: {}".format(root.ID, root.tail_time,len(path)))
                    stitched_trajectory_queue.put(path) # doesn't know ObjectId
                    dbw.write_stitch(path)
                else: # break if first in cache is not timed out yet
                    break
            except StopIteration: # break if nothing in cache
                break
            
        num_roots = P.count() # number of roots    
        print("Number of roots: ", num_roots)
    
    print("Total stitched trajectories: ", num_roots)
    # P.print_cache()
    all_paths = P.get_all_paths("ID")
    print(all_paths)


        
            
            
    
