#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Apr 16 16:13:43 2022

@author: yanbing_wang
"""
TIME_WIN = 50
THRESH = 3
VARX = 0.05 # TODO: unit conversion
VARY = 0.03

IDLE_TIME = 20

# For writing raw trajectories as Fragment objects
# change first "ID" to "_id" to query by ObjectId
WANTED_DOC_FIELDS = ["ID", "ID","timestamp","x_position","y_position","direction","last_timestamp","last_timestamp", "first_timestamp"]
FRAGMENT_ATTRIBUTES = ["id","ID","t","x","y","dir","tail_time","last_timestamp","first_timestamp"]


