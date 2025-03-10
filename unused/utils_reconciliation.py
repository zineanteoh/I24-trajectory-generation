import pandas as pd
import numpy as np
from cvxopt import matrix, solvers, sparse,spdiag,spmatrix
from bson.objectid import ObjectId
from collections import defaultdict

from i24_logger.log_writer import logger, catch_critical, log_warnings, log_errors

# TODO
# add try except and put errors/warnings to log
logger.set_name("reconciliation_module")
solvers.options['show_progress'] = False
dt = 1/30

# ==================== CVX optimization for 2d dynamics ==================
@catch_critical(errors = (Exception))
def combine_fragments(raw_collection, stitched_doc):
    '''
    stack fragments from stitched_doc to a single document
    fragment_ids should be sorted by last_timestamp (see PathCache data structures for details)
    :param raw_collection: a mongoDB collection object to query fragments from fragment_ids
    :param stitched_doc: an output document from stitcher
    fields that need to be extended: timestamp, x_position, y_positin, road_segment_id, flags
    fields that need to be removed: _id, 
    fields that are preserved (copied from any fragment): vehicle class
    fields that need to be re-assigned: first_timestamp, last_timestamp, starting_x, ending_x, length, width, height
    '''
    
    stacked = defaultdict(list)

    if isinstance(stitched_doc, list):
        fragment_ids = stitched_doc
    else:
        fragment_ids = stitched_doc["fragment_ids"]
    if isinstance(fragment_ids[0], str):
        fragment_ids = [ObjectId(_id) for _id in fragment_ids]

    # logger.info("fragment_ids type: {}, {}".format(type(fragment_ids), fragment_ids))
    # logger.debug("first doc {}".format(raw_collection.find_one(fragment_ids[0]))) # this returns none
    
    stacked["fragment_ids"] = fragment_ids
    all_fragment = raw_collection.find({"_id": {"$in": fragment_ids}}) # returns a cursor

    for fragment in all_fragment:
        # logger.debug("fragment keys: {}".format(fragment.keys()))
        stacked["timestamp"].extend(fragment["timestamp"])
        stacked["x_position"].extend(fragment["x_position"])
        stacked["y_position"].extend(fragment["y_position"])
        stacked["road_segment_ids"].extend(fragment["road_segment_ids"])
        stacked["flags"].extend(fragment["flags"])
        stacked["length"].extend(fragment["length"])
        stacked["width"].extend(fragment["width"])
        stacked["height"].extend(fragment["height"])
        # stacked["detection_confidence"].extend(fragment["detection_confidence"])
        stacked["coarse_vehicle_class"].append(fragment["coarse_vehicle_class"])
        stacked["fine_vehicle_class"].append(fragment["fine_vehicle_class"])
        stacked["direction"].append(fragment["direction"])
        
        stacked["filter"].extend(fragment["filter"])
        
       
    # first fragment
    first_id = fragment_ids[0]
    # logger.debug("** first_id: {}, type: {}".format(first_id, type(first_id)), extra = None)
    # logger.debug("** timestamp: {}, collection size: {}".format(stacked["timestamp"], raw_collection.count_documents({})), extra = None)
    
    first_fragment = raw_collection.find_one({"_id": first_id})
    stacked["starting_x"] = first_fragment["starting_x"]
    stacked["first_timestamp"] = first_fragment["first_timestamp"]
    
    # last fragment
    last_id = fragment_ids[-1]
    last_fragment = raw_collection.find_one({"_id": last_id})
    stacked["ending_x"] = last_fragment["ending_x"]
    stacked["last_timestamp"] = last_fragment["last_timestamp"]
    
    # take the median of dimensions
    stacked["length"] = np.median(stacked["length"])
    stacked["width"] = np.median(stacked["width"])
    stacked["height"] = np.median(stacked["height"])
    
    # Take the most frequent element of the list
    stacked["coarse_vehicle_class"] = max(set(stacked["coarse_vehicle_class"]), key = stacked["coarse_vehicle_class"].count)
    stacked["fine_vehicle_class"] = max(set(stacked["fine_vehicle_class"]), key = stacked["fine_vehicle_class"].count)
    stacked["direction"] = max(set(stacked["direction"]), key = stacked["direction"].count)
    
    # Apply filter
    if len(stacked["filter"]) == 0: # no good measurements
        stacked["post_flag"] = "low conf fragment"
    else:
        stacked["x_position"] = [stacked["x_position"][i] if stacked["filter"][i] == 1 else np.nan for i in range(len(stacked["filter"])) ]
        stacked["y_position"] = [stacked["y_position"][i] if stacked["filter"][i] == 1 else np.nan for i in range(len(stacked["filter"])) ]
    return stacked



