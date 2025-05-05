#!/usr/bin/env python3
# coding: utf8
# Written by Galchenkova M., Tolstikova A., Yefanov O., 2022

"""
Example of usage:
-offline mode
python3 autoprocessing_pipeline_P09.py -i /gpfs/cfel/group/cxi/scratch/2020/EXFEL-2019-Schmidt-Mar-p002450/scratch/galchenm/scripts_for_work/REGAE_dev/om/src/testing/configuration.yaml --offline

-offline with block of interest
python3 autoprocessing_pipeline_P09.py -i /gpfs/cfel/group/cxi/scratch/2020/EXFEL-2019-Schmidt-Mar-p002450/scratch/galchenm/scripts_for_work/REGAE_dev/om/src/testing/configuration.yaml --offline --f /gpfs/cfel/group/cxi/scratch/2020/EXFEL-2019-Schmidt-Mar-p002450/scratch/galchenm/scripts_for_work/REGAE_dev/om/src/testing/block_runs.lst

-online mode 
python3 autoprocessing_pipeline_P09.py -i /gpfs/cfel/group/cxi/scratch/2020/EXFEL-2019-Schmidt-Mar-p002450/scratch/galchenm/scripts_for_work/REGAE_dev/om/src/testing/configuration.yaml  --p /asap3/petra3/gpfs/p09/2022/data/11016565/raw/lyso/lamdatest_lyso3/rotational_001
"""
import argparse
import glob
import logging
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

import h5py as h5
import numpy
import numpy.typing
from numpy.typing import NDArray
import yaml
from string import Template

import fabio
from typing import Any, List, Dict, Union, Tuple, TextIO, cast

from utils import crystfel_geometry

os.nice(0)

# This is needed to check the number of running/pending processes
USER = 'galchenm'  # !!!PLEASE CHANGE IT!!!
CURRENT_PATH_OF_SCRIPT = '/gpfs/cfel/group/cxi/scratch/2020/EXFEL-2019-Schmidt-Mar-p002450/scratch/galchenm/scripts_for_work/REGAE_dev/om/src/testing'  # !!!PLEASE CHANGE IT!!!

def parse_cmdline_args():
    parser = argparse.ArgumentParser(
        description=sys.modules[__name__].__doc__,
        formatter_class=CustomFormatter)
    parser.add_argument('-i', type=str, help="The full path to configuration file")
    parser.add_argument('--offline', default=False, action='store_true', help="Use this flag if you want to run this script for offline automatic data processing")
    parser.add_argument('--online', dest='offline', action='store_false', help="Use this flag if you want to run this script for online data processing per each run")
    parser.add_argument('--p', default=None, type=str, help="Use this flag and associate it with the current raw folder to process if you are using online mode per each run")
    parser.add_argument('--f', default=None, type=str, help="Use this flag and associate it with the file with list of runs you want to reprocess, for that before use --offline attribute")
    parser.add_argument('--force', default=False, action='store_true', help="Use this flag if you want to force rerunning in the same processed folder")

    return parser.parse_args()

