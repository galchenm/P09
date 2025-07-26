#!/usr/bin/env python3
# coding: utf8
# Written by Galchenkova M., Tolstikova A., Yefanov O., 2022

import os
import re
import glob
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from string import Template
from utils.nodes import are_the_reserved_nodes_overloaded
from utils.templates import filling_template_serial

split_lines = 250

def serial_data_processing(folder_with_raw_data, current_data_processing_folder,
                            cell_file, indexing_method, USER, RESERVED_NODE, SLURM_PARTITION, sshPrivateKeyPath, sshPublicKeyPath):
    """Prepare and submit the serial data processing job."""
    job_name = Path(current_data_processing_folder).name

    raw = folder_with_raw_data
    proc = current_data_processing_folder
    pdb = cell_file if cell_file else ""
    
    geom = "geometry.geom"
    
    os.chdir(proc)
    os.chmod(proc, 0o777)
    
    # Create directories
    stream_dir = Path("streams")
    error_dir = Path("error")
    joined_stream_dir = Path("j_stream")
    for d in [stream_dir, error_dir, joined_stream_dir]:
        d.mkdir(exist_ok=True)

    name1 = Path(proc).name
    
    # Load modules
    subprocess.run("source /etc/profile.d/modules.sh && module load maxwell xray crystfel", shell=True, executable='/bin/bash')

    # Find files
    list_h5 = "list_h5.lst"
    list_cbf = "list_cbf.lst"
    with open(list_h5, "w") as f:
        subprocess.run(f"find {raw} -name '*.h5' | sort", shell=True, stdout=f)
    with open(list_cbf, "w") as f:
        subprocess.run(f"find {raw} -name '*.cbf' | sort", shell=True, stdout=f)

    # Determine filetype
    filetype = 0
    if os.path.getsize(list_h5) > 0:
        print("Found h5 files")
        filetype = 1

    if os.path.getsize(list_cbf) > 0:
        print("Found cbf files")
        filetype = 2

    if filetype == 0:
        print("No .h5 or .cbf files found in the raw folder. Exiting.")
        sys.exit(0)

    # Convert list if necessary
    if filetype == 1:
        subprocess.run(f"list_events -i {list_h5} -g {geom} -o {list_cbf}", shell=True)

    # Split input file
    split_prefix = f"events-{name1}.lst"
    subprocess.run(f"split -a 3 -d -l {split_lines} {list_cbf} {split_prefix}", shell=True)
    
    # Create and submit SLURM jobs
    for split_file in sorted(Path(".").glob(f"{split_prefix}*")):
        suffix = split_file.name.replace(f"events-{name1}.lst", "")
        name = f"{name1}{suffix}"
        stream = f"{name1}.stream{suffix}"
        slurmfile = f"{name}.sh"
        err_file = Path(current_data_processing_folder) / f"{error_dir}/{name}_serial.err"
        out_file = Path(current_data_processing_folder) / f"{error_dir}/{name}_serial.out"
    
        print(f"Processing {split_file.name} -> {stream}")
        with open(slurmfile, "w") as f:
            sbatch_command = "#!/bin/sh\n"
            sbatch_command += f"#SBATCH --job-name={name}\n"
            sbatch_command += f"#SBATCH --output={out_file}\n"
            sbatch_command += f"#SBATCH --error={err_file}\n"
            if "maxwell" not in RESERVED_NODE:
                login_node = RESERVED_NODE.split(",")[0] if "," in RESERVED_NODE else RESERVED_NODE
                reserved_nodes_overloaded = are_the_reserved_nodes_overloaded(RESERVED_NODE)
        
                ssh_command = (
                    f"/usr/bin/ssh -o BatchMode=yes -o CheckHostIP=no -o StrictHostKeyChecking=no "
                    f"-o GSSAPIAuthentication=no -o GSSAPIDelegateCredentials=no "
                    f"-o PasswordAuthentication=no -o PubkeyAuthentication=yes "
                    f"-o PreferredAuthentications=publickey -o ConnectTimeout=10 "
                    f"-l {USER} -i {sshPrivateKeyPath} {login_node}"
                )
                if not reserved_nodes_overloaded:
                    sbatch_command += f"#SBATCH --partition={SLURM_PARTITION}\n"
                    sbatch_command += f"#SBATCH --reservation={RESERVED_NODE}\n"
                else:
                    sbatch_command += f"#SBATCH --partition=allcpu,upex,short\n"
            else:
                ssh_command = ""
                sbatch_command += "#SBATCH --partition=allcpu,upex,short\n"
                sbatch_command += "#SBATCH --time=4:00:00\n"
                sbatch_command += "#SBATCH --nodes=1\n"
                sbatch_command += "#SBATCH --nice=100\n"
                sbatch_command += "#SBATCH --mem=500000\n"
            
            sbatch_command += "module load maxwell xray crystfel\n"

            indexing_command = f"indexamajig -i {split_file.name} -o {stream_dir}/{stream} -j 80 -g {geom} --int-radius=3,6,8"
            indexing_command += " --peaks=peakfinder8 --min-snr=8 --min-res=10 --max-res=1200 --threshold=5"
            indexing_command += " --min-pix-count=1 --max-pix-count=10 --min-peaks=15 --local-bg-radius=3"
            indexing_command += f" --indexing={indexing_method} --no-check-cell --multi"
            if pdb:
                indexing_command += f" -p {pdb}"

            f.write(sbatch_command + "\n" + indexing_command + "\n")
            f.write(f"touch {name}.done\n")
        os.chmod(slurmfile, 0o755)
        # Submit the job  
        if ssh_command:
            subprocess.run(f'{ssh_command} "sbatch {slurmfile}"', shell=True, check=True)
        else:
            subprocess.run(f'sbatch {slurmfile}', shell=True, check=True)


def serial_processing(
        folder_with_raw_data,
        current_data_processing_folder,
        ORGX,
        ORGY,
        DISTANCE_OFFSET,
        geometry_filename_template,
        cell_file,
        data_h5path,
        USER,
        RESERVED_NODE,
        SLURM_PARTITION,
        sshPrivateKeyPath,
        sshPublicKeyPath
    ):
    """Main function to handle command line arguments and initiate data processing."""

    ORGX = float(ORGX) if ORGX != "None" else 0
    ORGY = float(ORGY) if ORGY != "None" else 0
    DISTANCE_OFFSET = float(DISTANCE_OFFSET)
    if cell_file == "None":
        cell_file = None

    indexing_method, cell_file = filling_template_serial(
        folder_with_raw_data,
        current_data_processing_folder,
        geometry_filename_template,
        data_h5path,
        ORGX,
        ORGY,
        DISTANCE_OFFSET,
        cell_file
    )
    
    serial_data_processing(
        folder_with_raw_data, current_data_processing_folder,
        cell_file, indexing_method, USER, RESERVED_NODE, SLURM_PARTITION, sshPrivateKeyPath, sshPublicKeyPath
    )
    
    # Create flag file
    flag_file = Path(current_data_processing_folder) / 'flag.txt'
    flag_file.touch(exist_ok=True)

