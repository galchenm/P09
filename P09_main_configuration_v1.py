#!/usr/bin/env python3
# coding: utf8
# Written by Galchenkova M., Tolstikova A., Yefanov O., 2022

"""

"""
import logging
import yaml
import os
import sys
import h5py as h5
import numpy
import numpy.typing
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
import time

os.nice(0)

#This is needed to check the number of running/pending processes
USER='galchenm' #!!!PLEASE CHANGE IT!!!

def setup_logger():
   level = logging.INFO
   logger = logging.getLogger("app")
   logger.setLevel(level)
   log_file = 'Auto-processing-P09-beamline.log'
   formatter = logging.Formatter('%(levelname)s - %(message)s')
   ch = logging.FileHandler(os.path.join(os.getcwd(), log_file))
   
   ch.setLevel(level)
   ch.setFormatter(formatter)
   logger.addHandler(ch)
   logger.info("Setup logger in PID {}".format(os.getpid()))
   print("Log file is {}".format(os.path.join(os.getcwd(), log_file)))


def converter_start(
                    current_raw_folder_for_conversion, converted_directory, current_data_processing_folder
                    ):
    global raw_directory
    global information
    
    #ORGX and ORGY are the origing of the detector that is needed for xds data processing
    ORGX = information['crystallography']['ORGX']
    ORGY = information['crystallography']['ORGY']
    
    #DISTANCE_OFFSET is the offset for recalculation of real detector distance required for XDS
    DISTANCE_OFFSET = information['crystallography']['DISTANCE_OFFSET'] 
    
    command_for_data_processing = information['crystallography']['command_for_processing']
    XDS_INP_template = information['crystallography']['XDS_INP_template']
    experiment_method = information['crystallography']['method']
    cell_file = information['crystallography']['cell_file']
    geometry_for_conversion = information['crystallography']['geometry_for_conversion']
    geometry_for_processing = information['crystallography']['geometry_for_processing']
    
    #h5path is the path in HDF5 file needed only for Lamda generated images
    h5path = information['crystallography']['data_h5path'] 
    
    logger = logging.getLogger('app')
    
    job_file = os.path.join(converted_directory,"%s.sh" % converted_directory.split("/")[-1])
    err_file = os.path.join(converted_directory,"%s.err" % converted_directory.split("/")[-1])
    out_file = os.path.join(converted_directory,"%s.out" % converted_directory.split("/")[-1])
    
    src_file = os.path.join(current_raw_folder_for_conversion, 'info.txt')
    dst_file = os.path.join(converted_directory, 'info.txt')
    shutil.copyfile(src_file, dst_file)
    
    with open(job_file, 'w+') as fh:
        fh.writelines("#!/bin/sh\n")
        fh.writelines("#SBATCH --job=%s\n" % job_file)
        fh.writelines("#SBATCH --partition=upex\n")
        fh.writelines("#SBATCH --time=12:00:00\n")
        fh.writelines("#SBATCH --nodes=1\n")
        fh.writelines("#SBATCH --nice=100\n")
        fh.writelines("#SBATCH --mem=500000\n")
        fh.writelines("#SBATCH --output=%s\n" % out_file)
        fh.writelines("#SBATCH --error=%s\n" % err_file)
        fh.writelines("source /etc/profile.d/modules.sh\n")
        fh.writelines("module load maxwell python/3.9\n")
        command = f'python3 /gpfs/cfel/group/cxi/scratch/2020/EXFEL-2019-Schmidt-Mar-p002450/scratch/galchenm/scripts_for_work/REGAE_dev/om/src/testing/cbf.py --d {current_raw_folder_for_conversion} --g {geometry_for_conversion} --o {converted_directory} --r {raw_directory} --h5p {h5path}'
        fh.writelines(f"{command}\n")
        logger.info(f'INFO: Execute {command}')
        if experiment_method == 'rotational':
            command = f'python3 /gpfs/cfel/group/cxi/scratch/2020/EXFEL-2019-Schmidt-Mar-p002450/scratch/galchenm/scripts_for_work/REGAE_dev/om/src/testing/xds.py {converted_directory} {current_data_processing_folder} {ORGX} {ORGY} {DISTANCE_OFFSET} {command_for_data_processing} {XDS_INP_template}'
            fh.writelines(f"{command}\n")
            logger.info(f'INFO: Execute {command}')
        else:
            serial_data_processing(converted_directory, current_data_processing_folder)
            pass
            #logger.info(f'INFO: Execute {command}')
    os.system("sbatch %s" % job_file)

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
                            folder_with_raw_data, current_data_processing_folder
                           ):
    global information
    logger = logging.getLogger('app')
    
    #logger.info(f'INFO: Execute {command}')
    geometry_fill_template_for_serial(current_data_processing_folder)
    cell_file = information['crystallography']['cell_file']
    command_for_data_processing = information['crystallography']['command_for_processing']

    
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