@catch_critical(errors = (Exception))    
def resample(car):
    # resample timestamps to 30hz, leave nans for missing data
    '''
    resample the original time-series to uniformly sampled time series in 30Hz
    car: document
    leave empty slop as nan
    '''

    # Select time series only
    time_series_field = ["timestamp", "x_position", "y_position"]
    data = {key: car[key] for key in time_series_field}
    
    # Read to dataframe and resample
    df = pd.DataFrame(data, columns=data.keys()) 
    index = pd.to_timedelta(df["timestamp"], unit='s')
    df = df.set_index(index)
    df = df.drop(columns = "timestamp")
    
    df = df.resample('0.033333333S').mean() # close to 30Hz
    df.index = df.index.values.astype('datetime64[ns]').astype('int64')*1e-9

    # resample to 25hz
    # df=df.groupby(df.index.floor('0.04S')).mean().resample('0.04S').asfreq()
    # df.index = df.index.values.astype('datetime64[ns]').astype('int64')*1e-9
    # df = df.interpolate(method='linear')


    # df=df.groupby(df.index.floor('0.04S')).mean().resample('0.04S').asfreq() # resample to 25Hz snaps to the closest integer
    car['x_position'] = df['x_position'].values
    car['y_position'] = df['y_position'].values
    car['timestamp'] = df.index.values
        
    return car

  
@catch_critical(errors = (Exception))     
def _blocdiag(X, n):
    """
    makes diagonal blocs of X, for indices in [sub1,sub2]
    n indicates the total number of blocks (horizontally)
    """
    if not isinstance(X, spmatrix):
        X = sparse(X)
    a,b = X.size
    if n==b:
        return X
    else:
        mat = []
        for i in range(n-b+1):
            row = spmatrix([],[],[],(1,n))
            row[i:i+b]=matrix(X,(b,1))
            mat.append(row)
        return sparse(mat)


# @catch_critical(errors = (Exception))
def _getQPMatrices(x, lam2, lam1, reg="l2"):
    '''
    turn ridge regression (reg=l2) 
    1/M||y-Hx||_2^2 + \lam2/N ||Dx||_2^2
    and elastic net regression (reg=l1)
    1/M||y-Hx-e||_2^2 + \lam2/N ||Dx||_2^2 + \lam1/M||e||_1
    to QP form
    min 1/2 z^T Q x + p^T z + r
    s.t. Gz <= h
    input:  x: data array with missing data
            t: array of timestamps (no missing)
    return: Q, p, H, (G, h if l1)
    TODO: uneven timestamps
    '''
    if reg == "l1" and lam1 is None:
        raise ValueError("lam1 must be specified when regularization is set to L1")
     
    # get data
    N = len(x)
    
    # non-missing entries
    idx = [i.item() for i in np.argwhere(~np.isnan(x)).flatten()]
    x = x[idx]
    M = len(x)
    
    
    if M == 0:
        raise ZeroDivisionError
    # differentiation operator
    # D1 = _blocdiag(matrix([-1,1],(1,2), tc="d"), N) * (1/dt)
    # D2 = _blocdiag(matrix([1,-2,1],(1,3), tc="d"), N) * (1/dt**2)
    D3 = _blocdiag(matrix([-1,3,-3,1],(1,4), tc="d"), N) * (1/dt**3)
    
    if reg == "l2":
        DD = lam2 * D3.trans() * D3
        # sol: xhat = (I+delta D'D)^(-1)x
        I = spmatrix(1.0, range(N), range(N))
        H = I[idx,:]
        DD = lam2*D3.trans() * D3
        HH = H.trans() * H

        Q = 2*(HH/M+DD/N)
        p = -2*H.trans() * matrix(x)/M

        return Q, p, H, N, M
    else:
        DD = lam2 * D3.trans() * D3
        # define matices
        I = spmatrix(1.0, range(N), range(N))
        IM = spmatrix(1.0, range(M), range(M))
        O = spmatrix([], [], [], (N,N))
        OM = spmatrix([], [], [], (M,M))
        H = I[idx,:]
        HH = H.trans()*H

        Q = 2*sparse([[HH/M+DD/N,H/M,-H/M], # first column of Q
                    [H.trans()/M,IM/M, -H*H.trans()/M], 
                    [-H.trans()/M,-H*H.trans()/M,IM/M]]) 
        
        p = 1/M * sparse([-2*H.trans()*matrix(x), -2*matrix(x)+lam1, 2*matrix(x)+lam1])
        G = sparse([[H*O,H*O],[-IM,OM],[OM,-IM]])
        h = spmatrix([], [], [], (2*M,1))
        return Q, p, H, G, h, N,M
    

