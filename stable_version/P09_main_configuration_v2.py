#!/usr/bin/env python3
# coding: utf8
# Written by Galchenkova M., Tolstikova A., Yefanov O., 2022

"""
Example of usage:
-offline mode
 python3 P09_main_configuration_v2.py -i /gpfs/cfel/group/cxi/scratch/2020/EXFEL-2019-Schmidt-Mar-p002450/scratch/galchenm/scripts_for_work/REGAE_dev/om/src/testing/configuration.yaml --offline
 
-online mode 
  python3 P09_main_configuration_v2.py -i /gpfs/cfel/group/cxi/scratch/2020/EXFEL-2019-Schmidt-Mar-p002450/scratch/galchenm/scripts_for_work/REGAE_dev/om/src/testing/configuration.yaml  --p /asap3/petra3/gpfs/p09/2022/data/11016565/raw/lyso/lamdatest_lyso3/rotational_001
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
import argparse


os.nice(0)

#This is needed to check the number of running/pending processes
USER='galchenm' #'guents' #!!!PLEASE CHANGE IT!!!
CURRENT_PATH_OF_SCRIPT = '/asap3/petra3/gpfs/p09/2023/data/11016750/shared/autoprocessing'  #!!!PLEASE CHANGE IT!!!

class CustomFormatter(argparse.RawDescriptionHelpFormatter,
                      argparse.ArgumentDefaultsHelpFormatter):
    pass

def parse_cmdline_args():
    parser = argparse.ArgumentParser(
        description=sys.modules[__name__].__doc__,
        formatter_class=CustomFormatter)
    parser.add_argument('-i', type=str, help="The full path to configuration file")
    parser.add_argument('--offline', default=False, action='store_true', help="Use this flag if you want to run this script for offline automatic data processing")
    parser.add_argument('--online', dest='offline', action='store_false', help="Use this flag if you want to run this script for online data processing per each run")
    parser.add_argument('--p', default=None, type=str, help="Use this flag and associate it with the current raw folder to process if you are using online mode per each run")
    return parser.parse_args()


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
   #logger.info("Setup logger in PID {}".format(os.getpid()))
   print("Log file is {}".format(os.path.join(os.getcwd(), log_file)))


def converter_start(
                    current_raw_folder_for_conversion, converted_directory, current_data_processing_folder, experiment_method
                    ):
    global raw_directory
    global configuration
    
    #ORGX and ORGY are the origing of the detector that is needed for xds data processing
    ORGX = configuration['crystallography']['ORGX']
    ORGY = configuration['crystallography']['ORGY']
    
    #DISTANCE_OFFSET is the offset for recalculation of real detector distance required for XDS
    DISTANCE_OFFSET = configuration['crystallography']['DISTANCE_OFFSET'] 
    
    command_for_processing_rotational = configuration['crystallography']['command_for_processing_rotational']
    
    
    XDS_INP_template = configuration['crystallography']['XDS_INP_template']
    
    cell_file = configuration['crystallography']['cell_file']
    geometry_for_conversion = configuration['crystallography']['geometry_for_conversion']
    geometry_for_processing = configuration['crystallography']['geometry_for_processing']
    
    #h5path is the path in HDF5 file needed only for Lambda generated images
    h5path = configuration['crystallography']['data_h5path'] 
    
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
        command = f'python3 {CURRENT_PATH_OF_SCRIPT}/cbf.py --d {current_raw_folder_for_conversion} --g {geometry_for_conversion} --o {converted_directory} --r {raw_directory} --h5p {h5path}'
        fh.writelines(f"{command}\n")
        ##logger.info(f'INFO: Execute {command}')
        if experiment_method == 'rotational':
            command = f'python3 {CURRENT_PATH_OF_SCRIPT}/xds.py {converted_directory} {current_data_processing_folder} {ORGX} {ORGY} {DISTANCE_OFFSET} {command_for_processing_rotational} {XDS_INP_template}'
            fh.writelines(f"{command}\n")
            ##logger.info(f'INFO: Execute {command}')
        else:
            serial_start(converted_directory, current_data_processing_folder)
            
            ##logger.info(f'INFO: Execute {command}')
    os.system("sbatch %s" % job_file)
    
def serial_start(
              folder_with_raw_data, current_data_processing_folder
              ):
    global configuration
    
    #ORGX and ORGY are the origing of the detector that is needed for xds data processing
    ORGX = configuration['crystallography']['ORGX']
    ORGY = configuration['crystallography']['ORGY']
    
    #DISTANCE_OFFSET is the offset for recalculation of real detector distance
    DISTANCE_OFFSET = configuration['crystallography']['DISTANCE_OFFSET'] 
    
    cell_file = configuration['crystallography']['cell_file']
    geometry_filename_template = configuration["crystallography"]["geometry_for_processing"]
    
    command_for_processing_serial = configuration['crystallography']['command_for_processing_serial']
    data_h5path = configuration['crystallography']['data_h5path'] 
    #logger = logging.getLogger('app')
    command = f'python3 {CURRENT_PATH_OF_SCRIPT}/serial.py {folder_with_raw_data} {current_data_processing_folder} {ORGX} {ORGY} {DISTANCE_OFFSET} {command_for_processing_serial} {geometry_filename_template} {cell_file} {data_h5path}'
    ##logger.info(f'INFO: Execute {command}')
    os.system(command)
    
def xds_start(
              folder_with_raw_data, current_data_processing_folder
              ):
    global configuration
    
    #ORGX and ORGY are the origing of the detector that is needed for xds data processing
    ORGX = configuration['crystallography']['ORGX']
    ORGY = configuration['crystallography']['ORGY']
    
    #DISTANCE_OFFSET is the offset for recalculation of real detector distance required for XDS
    DISTANCE_OFFSET = configuration['crystallography']['DISTANCE_OFFSET'] 
    
    command_for_processing_rotational = configuration['crystallography']['command_for_processing_rotational']
    XDS_INP_template = configuration['crystallography']['XDS_INP_template']
                  
    #logger = logging.getLogger('app')
    command = f'python3 {CURRENT_PATH_OF_SCRIPT}/xds.py {folder_with_raw_data} {current_data_processing_folder} {ORGX} {ORGY} {DISTANCE_OFFSET} {command_for_processing_rotational} {XDS_INP_template}'
    ##logger.info(f'INFO: Execute {command}')
    os.system(command)


def main(root):
    global configuration
    print(f'We are here: {root}')
    raw_directory = configuration['crystallography']['raw_directory']
    processed_directory = configuration['crystallography']['processed_directory']
    converted_directory = configuration['crystallography']['converted_directory']

    #ATTENTION! Here I'm checking the existance of info.txt file, if there is none or this file is empty, folder will not be processed!!!
    #So for serial method we also require this file. Generally it is needed to fill the geometry template for data processing
    files =  [f for f in os.listdir(root) if os.path.isfile(os.path.join(root, f))]
    
    if any([(file == 'info.txt' and os.stat(os.path.join(root,'info.txt')).st_size != 0) for file in files]):
        
        info_txt = glob.glob(os.path.join(root,'info.txt'))[0]
        
        #Determine experimental method (rotational or others) from info.txt for calling further proper data processing pipeline
        experiment_method = ''
        with open(info_txt, 'r') as f:
            experiment_method = next(f)
        experiment_method = experiment_method.split(':')[-1].strip()
        
        
        current_data_processing_folder = f'{processed_directory}{root[len(raw_directory):]}'
        ##logger.info(f'current_data_processing_folder ({experiment_method} method): {current_data_processing_folder}')
        
        #create the same subfolder structure for processing as in raw folder
        if not os.path.exists(current_data_processing_folder):
            os.makedirs(current_data_processing_folder, exist_ok=True)
        
        #check how many processes are pending in order not to submit
        pending_command = f'squeue -u {USER} -t pending'
        number_of_pending_processes = subprocess.check_output(shlex.split(pending_command)).decode('utf-8').strip().split('\n')
        if (
                os.path.exists(os.path.join(current_data_processing_folder, 'flag.txt')) or\
                len(number_of_pending_processes) > 100 or \
                os.path.exists(os.path.join(current_data_processing_folder, 'CORRECT.LP')) or \
                os.path.exists(os.path.join(current_data_processing_folder, 'XYCORR.LP')) 
            ):
            
            '''
            len(number_of_pending_processes) > 1  - we still have pending processes
            os.path.exists(os.path.join(current_data_processing_folder, 'CORRECT.LP')) - XDS has already finished data processing of this folder
            os.path.exists(os.path.join(current_data_processing_folder, 'XYCORR.LP')) - XDS has just started data processing of this folder
            os.path.exists(os.path.join(current_data_processing_folder, 'flag.txt')) - this file indicates that we already tried to process this folder (doesn't mean successfully
            '''
            
            print(f'{current_data_processing_folder} is skipped')
            
        
        elif(
                any([file.endswith(".nxs") for file in files]) and \
                not os.path.exists(f"{converted_directory}{root[len(raw_directory):]}")
            ): 
            
            '''
            This part is written to deal with images generated by Lambda detector
            '''
            
            os.makedirs(f"{converted_directory}{root[len(raw_directory):]}", exist_ok=True)
            print(f"CONVERTED: {converted_directory}{root[len(raw_directory):]}")
            
            converter_start(root, f"{converted_directory}{root[len(raw_directory):]}",\
                            current_data_processing_folder, experiment_method)
        elif (
                any([file.endswith(".nxs") for file in files]) and \
                os.path.exists(f"{converted_directory}{root[len(raw_directory):]}")
             ): 
            
            #No conversion, just running xds for converted files
            if experiment_method == 'rotational':
                print(f"XDS: {converted_directory}{root[len(raw_directory):]}")
                
                xds_start(f"{converted_directory}{root[len(raw_directory):]}", current_data_processing_folder)
            else: #serial
                print(f"SERIAL: {converted_directory}{root[len(raw_directory):]}")
                
                serial_start(f"{converted_directory}{root[len(raw_directory):]}", current_data_processing_folder)
        else:
            
            if experiment_method == 'rotational':
                print(f'XDS: {root}')
                
                xds_start(root, current_data_processing_folder)
            else: #serial
                print(f'SERIAL: {root}')
                
                serial_start(root, current_data_processing_folder)
    else:
        print(f"In {root} there is no info.txt file.")
        pass

setup_logger()

if __name__ == "__main__":
    logger = logging.getLogger('app')
    #reading configuration file
    args = parse_cmdline_args()
    configuration_file = args.i if args.i is not None else f'{CURRENT_PATH_OF_SCRIPT}/configuration.yaml'
    
    with open(configuration_file,'r') as file:
        configuration = yaml.safe_load(file)
    
    raw_directory = configuration['crystallography']['raw_directory']
    processed_directory = configuration['crystallography']['processed_directory']
    converted_directory = configuration['crystallography']['converted_directory']
    
    
    #logger.info(f"Configuration: {configuration}")
    
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
    
    
    while True: #wait while the directory with raw data appeared
        if os.path.exists(raw_directory):
            break
    
    if args.offline:
        while True: #main cycle for inspection folders and running data processing
            for root, dirs, files in os.walk(raw_directory):
                main(root)
                
            time.sleep(2)
    else:
        if args.p is None:
            print('ERROR: YOU HAVE TO GIVE THE ABSOLUTE PATH TO THE RAW FOLDER YOU ARE GOING TO PROCESS IF YOU ARE IN THIS MODE!')
        else:
            main(args.p)
