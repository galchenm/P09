#!/usr/bin/env python3
# coding: utf8
# Written by Galchenkova M., Tolstikova A., Yefanov O., 2022

import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from string import Template

os.nice(0)


def geometry_fill_template_for_serial(current_data_processing_folder):
    global information

    os.chdir(current_data_processing_folder)

    geometry_filename_template = information["crystallography"]["geometry_for_processing"]
    shutil.copy(geometry_filename_template, os.path.join(current_data_processing_folder, 'template.geom'))

    DETECTOR_DISTANCE = (
        information['crystallography']['DETECTOR_DISTANCE']
        + information['crystallography']['DISTANCE_OFFSET']
    )

    ORGX = -1 * information['crystallography']['ORGX']
    ORGY = -1 * information['crystallography']['ORGY']
    PHOTON_ENERGY = information['crystallography']['energy']
    data_h5path = information['crystallography']['data_h5path']

    template_data = {
        "DETECTOR_DISTANCE": DETECTOR_DISTANCE,
        "ORGX": ORGX,
        "ORGY": ORGY,
        "PHOTON_ENERGY": PHOTON_ENERGY,
        "data_h5path": data_h5path
    }

    geometry_filename = 'geometry.geom'
    with open(os.path.join(current_data_processing_folder, 'template.geom'), 'r') as f:
        src = Template(f.read())
    with open(geometry_filename, 'w') as monitor_file:
        result = src.substitute(template_data)
        monitor_file.write(result)

    os.remove(os.path.join(current_data_processing_folder, 'template.geom'))


def serial_data_processing(folder_with_raw_data, current_data_processing_folder,
                           command_for_data_processing, cell_file):

    job_name = current_data_processing_folder.split("/")[-1]
    job_file = os.path.join(current_data_processing_folder, f"{job_name}_serial.sh")
    err_file = os.path.join(current_data_processing_folder, f"{job_name}_serial.err")
    out_file = os.path.join(current_data_processing_folder, f"{job_name}_serial.out")

    with open(job_file, 'w+') as fh:
        fh.writelines([
            "#!/bin/sh\n",
            f"#SBATCH --job={job_file}\n",
            "#SBATCH --partition=allcpu\n",
            "#SBATCH --time=12:00:00\n",
            "#SBATCH --nodes=1\n",
            "#SBATCH --nice=100\n",
            "#SBATCH --mem=500000\n",
            f"#SBATCH --output={out_file}\n",
            f"#SBATCH --error={err_file}\n",
            "source /etc/profile.d/modules.sh\n",
            "module load xray maxwell crystfel\n",
            f"{command_for_data_processing} {folder_with_raw_data} {current_data_processing_folder} {cell_file}\n"
        ])

    os.system(f"sbatch {job_file}")


def filling_template(folder_with_raw_data, current_data_processing_folder, geometry_filename_template, data_h5path,\
                    ORGX=0, ORGY=0, DISTANCE_OFFSET=0, command_for_data_processing='turbo-index-P09', cell_file=None):
    os.chdir(current_data_processing_folder)
    shutil.copy(geometry_filename_template, os.path.join(current_data_processing_folder, 'template.geom'))

    info_txt = ''
    info_path = os.path.join(folder_with_raw_data, 'info.txt')
    if os.path.exists(info_path) and os.stat(info_path).st_size != 0:
        info_txt = info_path

        result = subprocess.check_output(shlex.split(f'grep -e "distance" {info_txt}')).decode('utf-8').strip().split('\n')[0]
        DETECTOR_DISTANCE = (float(re.search(r'\d+\.\d+', result).group(0)) + DISTANCE_OFFSET) / 1000
        if ORGX == 0:
            result = subprocess.check_output(shlex.split(f'grep -e "ORGX" {info_txt}')).decode('utf-8').strip().split('\n')[0]
            ORGX = float(re.search(r'\d+\.\d+', result).group(0))
        if ORGY == 0:
            result = subprocess.check_output(shlex.split(f'grep -e "ORGY" {info_txt}')).decode('utf-8').strip().split('\n')[0]
            ORGY = float(re.search(r'\d+\.\d+', result).group(0))
        result = subprocess.check_output(shlex.split(f'grep -e "wavelength" {info_txt}')).decode('utf-8').strip().split('\n')[0]
        WAVELENGTH = float(re.search(r'\d+\.\d+', result).group(0))
        PHOTON_ENERGY = 12400 / WAVELENGTH
        if cell_file == "None":
            result = subprocess.check_output(shlex.split(f'grep -e "wavelength" {info_txt}')).decode('utf-8').strip().split('\n')[0]
            cell_file = re.search(r'cell_file:\s*(\S+)', result).group(1)
        template_data = {
            "DETECTOR_DISTANCE": DETECTOR_DISTANCE,
            "ORGX": ORGX,
            "ORGY": ORGY,
            "PHOTON_ENERGY": PHOTON_ENERGY,
            "data_h5path": data_h5path
        }

        with open(os.path.join(current_data_processing_folder, 'template.geom'), 'r') as f:
            src = Template(f.read())
        with open('geometry.geom', 'w') as monitor_file:
            result = src.substitute(template_data)
            monitor_file.write(result)

        os.remove(os.path.join(current_data_processing_folder, 'template.geom'))

        serial_data_processing(folder_with_raw_data, current_data_processing_folder,
                            command_for_data_processing, cell_file)


# CLI Argument Handling
folder_with_raw_data = sys.argv[1]
current_data_processing_folder = sys.argv[2]

ORGX = sys.argv[3] if sys.argv[3] != "None" else 0
ORGX = (-1) * float(ORGX)  # Convert to negative as per

ORGY = sys.argv[4] if sys.argv[4] != "None" else 0
ORGY = (-1) * float(ORGY)  # Convert to negative as per

DISTANCE_OFFSET = float(sys.argv[5])
command_for_data_processing = sys.argv[6]
geometry_filename_template = sys.argv[7]            
cell_file = sys.argv[8] 
data_h5path = sys.argv[9] 

if cell_file == "None":
    cell_file = ""

filling_template(
                        folder_with_raw_data, current_data_processing_folder, geometry_filename_template, data_h5path,\
                        ORGX, ORGY, DISTANCE_OFFSET, command_for_data_processing, cell_file
                    )
# Create flag file
flag_file = os.path.join(current_data_processing_folder, 'flag.txt')
try:
    open(flag_file, 'a').close()
except OSError:
    pass
