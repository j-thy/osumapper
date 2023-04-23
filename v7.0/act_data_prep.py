# -*- coding: utf-8 -*-

#
# Part 1 action script
#

from audio_tools import *;
from os_tools import *;

import os, re, time;

mapdata_path = "mapdata/";
try:
    divisor = GLOBAL["divisor"];
except:
    divisor = 4;

def step1_load_maps():
    # Changes the current working directory to the directory where the script is located.
    fix_path()

    # Check if nodeJS is installed
    test_process_path("node");

    # Create mapdata folder if it doesn't already exist
    if not os.path.isdir(mapdata_path):
        os.mkdir(mapdata_path);

    # Checks whether the node modules directory exists
    test_node_modules()

    # Checks whether ffmpeg is installed
    test_process_path("ffmpeg", "-version");

    # Open map list
    with open("maplist.txt", encoding="utf8") as fp:
        fcont = fp.readlines();

    # Load maps from map list
    results = [];
    for line in fcont:
        results.append(line);

    # Removes all .npz files currently in the mapdata folder
    for file in os.listdir(mapdata_path):
        if file.endswith(".npz"):
            os.remove(os.path.join(mapdata_path, file));

    # Print number of maps loaded
    print("Number of filtered maps: {}".format(len(results)));

    # For each map in list to train...
    for k, mname in enumerate(results):
        try:
            start = time.time()
            # Read in osu map data, extract pitch, rhythm, and flow, and save to file.
            read_and_save_osu_file(mname.strip(), filename=os.path.join(mapdata_path, str(k)), divisor=divisor);
            end = time.time()
            print("Map data #" + str(k) + " saved! time = " + str(end - start) + " secs");
        except Exception as e:
            print("Error on #{}, path = {}, error = {}".format(str(k), mname.strip(), e));