def _getQPMatrices_nan(N, lam2, lam1, reg="l2"):
    '''
    same with _getQPMatrices, but dealt with x vector is all nans
    Q = 2(lam2 D^T D)
    p = 0
    
    '''
    if reg == "l1" and lam1 is None:
        raise ValueError("lam1 must be specified when regularization is set to L1")
    
    # differentiation operator
    # D1 = _blocdiag(matrix([-1,1],(1,2), tc="d"), N) * (1/dt)
    # D2 = _blocdiag(matrix([1,-2,1],(1,3), tc="d"), N) * (1/dt**2)
    D3 = _blocdiag(matrix([-1,3,-3,1],(1,4), tc="d"), N) * (1/dt**3)
    DD = lam2 * D3.trans() * D3
    Q = 2*(DD/N)
    p = spmatrix([], [], [], (N,1))
    p = matrix(p, tc="d")
    return Q, p
    
  

@catch_critical(errors = (Exception))
def rectify_1d(lam2, x):
    '''                        
    solve solve for ||y-x||_2^2 + \lam ||Dx||_2^2
    args: lam2
    axis: "x" or "y"
    '''  
    
    # TODO: if x is all nans, skip this trajectory
    Q, p, H, N,M = _getQPMatrices(x, lam2, None, reg="l2")
    
    sol=solvers.qp(P=Q, q=p)
    # print(sol["status"])
    
    # extract result
    xhat = sol["x"][:N]
    return xhat




# @catch_critical(errors = (Exception))
def rectify_2d(car, reg = "l2", **kwargs):
    '''
    rectify on x and y component independently
    batch method
    :param args: (lam2_x, lam2_y) if reg == "l2"
                (lam2_x, lam2_y, lam1_x, lam1_y) if reg == "l1"
    '''
    if reg == "l1" and "lam1_x" not in kwargs:
        raise ValueError("lam1 must be specified if regularization is set to l1.")
      
    lam2_x, lam2_y = kwargs["lam2_x"], kwargs["lam2_y"] # shared arguments
    
    if reg == "l2":
        xhat = rectify_1d(lam2_x, car["x_position"])
        yhat = rectify_1d(lam2_y, car["y_position"])
        
    elif reg == "l1": 
        lam1_x, lam1_y = kwargs["lam1_x"], kwargs["lam1_y"] # additional arguments for l1
        
        # max_acc = 99
        # min_acc = -99
        # trials=0
        # while (max_acc > 10 or min_acc < -10):
        xhat, cx1, max_acc, min_acc = rectify_1d_l1(lam2_x, lam1_x, car["x_position"])
        yhat, cy1, _,_ = rectify_1d_l1(lam2_y, lam1_y, car["y_position"])
            # lam2_x *=1.1 # incrementally adjust
            # lam1_x = 1e-6
            # print("max_acc: {:.2f}, min_acc: {:.2f}, cx1:{:.2f}".format(max_acc, min_acc,cx1))
            # trials+=1
            # if trials >= 10:
            #     car["post_flag"] = "exceeds max reconciliation trials"
            #     break
        # print("*** residual is {}, {}".format(cx1, cy1))
        
    # write to document
    car["timestamp"] = list(car["timestamp"])
    car["x_position"] = list(xhat)
    car["y_position"] = list(yhat)
    car["x_score"] = cx1
    car["y_score"] = cy1

    
    return car           




