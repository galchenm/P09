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

os.nice(0)

split_lines = 250

def serial_data_processing(folder_with_raw_data, current_data_processing_folder,
                            cell_file, indexing_method, USER, RESERVED_NODE, SLURM_PARTITION, sshPrivateKeyPath, sshPublicKeyPath):

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
        err_file = Path(current_data_processing_folder) / f"{name}_serial.err"
        out_file = Path(current_data_processing_folder) / f"{name}_serial.out"
    
        print(f"Processing {split_file.name} -> {stream}")
        with open(slurmfile, "w") as f:
            sbatch_command = "#!/bin/sh\n"
            sbatch_command += f"#SBATCH --job-name={name}\n"
            sbatch_command += f"#SBATCH --output={out_file}\n"
            sbatch_command += f"#SBATCH --error={err_file}\n"
            if "maxwell" not in RESERVED_NODE:
                ssh_command = (
                    f"/usr/bin/ssh -o BatchMode=yes -o CheckHostIP=no -o StrictHostKeyChecking=no "
                    f"-o GSSAPIAuthentication=no -o GSSAPIDelegateCredentials=no "
                    f"-o PasswordAuthentication=no -o PubkeyAuthentication=yes "
                    f"-o PreferredAuthentications=publickey -o ConnectTimeout=10 "
                    f"-l {USER} -i {sshPrivateKeyPath} {RESERVED_NODE}"
                )
                sbatch_command += f"#SBATCH --partition={SLURM_PARTITION}\n"
                sbatch_command += f"#SBATCH --reservation={RESERVED_NODE}\n"
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
                    cell_file=None, USER=None, RESERVED_NODE=None, SLURM_PARTITION=None, sshPrivateKeyPath=None, sshPublicKeyPath=None):
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
    
    if not cell_file:
        # Try to find a .cell or .pdb file in the raw data folder
        cell_matches = glob.glob(str(Path(folder_with_raw_data) / "*.cell"))
        if cell_matches:
            cell_file = cell_matches[0]
        else:
            pdb_matches = glob.glob(str(Path(folder_with_raw_data) / "*.pdb"))
            if pdb_matches:
                cell_file = pdb_matches[0]

    indexing_method = extract_value_from_info(info_path, "indexing_method", fallback="mosflm-latt-nocell", is_string=True)
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
        cell_file, indexing_method, USER, RESERVED_NODE, SLURM_PARTITION, sshPrivateKeyPath, sshPublicKeyPath
    )


def main():
    """Main function to handle command line arguments and initiate data processing."""
    # CLI Argument Handling
    
    args = sys.argv[1:]
    
    if len(args) != 13:
        print(f"Expected 13 arguments, got {len(args)}")
        sys.exit(1)

    (
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
