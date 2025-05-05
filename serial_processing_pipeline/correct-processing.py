#!/usr/bin/env python3
# coding: utf8

"""
python3 correct-processing.py /path_with_processed_data [-f file.lst, use this flag if you want to specify block of runs you are interested in] [-r, use this flag if you want to reprocess data]
"""

import os
import sys
import time
import numpy as np 
from collections import defaultdict

import re
import argparse

import subprocess
from subprocess import call
import shlex

import glob


os.nice(0)

class CustomFormatter(argparse.RawDescriptionHelpFormatter,
                      argparse.ArgumentDefaultsHelpFormatter):
    pass

def parse_cmdline_args():
    parser = argparse.ArgumentParser(
        description=sys.modules[__name__].__doc__,
        formatter_class=CustomFormatter)
    parser.add_argument('path_from', type=str, help="The path of folder/s that contain/s files")
    parser.add_argument('-f','--f', type=str, help='File with blocks')
    parser.add_argument('-r', '--r', type=bool, default=False, action="store" , help="Use this flag if you want to rerun indexing")
    return parser.parse_args()

def running(path_from, rerun):
    print('Rerun ', rerun) # type(rerun) = bool
    dic_stream = defaultdict(list)
    dic_list = defaultdict(list)
    
    files_lst = glob.glob(os.path.join(path_from,"*.lst?*"))
    streams = glob.glob(os.path.join(path_from,"streams/*.stream?*"))
    
    success = True

    if len(files_lst) == 0 or len(streams) == 0:
        print("Run {} has not been processed yet".format(path_from))
        success = False
    else:
        
        for file_lst in files_lst:
            filename = os.path.basename(file_lst).replace('split-events-EV-','').replace('split-events-EV','').replace('split-events-','').replace('events-','')

            suffix = re.search(r'.lst\d+', filename).group()
            prefix = filename.replace(suffix,'')
            
            suffix = re.search(r'\d+', suffix).group()

            key_name = prefix+'-'+suffix
            dic_list[os.path.join(path_from, key_name)] = file_lst
        
        for stream in streams:

            streamname = os.path.basename(stream)
            suffix = re.search(r'.stream\d+', streamname).group()
            prefix = streamname.replace(suffix,'')
            
            suffix = re.search(r'\d+', suffix).group()
            
            key_name = prefix+'-'+suffix
            dic_stream[os.path.join(path_from,key_name)] = stream
        
        mod_files_lst = dic_list.keys() 
        mod_streams = dic_stream.keys() 
        
        
        
        k_inter = set(mod_files_lst) & set(mod_streams)
        k_diff = set(mod_files_lst) - set(mod_streams) #there is no streams for some lst files

        
        
        if len(k_diff) != 0:
            for k in k_diff:
                print("There is no streams for some {}".format(k))
                success = False
                
                if rerun == True:
                    os.chdir(os.path.dirname(k))
                    command = "sbatch {}".format(k+'.sh')
                    os.system(command)
                
        for k in k_inter:
            
            lst = dic_list[k]

            k_lst =  len([line.strip() for line in open(lst, 'r').readlines() if len(line)>0])
            stream =  dic_stream[k]

            command = 'grep -ic "Image filename:" {}'.format(stream)
            process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
            k_stream = int(process.communicate()[0])

            if k_lst != k_stream:
                print("For {}: stream = {}, lst = {}".format(k, k_stream, k_lst))
                success = False
                if rerun == True:
                    os.chdir(os.path.dirname(k))
                    command = "sbatch {}".format(k+'.sh')
                    os.system(command)

    if success:
        print(f'All processed correctly in {os.path.basename(path_from)}')
        #pass


if __name__ == "__main__":
    args = parse_cmdline_args()
    rerun = args.r
    
    path_from = os.path.abspath(args.path_from)
    if args.f is None:
        if len(glob.glob(os.path.join(path_from, '*.lst*')))!=0:
            running(path_from, rerun)
        else:
            for path, dirs, all_files in os.walk(path_from):
                
                if len(glob.glob(os.path.join(path, '*.lst*')))!=0 and path != path_from:
                    #print(path)
                    running(path, rerun)
    else:
        with open(args.f,'r') as f:
            for d in f:
                d = d.strip()
                for path, dirs, all_files in os.walk(path_from):
                    
                    if len(glob.glob(os.path.join(path, '*.lst*')))!=0 and path != path_from and d in os.path.basename(path):
                        
                        running(path, rerun)

    