def xds_start(
              folder_with_raw_data, current_data_processing_folder
              ):
    global information
    
    #ORGX and ORGY are the origing of the detector that is needed for xds data processing
    ORGX = information['crystallography']['ORGX']
    ORGY = information['crystallography']['ORGY']
    
    #DISTANCE_OFFSET is the offset for recalculation of real detector distance required for XDS
    DISTANCE_OFFSET = information['crystallography']['DISTANCE_OFFSET'] 
    
    command_for_data_processing = information['crystallography']['command_for_processing']
    XDS_INP_template = information['crystallography']['XDS_INP_template']
                  
    logger = logging.getLogger('app')
    command = f'python3 /gpfs/cfel/group/cxi/scratch/2020/EXFEL-2019-Schmidt-Mar-p002450/scratch/galchenm/scripts_for_work/REGAE_dev/om/src/testing/xds.py {folder_with_raw_data} {current_data_processing_folder} {ORGX} {ORGY} {DISTANCE_OFFSET} {command_for_data_processing} {XDS_INP_template}'
    logger.info(f'INFO: Execute {command}')
    os.system(command)

setup_logger()

if __name__ == "__main__":
    logger = logging.getLogger('app')
    #reading configuration file
    configuration_file = 'configuration.yaml'
    with open(configuration_file,'r') as file:
        information = yaml.safe_load(file)
    
    experiment_method = information['crystallography']['method']
    raw_directory = information['crystallography']['raw_directory']
    processed_directory = information['crystallography']['processed_directory']
    converted_directory = information['crystallography']['converted_directory']
    
    print(information)
    
    
    if not os.path.exists(converted_directory):
        '''
        If the folder for converted images generated by Lambda detector doesn't exist,
        create it
        '''
        os.mkdir(converted_directory)    
    
    if not os.path.exists(processed_directory):
        '''
        If the folder for processing doesn't exist,
        create it
        '''
        os.mkdir(processed_directory)     
    
    #h5path is the path in HDF5 file needed only for Lamda generated images
    h5path = information['crystallography']['data_h5path'] 
        
    geometry_for_conversion = information['crystallography']['geometry_for_conversion']
    geometry_for_processing = information['crystallography']['geometry_for_processing']
    
    while True: #wait while the directory with raw data appeared
        if os.path.exists(raw_directory):
            break
    
    while True: #main cycle for inspection folders and running data processing
        for root, dirs, files in os.walk(raw_directory):
            
            #ATTENTION! Here I'm checking the existance of info.txt file, if there is none or this file is empty, folder will not be processed!!!
            #So for serial method we also require this file. Generally it is needed to fill the geometry template for data processing
            if any([(file == 'info.txt' and os.stat(os.path.join(root,'info.txt')).st_size != 0) for file in files]):
                
                current_data_processing_folder = f'{processed_directory}{root[len(raw_directory):]}'
                logger.info(f'current_data_processing_folder: {current_data_processing_folder}')
                
                #create the same subfolder structure for processing as in raw folder
                if not os.path.exists(current_data_processing_folder):
                    os.makedirs(current_data_processing_folder, exist_ok=True)
                
                #check how many processes are pending
                pending_command = f'squeue -u {USER} -t pending'
                number_of_pending_processes = subprocess.check_output(shlex.split(pending_command)).decode('utf-8').strip().split('\n')
                if (
                        len(number_of_pending_processes) > 100 or \
                        os.path.exists(os.path.join(current_data_processing_folder, 'CORRECT.LP')) or \
                        os.path.exists(os.path.join(current_data_processing_folder, 'XYCORR.LP')) or \
                        os.path.exists(os.path.join(current_data_processing_folder, 'flag.txt'))
                    ):
                    
                    '''
                    len(number_of_pending_processes) > 1  - we still have pending processes
                    os.path.exists(os.path.join(current_data_processing_folder, 'CORRECT.LP')) - XDS has already finished data processing of this folder
                    os.path.exists(os.path.join(current_data_processing_folder, 'XYCORR.LP')) - XDS has just started data processing of this folder
                    os.path.exists(os.path.join(current_data_processing_folder, 'flag.txt')) - this file indicates that we alredy tried to process this folder
                    '''
                    
                    logger.info(f'{current_data_processing_folder} is skipped')
                    pass
                
                elif(
                        any([file.endswith(".nxs") for file in files]) and \
                        not os.path.exists(f"{converted_directory}{root[len(raw_directory):]}")
                    ): 
                    
                    '''
                    This part is written to deal with images generated by Lambda detector
                    '''
                    
                    os.makedirs(f"{converted_directory}{root[len(raw_directory):]}", exist_ok=True)
                    logger.info(f"CONVERTED: {converted_directory}{root[len(raw_directory):]}")
                    
                    converter_start(root, f"{converted_directory}{root[len(raw_directory):]}",\
                                    current_data_processing_folder)
                elif (
                        any([file.endswith(".nxs") for file in files]) and \
                        os.path.exists(f"{converted_directory}{root[len(raw_directory):]}")
                     ): 
                    
                    #No conversion, just running xds for converted files
                    if experiment_method == 'rotational':
                        logger.info(f"XDS : {converted_directory}{root[len(raw_directory):]}")
                        xds_start(f"{converted_directory}{root[len(raw_directory):]}", current_data_processing_folder)
                    else: #serial
                        serial_data_processing(f"{converted_directory}{root[len(raw_directory):]}", current_data_processing_folder)
                else:
                    logger.info(f'XDS : {root}')
                    if experiment_method == 'rotational':
                        xds_start(root, current_data_processing_folder)
                    else: #serial
                        serial_data_processing(root, current_data_processing_folder)
        time.sleep(20)