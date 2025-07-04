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


def serial_data_processing(folder_with_raw_data, current_data_processing_folder,
                            command_for_data_processing, cell_file,
                            USER, RESERVED_NODE, SLURM_PARTITION, sshPrivateKeyPath, sshPublicKeyPath):

    job_name = Path(current_data_processing_folder).name
    job_file = Path(current_data_processing_folder) / f"{job_name}_serial.sh"
    err_file = Path(current_data_processing_folder) / f"{job_name}_serial.err"
    out_file = Path(current_data_processing_folder) / f"{job_name}_serial.out"

    if "maxwell" not in RESERVED_NODE:
        login_line = f"ssh -l {USER} -i {sshPrivateKeyPath} {RESERVED_NODE}"
        sbatch_file = [
            "#!/bin/sh\n",
            login_line + "\n",
            f"#SBATCH --job-name={job_name}\n",
            f"#SBATCH --partition={SLURM_PARTITION}\n",
            f"#SBATCH --reservation={RESERVED_NODE}\n",
            "#SBATCH --nodes=1\n",
            f"#SBATCH --output={out_file}\n",
            f"#SBATCH --error={err_file}\n",
            "source /etc/profile.d/modules.sh\n",
            "module load maxwell xray crystfel\n",
            f"{command_for_data_processing} {folder_with_raw_data} {current_data_processing_folder} {cell_file}\n"
        ]
    else:
        sbatch_file = [
            "#!/bin/sh\n",
            f"#SBATCH --job-name={job_name}\n",
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
        ]

    with open(job_file, 'w') as fh:
        fh.writelines(sbatch_file)

    os.chmod(job_file, 0o755)

    if shutil.which("sbatch"):
        os.system(f"sbatch {job_file}")
    else:
        print("Error: sbatch command not found. Job not submitted.")

import re

def extract_value_from_info(info_path, key, fallback=None, is_float=True, is_string=False):
    if fallback is None:
        fallback = "" if is_string else 0

    try:
        with open(info_path) as f:
            lines = f.readlines()
        for line in lines:
            if key in line:
                if is_string:
                    # Get value after the first colon, trim whitespace
                    return line.split(":", 1)[-1].strip()
                else:
                    match = re.search(r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", line)
                    if match:
                        return float(match.group()) if is_float else int(float(match.group()))
    except Exception:
        pass

    return fallback



def filling_template(folder_with_raw_data, current_data_processing_folder,
                    geometry_filename_template, data_h5path,
                    ORGX=0, ORGY=0, DISTANCE_OFFSET=0,
                    command_for_data_processing='turbo-index-P09', cell_file=None,
                    USER=None, RESERVED_NODE=None, SLURM_PARTITION=None, sshPrivateKeyPath=None, sshPublicKeyPath=None):
    """Fills the geometry template with parameters extracted from info.txt and prepares for data processing."""
    
    os.chdir(current_data_processing_folder)
    template_geom_path = Path(current_data_processing_folder) / 'template.geom'
    shutil.copy(geometry_filename_template, template_geom_path)

    info_path = Path(folder_with_raw_data) / 'info.txt'
    if not info_path.exists() or info_path.stat().st_size == 0:
        print(f"No valid info.txt found in {folder_with_raw_data}")
        return

    with open(info_path) as f:
        content = f.read()

    DETECTOR_DISTANCE = extract_value_from_info(info_path, "distance") + DISTANCE_OFFSET
    ORGX = ORGX or extract_value_from_info(info_path, "ORGX")
    ORGY = ORGY or extract_value_from_info(info_path, "ORGY")
    NFRAMES = extract_value_from_info(info_path, "frames", fallback=1, is_float=False)
    STARTING_ANGLE = extract_value_from_info(info_path, "start angle")
    OSCILLATION_RANGE = extract_value_from_info(info_path, "degrees/frame")
    WAVELENGTH = extract_value_from_info(info_path, "wavelength")
    PHOTON_ENERGY = 12400 / WAVELENGTH
    
    cell_file = cell_file or extract_value_from_info(info_path, "cell_file", fallback="", is_string=True)

    template_data = {
        "DETECTOR_DISTANCE": DETECTOR_DISTANCE,
        "ORGX": -ORGX,
        "ORGY": -ORGY,
        "PHOTON_ENERGY": PHOTON_ENERGY,
        "data_h5path": data_h5path
    }

    with open(template_geom_path, 'r') as f:
        src = Template(f.read())

    with open('geometry.geom', 'w') as monitor_file:
        monitor_file.write(src.substitute(template_data))

    template_geom_path.unlink()

    serial_data_processing(
        folder_with_raw_data, current_data_processing_folder,
        command_for_data_processing, cell_file,
        USER, RESERVED_NODE, SLURM_PARTITION, sshPrivateKeyPath, sshPublicKeyPath
    )


def main():
    """Main function to handle command line arguments and initiate data processing."""
    # CLI Argument Handling
    print("sys.argv=", sys.argv)
    args = sys.argv[1:]
    
    if len(args) != 14:
        print(f"Expected 14 arguments, got {len(args)}")
        sys.exit(1)

    (
        folder_with_raw_data,
        current_data_processing_folder,
        ORGX,
        ORGY,
        DISTANCE_OFFSET,
        command_for_data_processing,
        geometry_filename_template,
        cell_file,
        data_h5path,
        USER,
        RESERVED_NODE,
        SLURM_PARTITION,
        sshPrivateKeyPath,
        sshPublicKeyPath
    ) = args[:]

    ORGX = float(ORGX) if ORGX != "None" else 0
    ORGY = float(ORGY) if ORGY != "None" else 0
    DISTANCE_OFFSET = float(DISTANCE_OFFSET)
    if cell_file == "None":
        cell_file = None

    filling_template(
        folder_with_raw_data,
        current_data_processing_folder,
        geometry_filename_template,
        data_h5path,
        ORGX,
        ORGY,
        DISTANCE_OFFSET,
        command_for_data_processing,
        cell_file,
        USER,
        RESERVED_NODE,
        SLURM_PARTITION,
        sshPrivateKeyPath,
        sshPublicKeyPath
    )

    # Create flag file
    flag_file = Path(current_data_processing_folder) / 'flag.txt'
    flag_file.touch(exist_ok=True)


if __name__ == '__main__':
    main()
