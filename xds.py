#!/usr/bin/env python3
# coding: utf8
# Written by Galchenkova M., Tolstikova A., Yefanov O., 2022

"""

"""

import logging
import os
import sys
import h5py as h5
import numpy
import numpy.typing
import argparse
from typing import Any, List, Dict, Union, Tuple, TextIO, cast
from utils import crystfel_geometry
from numpy.typing import NDArray
import fabio
from pathlib import Path
import glob
import re
from string import Template
import shutil
import subprocess
import shlex

os.nice(0)

def xds_start(current_data_processing_folder, command_for_data_processing):
    #XDS_INP = os.path.join(current_data_processing_folder, 'XDS.INP')
    
    job_file = os.path.join(current_data_processing_folder,"%s_XDS.sh" % current_data_processing_folder.split("/")[-1])
    err_file = os.path.join(current_data_processing_folder,"%s_XDS.err" % current_data_processing_folder.split("/")[-1])
    out_file = os.path.join(current_data_processing_folder,"%s_XDS.out" % current_data_processing_folder.split("/")[-1])
    
    with open(job_file, 'w+') as fh:
        fh.writelines("#!/bin/sh\n")
        fh.writelines("#SBATCH --job=%s\n" % job_file)
        fh.writelines("#SBATCH --partition=allcpu\n")
        fh.writelines("#SBATCH --time=12:00:00\n")
        fh.writelines("#SBATCH --nodes=1\n")
        fh.writelines("#SBATCH --nice=100\n")
        fh.writelines("#SBATCH --mem=500000\n")
        fh.writelines("#SBATCH --output=%s\n" % out_file)
        fh.writelines("#SBATCH --error=%s\n" % err_file)
        fh.writelines("source /etc/profile.d/modules.sh\n")
        fh.writelines("module load xray\n")
        fh.writelines(f"{command_for_data_processing}\n")
    os.system("sbatch %s" % job_file)
    
    
def filling_template(
                        folder_with_raw_data, current_data_processing_folder, ORGX=0 , ORGY=0,\
                        DISTANCE_OFFSET=0, NAME_TEMPLATE_OF_DATA_FRAMES='blablabla', command_for_data_processing='xds_par'
                    ):
    global XDS_INP_template
    
    os.chdir(current_data_processing_folder)
    
    shutil.copy(XDS_INP_template, os.path.join(current_data_processing_folder, XDS_INP_template))

    info_txt = ''
    if len(glob.glob(os.path.join(folder_with_raw_data,'info.txt')))>0 and os.stat(os.path.join(folder_with_raw_data,'info.txt')).st_size != 0:
        info_txt = glob.glob(os.path.join(folder_with_raw_data,'info.txt'))[0]
        
        #run_type = ''
        #with open(info_txt, 'r') as f:
        #    run_type = next(f)
        
        #run_type = run_type.split(':')[-1].strip()
        #if (run_type == 'rotational'):
            
        command = f' grep -e "distance" {info_txt}'
        result = subprocess.check_output(shlex.split(command)).decode('utf-8').strip().split('\n')[0]
        DETECTOR_DISTANCE = float(re.search(r'\d+\.\d+',result).group(0)) + DISTANCE_OFFSET
        
        
        command =  f' grep -e "frames" {info_txt}'
        result = subprocess.check_output(shlex.split(command)).decode('utf-8').strip().split('\n')[0]
        NFRAMES = int(re.search(r'\d+',result).group(0))
        
        
        try:
            command =  f' grep -e "start angle" {info_txt}'
            result = subprocess.check_output(shlex.split(command)).decode('utf-8').strip().split('\n')[0]
            STARTING_ANGLE = float(re.search(r'\d+\.\d+',result).group(0))
            
        except subprocess.CalledProcessError:
            STARTING_ANGLE = 0

        try:
            command =  f' grep -e "degrees/frame" {info_txt}'
            result = subprocess.check_output(shlex.split(command)).decode('utf-8').strip().split('\n')[0]
            OSCILLATION_RANGE = float(re.search(r'\d+\.\d+',result).group(0))
            
        except subprocess.CalledProcessError:
            OSCILLATION_RANGE = 0
            
        command =  f' grep -e "wavelength" {info_txt}'
        result = subprocess.check_output(shlex.split(command)).decode('utf-8').strip().split('\n')[0]
        WAVELENGTH =  float(re.search(r'\d+\.\d+',result).group(0))
        
        template_data = {"DETECTOR_DISTANCE":DETECTOR_DISTANCE, "ORGX":ORGX, "ORGY":ORGY, "NFRAMES":NFRAMES, "NAME_TEMPLATE_OF_DATA_FRAMES":NAME_TEMPLATE_OF_DATA_FRAMES, "STARTING_ANGLE":STARTING_ANGLE,"OSCILLATION_RANGE":OSCILLATION_RANGE, "WAVELENGTH":WAVELENGTH}
        
        monitor_file = open(f'XDS.INP', 'w')
        with open(os.path.join(current_data_processing_folder,'template.INP'), 'r') as f:
            src = Template(f.read())
            result = src.substitute(template_data)
            monitor_file.write(result)
        monitor_file.close()
        os.remove(os.path.join(current_data_processing_folder, XDS_INP_template))
        
        
        xds_start(current_data_processing_folder, command_for_data_processing)
            
    
folder_with_raw_data = sys.argv[1]
current_data_processing_folder = sys.argv[2]
ORGX = float(sys.argv[3]) 
ORGY = float(sys.argv[4])
DISTANCE_OFFSET = float(sys.argv[5])
command_for_data_processing = sys.argv[6]
XDS_INP_template = sys.argv[7]
res = [(os.path.join(folder_with_raw_data, file)) for file in os.listdir(folder_with_raw_data) if os.path.isfile(os.path.join(folder_with_raw_data, file)) and ((file.endswith(".h5") or file.endswith(".cxi"))and 'master' in file or file.endswith(".cbf")) ]
res.sort()

if len(res) > 0:
    NAME_TEMPLATE_OF_DATA_FRAMES = res[0]
    
    if 'master' in NAME_TEMPLATE_OF_DATA_FRAMES:
        NAME_TEMPLATE_OF_DATA_FRAMES = re.sub( r'_master\.', '_??????.', NAME_TEMPLATE_OF_DATA_FRAMES)
    else:
        NAME_TEMPLATE_OF_DATA_FRAMES = re.sub(r'\d+\.', lambda m: "?" *(len(m.group())-1) +'.', NAME_TEMPLATE_OF_DATA_FRAMES)
    
    filling_template(folder_with_raw_data, current_data_processing_folder, ORGX, ORGY, DISTANCE_OFFSET, NAME_TEMPLATE_OF_DATA_FRAMES, command_for_data_processing)
    #create this file as a flag that we have already visited this folder
    file = os.path.join(current_data_processing_folder, 'flag.txt') 

    try:
        open(file, 'a').close()
    except OSError:
        pass #Failed creating the file
    else:
        pass #File created
