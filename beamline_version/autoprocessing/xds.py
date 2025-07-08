#!/usr/bin/env python3
# coding: utf8
# Written by Galchenkova M., Tolstikova A., Yefanov O., 2022 (revised)

import os
import sys
import glob
import re
import shutil
import subprocess
from string import Template
from pathlib import Path

os.nice(0)

def xds_start(current_data_processing_folder, command_for_data_processing,
                USER, RESERVED_NODE, SLURM_PARTITION, sshPrivateKeyPath, sshPublicKeyPath):

    job_name = Path(current_data_processing_folder).name
    slurmfile = Path(current_data_processing_folder) / f"{job_name}_XDS.sh"
    err_file = Path(current_data_processing_folder) / f"{job_name}_XDS.err"
    out_file = Path(current_data_processing_folder) / f"{job_name}_XDS.out"

    if "maxwell" not in RESERVED_NODE:
        ssh_command = f"/usr/bin/ssh -o BatchMode=yes -o CheckHostIP=no -o StrictHostKeyChecking=no -o GSSAPIAuthentication=no -o GSSAPIDelegateCredentials=no -o PasswordAuthentication=no -o PubkeyAuthentication=yes -o PreferredAuthentications=publickey -o ConnectTimeout=10 -l {USER} -i {sshPrivateKeyPath} {RESERVED_NODE}"
        sbatch_file = [
            "#!/bin/sh\n",
            f"#SBATCH --job-name={job_name}\n",
            f"#SBATCH --partition={SLURM_PARTITION}\n",
            f"#SBATCH --reservation={RESERVED_NODE}\n",
            "#SBATCH --nodes=1\n",
            f"#SBATCH --output={out_file}\n",
            f"#SBATCH --error={err_file}\n",
            "source /etc/profile.d/modules.sh\n",
            "module load xray\n",
            f"{command_for_data_processing}\n"
        ]
    else:
        ssh_command = ""
        sbatch_file = [
            "#!/bin/sh\n",
            f"#SBATCH --job-name={job_name}\n",
            "#SBATCH --partition=allcpu,upex\n",
            "#SBATCH --time=12:00:00\n",
            "#SBATCH --nodes=1\n",
            "#SBATCH --nice=100\n",
            "#SBATCH --mem=500000\n",
            f"#SBATCH --output={out_file}\n",
            f"#SBATCH --error={err_file}\n",
            "source /etc/profile.d/modules.sh\n",
            "module load xray\n",
            f"{command_for_data_processing}\n"
        ]

    with open(slurmfile, 'w') as fh:
        fh.writelines(sbatch_file)

    os.chmod(slurmfile, 0o755)
    # Submit the job  
    if ssh_command:
        subprocess.run(f'{ssh_command} "sbatch {slurmfile}"', shell=True, check=True)
    else:
        subprocess.run(f'sbatch {slurmfile}', shell=True, check=True)

def extract_value_from_info(info_path, key, fallback=0, is_float=True):
    try:
        with open(info_path) as f:
            lines = f.readlines()
        for line in lines:
            if key in line:
                match = re.search(r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", line)
                if match:
                    return float(match.group()) if is_float else int(float(match.group()))
    except Exception:
        pass
    return fallback


def filling_template(folder_with_raw_data, current_data_processing_folder, ORGX=0, ORGY=0,
                    DISTANCE_OFFSET=0, NAME_TEMPLATE_OF_DATA_FRAMES='blabla',
                    command_for_data_processing='xds_par', XDS_INP_template=None,
                    USER=None, RESERVED_NODE=None, sshPrivateKeyPath=None, sshPublicKeyPath=None):

    folder_with_raw_data = Path(folder_with_raw_data)
    current_data_processing_folder = Path(current_data_processing_folder)

    shutil.copy(XDS_INP_template, current_data_processing_folder / 'template.INP')

    info_path = folder_with_raw_data / 'info.txt'
    if not info_path.exists() or info_path.stat().st_size == 0:
        print(f"Error: info.txt not found or empty in {folder_with_raw_data}")
        return

    DETECTOR_DISTANCE = extract_value_from_info(info_path, "distance") + DISTANCE_OFFSET
    ORGX = ORGX or extract_value_from_info(info_path, "ORGX")
    ORGY = ORGY or extract_value_from_info(info_path, "ORGY")
    NFRAMES = extract_value_from_info(info_path, "frames", fallback=1, is_float=False)
    STARTING_ANGLE = extract_value_from_info(info_path, "start angle")
    OSCILLATION_RANGE = extract_value_from_info(info_path, "degrees/frame")
    WAVELENGTH = extract_value_from_info(info_path, "wavelength")

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

    with open(current_data_processing_folder / 'template.INP', 'r') as f:
        src = Template(f.read())
    with open(current_data_processing_folder / 'XDS.INP', 'w') as f:
        f.write(src.substitute(template_data))

    os.remove(current_data_processing_folder / 'template.INP')

    xds_start(current_data_processing_folder, command_for_data_processing,
            USER, RESERVED_NODE, SLURM_PARTITION, sshPrivateKeyPath, sshPublicKeyPath)

def main():
    folder_with_raw_data = sys.argv[1]
    current_data_processing_folder = sys.argv[2]
    ORGX = float(sys.argv[3]) if sys.argv[3] != "None" else 0
    ORGY = float(sys.argv[4]) if sys.argv[4] != "None" else 0
    DISTANCE_OFFSET = float(sys.argv[5])
    command_for_data_processing = sys.argv[6]
    XDS_INP_template = sys.argv[7]
    USER, RESERVED_NODE, SLURM_PARTITION, sshPrivateKeyPath, sshPublicKeyPath = sys.argv[8:13]

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
                        DISTANCE_OFFSET, NAME_TEMPLATE_OF_DATA_FRAMES, command_for_data_processing,
                        XDS_INP_template, USER, RESERVED_NODE, sshPrivateKeyPath, sshPublicKeyPath)

        Path(current_data_processing_folder, 'flag.txt').touch()

if __name__ == "__main__":
    main()