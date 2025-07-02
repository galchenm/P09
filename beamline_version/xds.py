#!/usr/bin/env python3
# coding: utf8
# Written by Galchenkova M., Tolstikova A., Yefanov O., 2022

import os
import sys
import glob
import re
import shutil
import subprocess
import shlex
from string import Template

os.nice(0)

def xds_start(current_data_processing_folder, command_for_data_processing):
    job_file = os.path.join(current_data_processing_folder, f"{current_data_processing_folder.split('/')[-1]}_XDS.sh")
    err_file = os.path.join(current_data_processing_folder, f"{current_data_processing_folder.split('/')[-1]}_XDS.err")
    out_file = os.path.join(current_data_processing_folder, f"{current_data_processing_folder.split('/')[-1]}_XDS.out")

    with open(job_file, 'w+') as fh:
        fh.writelines("#!/bin/sh\n")
        fh.writelines(f"#SBATCH --job={job_file}\n")
        fh.writelines("#SBATCH --partition=upex\n")
        fh.writelines("#SBATCH --time=12:00:00\n")
        fh.writelines("#SBATCH --nodes=1\n")
        fh.writelines("#SBATCH --nice=100\n")
        fh.writelines("#SBATCH --mem=500000\n")
        fh.writelines(f"#SBATCH --output={out_file}\n")
        fh.writelines(f"#SBATCH --error={err_file}\n")
        fh.writelines("source /etc/profile.d/modules.sh\n")
        fh.writelines("module load xray\n")
        fh.writelines(f"{command_for_data_processing}\n")

    os.system(f"sbatch {job_file}")


def filling_template(folder_with_raw_data, current_data_processing_folder, ORGX=0, ORGY=0,
                     DISTANCE_OFFSET=0, NAME_TEMPLATE_OF_DATA_FRAMES='blablabla',
                     command_for_data_processing='xds_par'):
    global XDS_INP_template

    os.chdir(current_data_processing_folder)
    shutil.copy(XDS_INP_template, os.path.join(current_data_processing_folder, 'template.INP'))

    info_txt = ''
    info_files = glob.glob(os.path.join(folder_with_raw_data, 'info.txt'))
    if info_files and os.stat(info_files[0]).st_size != 0:
        info_txt = info_files[0]

        command = f'grep -e "distance" {info_txt}'
        result = subprocess.check_output(shlex.split(command)).decode('utf-8').strip().split('\n')[0]
        DETECTOR_DISTANCE = float(re.search(r'\d+\.\d+', result).group(0)) + DISTANCE_OFFSET
        
        if ORGX == 0:
            result = subprocess.check_output(shlex.split(f'grep -e "ORGX" {info_txt}')).decode('utf-8').strip().split('\n')[0]
            ORGX = float(re.search(r'\d+\.\d+', result).group(0))
        if ORGY == 0:
            result = subprocess.check_output(shlex.split(f'grep -e "ORGY" {info_txt}')).decode('utf-8').strip().split('\n')[0]
            ORGY = float(re.search(r'\d+\.\d+', result).group(0))
            
        command = f'grep -e "frames" {info_txt}'
        result = subprocess.check_output(shlex.split(command)).decode('utf-8').strip().split('\n')[0]
        NFRAMES = int(re.search(r'\d+', result).group(0))

        try:
            command = f'grep -e "start angle" {info_txt}'
            result = subprocess.check_output(shlex.split(command)).decode('utf-8').strip().split('\n')[0]
            STARTING_ANGLE = float(re.search(r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", result).group(0))
        except subprocess.CalledProcessError:
            STARTING_ANGLE = 0

        try:
            command = f'grep -e "degrees/frame" {info_txt}'
            result = subprocess.check_output(shlex.split(command)).decode('utf-8').strip().split('\n')[0]
            OSCILLATION_RANGE = float(re.search(r'\d+\.\d+', result).group(0))
        except subprocess.CalledProcessError:
            OSCILLATION_RANGE = 0

        command = f'grep -e "wavelength" {info_txt}'
        result = subprocess.check_output(shlex.split(command)).decode('utf-8').strip().split('\n')[0]
        WAVELENGTH = float(re.search(r'\d+\.\d+', result).group(0))

        template_data = {
            "DETECTOR_DISTANCE": DETECTOR_DISTANCE,
            "ORGX": ORGX,
            "ORGY": ORGY,
            "NFRAMES": NFRAMES,
            "NAME_TEMPLATE_OF_DATA_FRAMES": NAME_TEMPLATE_OF_DATA_FRAMES,
            "STARTING_ANGLE": STARTING_ANGLE,
            "OSCILLATION_RANGE": OSCILLATION_RANGE,
            "WAVELENGTH": WAVELENGTH
        }

        with open('XDS.INP', 'w') as monitor_file, open('template.INP', 'r') as f:
            src = Template(f.read())
            result = src.substitute(template_data)
            monitor_file.write(result)

        os.remove('template.INP')
        xds_start(current_data_processing_folder, command_for_data_processing)


# --- MAIN ---
folder_with_raw_data = sys.argv[1]
current_data_processing_folder = sys.argv[2]
ORGX = sys.argv[3] if sys.argv[3] != "None" else 0
ORGX = (-1) * float(ORGX)  # Convert to negative as per

ORGY = sys.argv[4] if sys.argv[4] != "None" else 0
ORGY = (-1) * float(ORGY)  # Convert to negative as per

DISTANCE_OFFSET = float(sys.argv[5])
command_for_data_processing = sys.argv[6]
XDS_INP_template = sys.argv[7]

res = [
    os.path.join(folder_with_raw_data, file)
    for file in os.listdir(folder_with_raw_data)
    if os.path.isfile(os.path.join(folder_with_raw_data, file)) and (
        (file.endswith(".h5") or file.endswith(".cxi")) and 'master' in file or file.endswith(".cbf"))
]
res.sort()

if res:
    NAME_TEMPLATE_OF_DATA_FRAMES = res[0]
    if 'master' in NAME_TEMPLATE_OF_DATA_FRAMES:
        NAME_TEMPLATE_OF_DATA_FRAMES = re.sub(r'_master\.', '_??????.', NAME_TEMPLATE_OF_DATA_FRAMES)
    else:
        NAME_TEMPLATE_OF_DATA_FRAMES = re.sub(r'\d+\.', lambda m: '?' * (len(m.group()) - 1) + '.', NAME_TEMPLATE_OF_DATA_FRAMES)

    filling_template(folder_with_raw_data, current_data_processing_folder, ORGX, ORGY,
                    DISTANCE_OFFSET, NAME_TEMPLATE_OF_DATA_FRAMES, command_for_data_processing)

    # Create flag file
    flag_file = os.path.join(current_data_processing_folder, 'flag.txt')
    try:
        open(flag_file, 'a').close()
    except OSError:
        pass