def rectify_1d_l1(lam2, lam1, x):
    '''                        
    solve for ||y-Hx-e||_2^2 + \lam2 ||Dx||_2^2 + \lam1||e||_1
    convert to quadratic programming with linear inequality constraints
    handle sparse outliers in data
    rewrite l1 penalty to linear constraints https://math.stackexchange.com/questions/391796/how-to-expand-equation-inside-the-l2-norm
    :param args: (lam2, lam1)
    '''  

    Q, p, H, G, h, N,M = _getQPMatrices(x, lam2, lam1, reg="l1")
    sol=solvers.qp(P=Q, q=matrix(p) , G=G, h=matrix(h))
    # extract result
    xhat = sol["x"][:N]
    # u = sol["x"][N:N+M]
    # v = sol["x"][N+M:]
    # print(sol["status"])
    
    # first term of the cost function
    xhat_re = np.reshape(xhat, -1) # (N,)
    # c1 = np.sqrt(np.nansum((x-xhat_re)**2)/M) # RMSE
    c1 = np.nansum(np.abs(x-xhat_re))/M # MAE
    
    # get the max acceleration
    D2 = _blocdiag(matrix([1,-2,1],(1,3), tc="d"), N) * (1/dt**2)
    acc = D2*xhat
    max_acc = max(acc)
    min_acc = min(acc)
    return xhat, c1, max_acc, min_acc
    

    
    
    





# =================== RECEDING HORIZON RECTIFICATION =========================
@catch_critical(errors = (Exception))
def receding_horizon_1d(x, lam2, PH, IH):
    '''
    rolling horizon version of rectify_1d
    x: a time series that needs to be reconciled.
    args: (lam2, PH, IH)
        PH: prediction horizon
        IH: implementation horizon
    QP formulation with sparse matrix min ||y-Hx||_2^2 + \lam ||Dx||_2^2
    '''
    # TODO: compute matrices once -> need to flatten _getQPMatrices here

    # get data
    n_total = len(x)
    
    # matrices that are not the first or last window -> compute once
    A = sparse([[spmatrix(1.0, range(3), range(3))], [spmatrix([], [], [], (3,PH-3))]])
    A = matrix(A, tc="d")
    # Q0, p0 = _getQPMatrices_nan(PH, lam2, None, reg="l2")
    
    # save final answers
    xfinal = matrix([])
    x_prev = None
    l = 0
    r = l+PH
    last = False
    
    while True:
        
        # termination criterion
        if r > n_total:
            r = n_total
            IH = n_total - l
            last = True
        
        # print(l, l+IH, r)
        xx = x[l: r]
        nn = len(xx)
        try:
            Q, p, H, N,M,r = _getQPMatrices(xx, lam2, None, reg="l2")
        except ZeroDivisionError: 
            # M=0, all missing entries in this rolling window
            # ... simply ignore the data fitting term, assume 0 jerk motion (constant accel)
            Q, p = _getQPMatrices_nan(nn, lam2, None, reg="l2")
        
        if not x_prev: # first window, no fixed initial conditions
            sol=solvers.qp(P=Q, q=p)  
        else:
            b = matrix(x_prev)
            if last:
                A = sparse([[spmatrix(1.0, range(3), range(3))], [spmatrix([], [], [], (3,nn-3))]])
                A = matrix(A, tc="d")
            sol=solvers.qp(P=Q, q=p, A=A, b=b) 
        
        xhat = sol["x"]
        xfinal = matrix([xfinal, xhat[:IH]])
        
        # update
        if last:
            break
        else:
            l += IH
            r = l+PH
            # save for the next loop
            x_prev = xhat[IH:IH+3]
    
    return xfinal