class CustomFormatter(argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    pass

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
    print("Log file is {}".format(os.path.join(os.getcwd(), log_file)))

def converter_start(
    current_raw_folder_for_conversion, converted_directory, current_data_processing_folder, experiment_method
):
    global raw_directory
    global configuration

    ORGX = configuration['crystallography']['ORGX']
    ORGY = configuration['crystallography']['ORGY']

    DISTANCE_OFFSET = configuration['crystallography']['DISTANCE_OFFSET']
    command_for_processing_rotational = configuration['crystallography']['command_for_processing_rotational']

    XDS_INP_template = configuration['crystallography']['XDS_INP_template']
    cell_file = configuration['crystallography']['cell_file']
    geometry_for_conversion = configuration['crystallography']['geometry_for_conversion']
    geometry_for_processing = configuration['crystallography']['geometry_for_processing']
    h5path = configuration['crystallography']['data_h5path']

    logger = logging.getLogger('app')

    job_file = os.path.join(converted_directory, "%s.sh" % converted_directory.split("/")[-1])
    err_file = os.path.join(converted_directory, "%s.err" % converted_directory.split("/")[-1])
    out_file = os.path.join(converted_directory, "%s.out" % converted_directory.split("/")[-1])

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

        if experiment_method == 'rotational':
            command = f'python3 {CURRENT_PATH_OF_SCRIPT}/xds.py {converted_directory} {current_data_processing_folder} {ORGX} {ORGY} {DISTANCE_OFFSET} {command_for_processing_rotational} {XDS_INP_template}'
            fh.writelines(f"{command}\n")
        else:
            serial_start(converted_directory, current_data_processing_folder)

    os.system("sbatch %s" % job_file)

def serial_start(folder_with_raw_data, current_data_processing_folder):
    global configuration
    ORGX = configuration['crystallography']['ORGX']
    ORGY = configuration['crystallography']['ORGY']
    DISTANCE_OFFSET = configuration['crystallography']['DISTANCE_OFFSET']
    cell_file = configuration['crystallography']['cell_file']
    geometry_filename_template = configuration["crystallography"]["geometry_for_processing"]
    command_for_processing_serial = configuration['crystallography']['command_for_processing_serial']
    data_h5path = configuration['crystallography']['data_h5path']

    command = f'python3 {CURRENT_PATH_OF_SCRIPT}/serial.py {folder_with_raw_data} {current_data_processing_folder} {ORGX} {ORGY} {DISTANCE_OFFSET} {command_for_processing_serial} {geometry_filename_template} {cell_file} {data_h5path}'
    os.system(command)

def xds_start(folder_with_raw_data, current_data_processing_folder):
    global configuration

    ORGX = configuration['crystallography']['ORGX']
    ORGY = configuration['crystallography']['ORGY']
    DISTANCE_OFFSET = configuration['crystallography']['DISTANCE_OFFSET']
    command_for_processing_rotational = configuration['crystallography']['command_for_processing_rotational']
    XDS_INP_template = configuration['crystallography']['XDS_INP_template']

    command = f'python3 {CURRENT_PATH_OF_SCRIPT}/xds.py {folder_with_raw_data} {current_data_processing_folder} {ORGX} {ORGY} {DISTANCE_OFFSET} {command_for_processing_rotational} {XDS_INP_template}'
    os.system(command)

def main(root):
    global configuration
    global is_force

    raw_directory = configuration['crystallography']['raw_directory']
    processed_directory = configuration['crystallography']['processed_directory']
    converted_directory = configuration['crystallography']['converted_directory']

    files = [f for f in os.listdir(root) if os.path.isfile(os.path.join(root, f))]

    if any([(file == 'info.txt' and os.stat(os.path.join(root, 'info.txt')).st_size != 0) for file in files]):
        info_txt = glob.glob(os.path.join(root, 'info.txt'))[0]
        experiment_method = ''
        with open(info_txt, 'r') as f:
            experiment_method = next(f)
        experiment_method = experiment_method.split(':')[-1].strip()

        current_data_processing_folder = f'{processed_directory}{root[len(raw_directory):]}'
        if not os.path.exists(current_data_processing_folder):
            os.makedirs(current_data_processing_folder, exist_ok=True)

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
            os.path.exists(os.path.join(current_data_processing_folder, 'flag.txt')) or \
            len(number_of_pending_processes) > 100 or \
            os.path.exists(os.path.join(current_data_processing_folder, 'CORRECT.LP')) or \
            os.path.exists(os.path.join(current_data_processing_folder, 'XYCORR.LP'))
        ):
            print(f'{current_data_processing_folder} is skipped')
        elif (
            any([file.endswith(".nxs") for file in files]) and \
            not os.path.exists(f"{converted_directory}{root[len(raw_directory):]}")
        ):
            os.makedirs(f"{converted_directory}{root[len(raw_directory):]}", exist_ok=True)
            converter_start(root, f"{converted_directory}{root[len(raw_directory):]}", current_data_processing_folder, experiment_method)
        elif (
            any([file.endswith(".nxs") for file in files]) and \
            os.path.exists(f"{converted_directory}{root[len(raw_directory):]}")
        ):
            if experiment_method == 'rotational':
                xds_start(f"{converted_directory}{root[len(raw_directory):]}", current_data_processing_folder)
            else:
                serial_start(f"{converted_directory}{root[len(raw_directory):]}", current_data_processing_folder)
        else:
            if experiment_method == 'rotational':
                xds_start(root, current_data_processing_folder)
            else:
                serial_start(root, current_data_processing_folder)
    else:
        print(f"In {root} there is no info.txt file.")
        pass

def folders_in(path_to_parent):
    return (os.path.join(path_to_parent, fname) for fname in os.listdir(path_to_parent) if os.path.isdir(os.path.join(path_to_parent, fname)))

def process_folders():
    while True:
        for root, dirs, files in os.walk(raw_directory):
            if len(list(folders_in(root))) > 0:
                continue
            main(root)
        time.sleep(2)

setup_logger()

if __name__ == "__main__":
    logger = logging.getLogger('app')
    args = parse_cmdline_args()
    configuration_file = args.i if args.i is not None else f'{CURRENT_PATH_OF_SCRIPT}/configuration.yaml'
    is_force = args.force

    print('is_force = ', is_force)

    with open(configuration_file, 'r') as file:
        configuration = yaml.safe_load(file)

    raw_directory = configuration['crystallography']['raw_directory']
    processed_directory = configuration['crystallography']['processed_directory']
    converted_directory = configuration['crystallography']['converted_directory']

    os.makedirs(converted_directory, exist_ok=True)
    os.makedirs(processed_directory, exist_ok=True)

    while not os.path.exists(raw_directory):
        pass

    if args.offline:
        to_process = []
        filename = args.f
        if filename is not None:
            with open(filename, 'r') as file:
                for line in file:
                    line = line.strip()
                    if len(line) > 0 and line not in to_process: 
                        to_process.append(line)

            for root, dirs, files in os.walk(raw_directory):
                for pattern in to_process:
                    if pattern in root[len(raw_directory):]:
                        if len(list(folders_in(root))) > 0:
                            continue
                        main(root)
        else:
            process_folders()
    else:
        if args.p is None:
            print('ERROR: YOU HAVE TO GIVE THE ABSOLUTE PATH TO THE RAW FOLDER YOU ARE GOING TO PROCESS IF YOU ARE IN THIS MODE!')
        else:
            main(args.p)
