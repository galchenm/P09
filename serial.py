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

def geometry_fill_template_for_serial(current_data_processing_folder):
    global information
    
    os.chdir(current_data_processing_folder)
    
    geometry_filename_template = information["crystallography"]["geometry_for_processing"]
    
    shutil.copy(geometry_filename_template, os.path.join(current_data_processing_folder, 'template.geom'))
    
    DETECTOR_DISTANCE = information['crystallography']['DETECTOR_DISTANCE'] + information['crystallography']['DISTANCE_OFFSET'] 
    
    ORGX = (-1)*information['crystallography']['ORGX']
    ORGY = (-1)*information['crystallography']['ORGY']
    PHOTON_ENERGY = information['crystallography']['energy']
    data_h5path = information['crystallography']['data_h5path']
    
    template_data = {
                        "DETECTOR_DISTANCE":DETECTOR_DISTANCE, "ORGX":ORGX, "ORGY":ORGY,\
                        "PHOTON_ENERGY":PHOTON_ENERGY, "data_h5path": data_h5path
                    }
    geometry_filename = 'geometry.geom'
    monitor_file = open(geometry_filename, 'w')
    with open(os.path.join(current_data_processing_folder,'template.geom'), 'r') as f:
        src = Template(f.read())
        result = src.substitute(template_data)
        monitor_file.write(result)
    monitor_file.close()
    os.remove(os.path.join(current_data_processing_folder, 'template.geom'))
    
    
def serial_data_processing(
                            folder_with_raw_data, current_data_processing_folder\
                            command_for_data_processing, cell_file
                           ):
    job_file = os.path.join(current_data_processing_folder,"%s_serial.sh" % current_data_processing_folder.split("/")[-1])
    err_file = os.path.join(current_data_processing_folder,"%s_serial.err" % current_data_processing_folder.split("/")[-1])
    out_file = os.path.join(current_data_processing_folder,"%s_serial.out" % current_data_processing_folder.split("/")[-1])
    
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
        fh.writelines("module load xray maxwell crystfel\n")
        fh.writelines(f"{command_for_data_processing} {folder_with_raw_data} {current_data_processing_folder} {cell_file}\n")
    os.system("sbatch %s" % job_file)


def filling_template(
                        folder_with_raw_data, current_data_processing_folder, geometry_filename_template, data_h5path\
                        ORGX=0 , ORGY=0, DISTANCE_OFFSET=0, command_for_data_processing='turbo-index-P09', cell_file='lyzo.pdb'
                    ):

    
    os.chdir(current_data_processing_folder)
    
    shutil.copy(geometry_filename_template, os.path.join(current_data_processing_folder, 'template.geom'))

    info_txt = ''
    if len(glob.glob(os.path.join(folder_with_raw_data,'info.txt')))>0 and os.stat(os.path.join(folder_with_raw_data,'info.txt')).st_size != 0:
        info_txt = glob.glob(os.path.join(folder_with_raw_data,'info.txt'))[0]
        
        command = f' grep -e "distance" {info_txt}'
        result = subprocess.check_output(shlex.split(command)).decode('utf-8').strip().split('\n')[0]
        #we assume here DETECTOR_DISTANCE in info.txt and DISTANCE_OFFSET from configuarion file are in [mm]!!
        #we have to convert for crystfel it to [m]
        DETECTOR_DISTANCE = (float(re.search(r'\d+\.\d+',result).group(0)) + DISTANCE_OFFSET)/1000
           
        command =  f' grep -e "wavelength" {info_txt}'
        result = subprocess.check_output(shlex.split(command)).decode('utf-8').strip().split('\n')[0]
        WAVELENGTH =  float(re.search(r'\d+\.\d+',result).group(0))
        PHOTON_ENERGY = 12400 / WAVELENGTH
        template_data = {
                            "DETECTOR_DISTANCE":DETECTOR_DISTANCE, "ORGX":ORGX, "ORGY":ORGY,\
                            "PHOTON_ENERGY":PHOTON_ENERGY, "data_h5path": data_h5path
                        }
        geometry_filename = 'geometry.geom'
        monitor_file = open(geometry_filename, 'w')
        with open(os.path.join(current_data_processing_folder,'template.geom'), 'r') as f:
            src = Template(f.read())
            result = src.substitute(template_data)
            monitor_file.write(result)
        monitor_file.close()
        os.remove(os.path.join(current_data_processing_folder, 'template.geom'))
        serial_data_processing(
                            folder_with_raw_data, current_data_processing_folder\
                            command_for_data_processing, cell_file
                           )

folder_with_raw_data = sys.argv[1]
current_data_processing_folder = sys.argv[2]
ORGX = (-1)*float(sys.argv[3]) 
ORGY = (-1)*float(sys.argv[4])
DISTANCE_OFFSET = float(sys.argv[5])
command_for_data_processing = sys.argv[6]
geometry_filename_template = sys.argv[7]            
cell_file = sys.argv[8] 


filling_template(
                        folder_with_raw_data, current_data_processing_folder, geometry_filename_template, data_h5path\
                        ORGX, ORGY, DISTANCE_OFFSET, command_for_data_processing, cell_file
                    )
                    

#create this file as a flag that we have already visited this folder                    
file = os.path.join(current_data_processing_folder, 'flag.txt') 

try:
    open(file, 'a').close()
except OSError:
    pass #Failed creating the file
else:
    pass #File created                    
   