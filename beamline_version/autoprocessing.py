#!/usr/bin/env python3
# coding: utf8
# Written by Galchenkova M., Tolstikova A., Yefanov O., 2022

"""
Example of usage:
-offline mode
 python3 autoprocessing.py -i configuration.yaml --offline

-offline with block of interest
python3 autoprocessing.py -i configuration.yaml --offline --f block_runs.lst

 -offline with force feature
 python3 autoprocessing.py -i configuration.yaml --offline --f block_runs.lst --force
 
-online mode 
  python3 autoprocessing.py -i configuration.yaml  --p /asap3/petra3/gpfs/p09/2022/data/11016565/raw/lyso/lamdatest_lyso3/rotational_001
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
CURRENT_PATH_OF_SCRIPT = os.path.abspath(__file__)

class CustomFormatter(argparse.RawDescriptionHelpFormatter,
                    argparse.ArgumentDefaultsHelpFormatter):
    pass

def parse_cmdline_args():
    parser = argparse.ArgumentParser(
        description=sys.modules[__name__].__doc__,
        formatter_class=CustomFormatter)
    parser.add_argument('-config','--config', type=str, help="The full path to configuration file")
    parser.add_argument('--offline', default=False, action='store_true', help="Use this flag if you want to run this script for offline automatic data processing")
    parser.add_argument('--online', dest='offline', action='store_false', help="Use this flag if you want to run this script for online data processing per each run")
    parser.add_argument('--path', default=None, type=str, help="Use this flag and associate it with the current raw folder to process if you are using online mode per each run")
    parser.add_argument('--blocks', default=None, type=str, help="Use this flag and associate it with the file with list of runs you want to reprocess, for that before use --offline attribute")
    
    parser.add_argument('--force', default=False, action='store_true', help="Use this flag if you want to force rerunning in the same processed folder")

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
   logger.info("Setup logger in PID {}".format(os.getpid()))
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
    global is_force
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
    global is_force
    
    USER = configuration['crystallography']['USERNAME']
    RESERVED_NODE = configuration['crystallography']['RESERVED_NODE']
    
    #ORGX and ORGY are the origing of the detector that is needed for xds data processing
    ORGX = configuration['crystallography']['ORGX']
    ORGY = configuration['crystallography']['ORGY']
    
    #DISTANCE_OFFSET is the offset for recalculation of real detector distance required for XDS
    DISTANCE_OFFSET = configuration['crystallography']['DISTANCE_OFFSET'] 
    
    command_for_processing_rotational = configuration['crystallography']['command_for_processing_rotational']
    XDS_INP_template = configuration['crystallography']['XDS_INP_template']
    
    logger = logging.getLogger('app')
    command = f'python3 {CURRENT_PATH_OF_SCRIPT}/xds.py {folder_with_raw_data} {current_data_processing_folder} {ORGX} {ORGY} {DISTANCE_OFFSET} {command_for_processing_rotational} {XDS_INP_template}'
    logger.info(f'INFO: Execute {command}')
    os.system(command)


def main(root):
    global configuration
    global is_force
    
    print(f'We are here: {root}')
    raw_directory = configuration['crystallography']['raw_directory']
    processed_directory = configuration['crystallography']['processed_directory']
    converted_directory = configuration['crystallography']['converted_directory']

    #ATTENTION! Here I'm checking the existance of info.txt file, if there is none or this file is empty, folder will not be processed!!!
    #So for serial method we also require this file. Generally it is needed to fill the geometry template for data processing
    files =  [f for f in os.listdir(root) if os.path.isfile(os.path.join(root, f))]
    other_files = [file for file in os.listdir(root) if os.path.isfile(os.path.join(root, file))]

    if any([(file == 'info.txt' and os.stat(os.path.join(root,'info.txt')).st_size != 0) for file in files]) and len(other_files)>1:
        
        info_txt = glob.glob(os.path.join(root,'info.txt'))[0]
        
        #Determine experimental method (rotational or others) from info.txt for calling further proper data processing pipeline
        experiment_method = ''
        with open(info_txt, 'r') as f:
            experiment_method = next(f)
        experiment_method = experiment_method.split(':')[-1].strip()
        
        current_data_processing_folder = f'{processed_directory}{root[len(raw_directory):]}'
        logger.info(f'current_data_processing_folder ({experiment_method} method): {current_data_processing_folder}')
        
        #create the same subfolder structure for processing as in raw folder
        if not os.path.exists(current_data_processing_folder):
            os.makedirs(current_data_processing_folder, exist_ok=True)
            os.chmod(current_data_processing_folder, 0o777)
        
        #check how many processes are pending in order not to submit
        pending_command = f'squeue -u {USER} -t pending'
        number_of_pending_processes = subprocess.check_output(shlex.split(pending_command)).decode('utf-8').strip().split('\n')
        
        if is_force and os.path.exists(os.path.join(current_data_processing_folder, 'flag.txt')):
            
            for filename in os.listdir(current_data_processing_folder):
                file_path = os.path.join(current_data_processing_folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print('Failed to delete %s. Reason: %s' % (file_path, e))
            print(f'In {current_data_processing_folder} we delete the previous processed results')            
        
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
            
            logger.info(f'{current_data_processing_folder} is skipped')
            
        
        elif(
                any([file.endswith(".nxs") for file in files]) and \
                not os.path.exists(f"{converted_directory}{root[len(raw_directory):]}")
            ): 
            
            '''
            This part is written to deal with images generated by Lambda detector
            '''
            
            os.makedirs(f"{converted_directory}{root[len(raw_directory):]}", exist_ok=True)
            os.chmod(f"{converted_directory}{root[len(raw_directory):]}", 0o777)
            logger.info(f"CONVERTED: {converted_directory}{root[len(raw_directory):]}")
            
            converter_start(root, f"{converted_directory}{root[len(raw_directory):]}",\
                            current_data_processing_folder, experiment_method)
        elif (
                any([file.endswith(".nxs") for file in files]) and \
                os.path.exists(f"{converted_directory}{root[len(raw_directory):]}")
            ): 
            
            #No conversion, just running xds for converted files
            if experiment_method == 'rotational':
                logger.info(f"XDS: {converted_directory}{root[len(raw_directory):]}")
                
                xds_start(f"{converted_directory}{root[len(raw_directory):]}", current_data_processing_folder)
            else: #serial
                logger.info(f"SERIAL: {converted_directory}{root[len(raw_directory):]}")
                
                serial_start(f"{converted_directory}{root[len(raw_directory):]}", current_data_processing_folder)
        else:
            
            if experiment_method == 'rotational':
                logger.info(f'XDS: {root}')
                
                xds_start(root, current_data_processing_folder)
            else: #serial
                logger.info(f'SERIAL: {root}')
                
                serial_start(root, current_data_processing_folder)
    else:
        logger.info(f"In {root} there is no info.txt file.")
        pass

def filling_configuration_file(configuration_file_template, json_beamtime_file=None):
    """
    Fills a YAML configuration template using selected values from a JSON beamtime file.

    Parameters:
    - json_beamtime_file (str): Path to the JSON file containing beamtime data.
    - configuration_file_template (str): Path to the YAML template file with placeholders.

    Returns:
    - str: Path to the generated filled YAML file.
    """

    with open(configuration_file_template, "r") as f:
        template_text = f.read()
        
    templates_folder = os.path.join(CURRENT_PATH_OF_SCRIPT, 'templates')
    
    
    if json_beamtime_file is not None:
        with open(json_beamtime_file, "r") as f:
            beamtime_data = json.load(f)
        
        
        values = {
            "beamtimeID": beamtime_data.get("beamtimeID", ""),
            "username": beamtime_data.get("username", ""),
            "reservedNode": beamtime_data.get("reserved_node", ""),
            "XDS_INP_template": os.path.join(templates_folder, 'XDS.INP')
            "geometry_for_conversion": os.path.join(templates_folder, 'lambda1M5.geom')
            "geometry_for_processing": os.path.join(templates_folder, 'pilatus6M.geom')
        
        }
    else:
        values = {
            "XDS_INP_template": os.path.join(templates_folder, 'XDS.INP')
            "geometry_for_conversion": os.path.join(templates_folder, 'lambda1M5.geom')
            "geometry_for_processing": os.path.join(templates_folder, 'pilatus6M.geom')
        
        }
    
    filled_template = Template(template_text).safe_substitute(values)

    output_file = os.path.join(f"/gpfs/current/processed/filled_config.yaml")
    with open(output_file, "w") as f:
        f.write(filled_template)

    print(f"Generated file: {output_file}")
    return output_file

# Setup logger
setup_logger()

if __name__ == "__main__":
    logger = logging.getLogger('app')
    #reading configuration file
    args = parse_cmdline_args()
    configuration_file = args.config if args.config is not None else f'{CURRENT_PATH_OF_SCRIPT}/templates/configuration_template.yaml'
    
    #If the configuration file is a template, we fill it with values from the beamtime JSON file
    json_beamtime_file = os.path.join(os.getcwd(), 'beamtime.json')
    if not os.path.exists(json_beamtime_file):
        print(f"ERROR: The beamtime JSON file {json_beamtime_file} does not exist.")
        
        
    configuration_file = filling_configuration_file(configuration_file, json_beamtime_file) 
    
    is_force = args.force

    with open(configuration_file,'r') as file:
        configuration = yaml.safe_load(file)
    
    raw_directory = configuration['crystallography']['raw_directory']
    processed_directory = configuration['crystallography']['processed_directory']
    converted_directory = configuration['crystallography']['converted_directory']
    USER = configuration['crystallography']['USERNAME']
    
    logger.info(f"Configuration: {configuration}")
    
    if not os.path.exists(converted_directory):
        '''
        If the folder for converted images generated by Lambda detector doesn't exist,
        create it
        '''
        os.makedirs(converted_directory)
        os.chmod(converted_directory, 0o777)    
    
    if not os.path.exists(processed_directory):
        '''
        If the folder for processing doesn't exist,
        create it
        '''
        os.makedirs(processed_directory)
        os.chmod(processed_directory, 0o777)     
    
    
    while True: #wait while the directory with raw data appeared
        if os.path.exists(raw_directory):
            break
    
    if args.offline:
        to_process = []
        blocks_of_files = args.blocks
        if blocks_of_files is not None:
            with open(blocks_of_files, 'r') as file:
                for line in file:
                    line = line.strip()
                    if len(line) > 0 and line not in to_process: 
                        to_process.append(line)
            

            for root, dirs, files in os.walk(raw_directory):
                for pattern in to_process:
                    
                    if pattern in root[len(raw_directory):]:
                        main(root)
                        logger.info(f'INFO: Processed {root}')
        else:
            while True: #main cycle for inspection folders and running data processing
                for root, dirs, files in os.walk(raw_directory):
                    main(root)
                    logger.info(f'INFO: Processed {root}')
                time.sleep(2)
    else:
        if args.path is None:
            logger.error('ERROR: YOU HAVE TO GIVE THE ABSOLUTE PATH TO THE RAW FOLDER YOU ARE GOING TO PROCESS IF YOU ARE IN THIS MODE!')
        else:
            main(args.path)
            logger.info(f'INFO: Processed {args.path}')