@catch_critical(errors = (Exception))
def receding_horizon_2d(car, lam2_x, lam2_y, PH, IH):
    '''
    car: stitched fragments from data_q
    TODO: parallelize x and y?
    '''
    # get data 
    # TODO: if x is all nans, skip this trajectory
    # non-missing entries
    # idx = [i.item() for i in np.argwhere(~np.isnan(car["x_position"])).flatten()]
    # x = car["x_position"][idx]
    # M = len(x)
    # logger.debug("M {}".format(M))
    # if M < 3:
    #     logger.warning("Not enough valid data in receding_horizon_2d")
    #     # TODO: raise exception
    
    if len(car["x_position"]) > 3:
        xhat = receding_horizon_1d(car["x_position"], lam2_x, PH, IH)
        yhat = receding_horizon_1d(car["y_position"], lam2_x, PH, IH)
        
        car['x_position'] = xhat
        car['y_position'] = yhat
    
    # simply return the raw data if length is less than 3
    car["timestamp"] = list(car["timestamp"])
    car["x_position"] = list(car["x_position"])
    car["y_position"] = list(car["y_position"])
    

    return car


@catch_critical(errors = (Exception))
def receding_horizon_1d_l1(car, lam2, lam1, PH, IH, axis):
    '''
    rolling horizon version of rectify_1d_l1
    car: dict
    args: (lam1, lam2, PH, IH)
        PH: prediction horizon
        IH: implementation horizon
    '''
    # TODO: compute matrices once

    # get data
    x = car[axis+"_position"]
    n_total = len(x)
    
    # additional equality constraint: state continuity
    A = sparse([[spmatrix(1.0, range(4), range(4))], [spmatrix([], [], [], (4,PH-4))]])
    A = matrix(A, tc="d")
    
    # save final answers
    xfinal = matrix([])
    
    n_win = max(0,(n_total-PH+IH)//IH)
    last = False
    
    cs = 3
    for i in range(n_win+1):
        # print(i,'/',n_total, flush=True)
        if i == n_win: # last
            xx =x[i*IH:]
            last = True
        else:
            xx = x[i*IH: i*IH+PH]
        # nn = len(xx)
        Q, p, H, G, h, N,M,r = _getQPMatrices(xx, lam2, lam1, reg="l1")
        
        
        try: # if x_prev exists - not first window
            A = sparse([[spmatrix(1.0, range(cs), range(cs))], [spmatrix([], [], [], (cs,N-cs + 2*M))]])
            A = matrix(A, tc="d")
            b = matrix(x_prev)
            sol=solvers.qp(P=Q, q=p, G=G, h=matrix(h), A = A, b=b)   
            
        except:
            sol=solvers.qp(P=Q, q=matrix(p) , G=G, h=matrix(h))    
        
        xhat = sol["x"][:N]

        if last:
            xfinal = matrix([xfinal, xhat])         
        else:
            xfinal = matrix([xfinal, xhat[:IH]])
            
        # save for the next loop
        x_prev = xhat[IH:IH+cs]
    
    return xfinal








@catch_critical(errors = (Exception))
def receding_horizon_2d_l1(car, lam2_x, lam2_y, lam1_x, lam1_y, PH, IH):
    '''
    car: stitched fragments from data_q
    TODO: parallelize x and y?
    '''
    xhat = receding_horizon_1d_l1(car, lam2_x, lam1_x, PH, IH, "x")
    yhat = receding_horizon_1d_l1(car, lam2_y, lam1_y, PH, IH, "y")
    
    car['x_position'] = xhat
    car['y_position'] = yhat

    # TODO: replace with schema validation in dbw before insert
    car["timestamp"] = list(car["timestamp"])
    car["x_position"] = list(car["x_position"])
    car["y_position"] = list(car["y_position"])
    return car




    
if __name__ == '__main__':
    PH = 120
    IH = 30
    N = 410
    l = 0
    r = l+PH
    
    while True:
        
        # termination criterion
        if r > N:
            r = N
            IH = N - l
            print(l, r)
            break
        
        print(l, l+IH, r)
        # update
        l += IH
        r = l+PH

        
    
    
    
    
    
    