#!/usr/bin/env python3
# coding: utf8
# Written by Galchenkova M., Tolstikova A., Yefanov O., 2022 (revised)

import os
import sys
import time
import math
import fabio
import gemmi
import glob
import re
import shutil
import subprocess
from string import Template
from pathlib import Path
from collections import defaultdict

os.nice(0)

SLEEP_TIME = 10
LIMIT_FOR_RESERVED_NODES = 25
def are_the_reserved_nodes_overloaded(node_list):
    """Check if the reserved nodes are overloaded by counting running jobs.
    Args:
        node_list (str): Comma-separated list of reserved nodes.
    Returns:
        bool: True if the number of jobs exceeds the limit, False otherwise.
    """
    try:
        jobs_cmd = f'squeue -w {node_list}'
        all_jobs = subprocess.check_output(shlex.split(jobs_cmd)).decode().splitlines()
    except subprocess.CalledProcessError:
        all_jobs = []
    return len(all_jobs) > LIMIT_FOR_RESERVED_NODES

def xds_start(current_data_processing_folder, command_for_data_processing,
                USER, RESERVED_NODE, SLURM_PARTITION, sshPrivateKeyPath, sshPublicKeyPath):
    """Prepare and submit the XDS job."""
    job_name = Path(current_data_processing_folder).name
    slurmfile = Path(current_data_processing_folder) / f"{job_name}_XDS.sh"
    err_file = Path(current_data_processing_folder) / f"{job_name}_XDS.err"
    out_file = Path(current_data_processing_folder) / f"{job_name}_XDS.out"

    if "maxwell" not in RESERVED_NODE:
        login_node = RESERVED_NODE.split(",")[0] if "," in RESERVED_NODE else RESERVED_NODE
        ssh_command = f"/usr/bin/ssh -o BatchMode=yes -o CheckHostIP=no -o StrictHostKeyChecking=no -o GSSAPIAuthentication=no -o GSSAPIDelegateCredentials=no -o PasswordAuthentication=no -o PubkeyAuthentication=yes -o PreferredAuthentications=publickey -o ConnectTimeout=10 -l {USER} -i {sshPrivateKeyPath} {login_node}"
        
        reserved_nodes_overloaded = are_the_reserved_nodes_overloaded(RESERVED_NODE)
        if not reserved_nodes_overloaded:
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
                f"{command_for_data_processing}\n",
                f"sleep {SLEEP_TIME}\n",
                f"cd {current_data_processing_folder}\n",
                "cp GXPARM.XDS XPARM.XDS\n",
                "cp XDS_ASCII.HKL XDS_ASCII.HKL_1\n",
                "mv CORRECT.LP CORRECT.LP_1\n",
                "sed -i 's/ JOB= XYCORR INIT/!JOB= XYCORR INIT/g' XDS.INP\n",
                "sed -i 's/!JOB= CORRECT/ JOB= DEFPIX INTEGRATE CORRECT/g' XDS.INP\n",
                f"{command_for_data_processing}\n"
            ]
        else:
            sbatch_file = [
                "#!/bin/sh\n",
                f"#SBATCH --job-name={job_name}\n",
                f"#SBATCH --partition=allcpu,upex,short\n",
                "#SBATCH --nodes=1\n",
                f"#SBATCH --output={out_file}\n",
                f"#SBATCH --error={err_file}\n",
                "source /etc/profile.d/modules.sh\n",
                "module load xray\n",
                f"{command_for_data_processing}\n",
                f"sleep {SLEEP_TIME}\n",
                f"cd {current_data_processing_folder}\n",
                "cp GXPARM.XDS XPARM.XDS\n",
                "cp XDS_ASCII.HKL XDS_ASCII.HKL_1\n",
                "mv CORRECT.LP CORRECT.LP_1\n",
                "sed -i 's/ JOB= XYCORR INIT/!JOB= XYCORR INIT/g' XDS.INP\n",
                "sed -i 's/!JOB= CORRECT/ JOB= DEFPIX INTEGRATE CORRECT/g' XDS.INP\n",
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
            f"{command_for_data_processing}\n",
            f"sleep {SLEEP_TIME}\n",
            f"cd {current_data_processing_folder}\n",
            "cp GXPARM.XDS XPARM.XDS\n",
            "cp XDS_ASCII.HKL XDS_ASCII.HKL_1\n",
            "mv CORRECT.LP CORRECT.LP_1\n",
            "sed -i 's/ JOB= XYCORR INIT/!JOB= XYCORR INIT/g' XDS.INP\n",
            "sed -i 's/!JOB= CORRECT/ JOB= DEFPIX INTEGRATE CORRECT/g' XDS.INP\n",
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

def parse_cryst1_and_spacegroup_number(file_path):
    """Parse the CRYST1 line from a PDB file to extract unit cell parameters and space group number.
    Args:
        file_path (str): Path to the PDB file.
    Returns:
        tuple: A tuple containing the unit cell parameters (a, b, c, alpha, beta, gamma) and space group number.
    Raises:
        ValueError: If the CRYST1 line is not found or does not contain valid data.
    """
    pattern = (
        r"CRYST1\s+"
        r"([\d.]+)\s+"     # a
        r"([\d.]+)\s+"     # b
        r"([\d.]+)\s+"     # c
        r"([\d.]+)\s+"     # alpha
        r"([\d.]+)\s+"     # beta
        r"([\d.]+)\s+"     # gamma
        r"(.{1,11})\s+\d+" # space group + Z
    )

    with open(file_path, 'r') as file:
        for line in file:
            if line.startswith("CRYST1"):
                match = re.match(pattern, line.strip())
                if match:
                    a = float(match.group(1))
                    b = float(match.group(2))
                    c = float(match.group(3))
                    alpha = float(match.group(4))
                    beta = float(match.group(5))
                    gamma = float(match.group(6))
                    space_group = match.group(7).strip()
                    sg_number = gemmi.SpaceGroup(space_group).number
                    return a, b, c, alpha, beta, gamma, sg_number

    raise ValueError("No CRYST1 line found in the provided PDB file.")

def parse_UC_file(UC_file):
    """Parse a unit cell file to extract unit cell parameters.
    This function checks the file extension and calls the appropriate parsing function. 
    If the file is a PDB file, it uses the parse_cryst1_from_pdb function.
    If the file is not a PDB file, it uses a regular expression to extract the unit cell parameters.
    Args:
        UC_file (str): The path to the unit cell file.
    Returns:
        tuple: A tuple containing the unit cell parameters (a, b, c, alpha, beta, gamma).
    Raises:
        ValueError: If the unit cell parameters are not found in the file.
    """
    if UC_file.endswith('pdb'):
        return parse_cryst1_and_spacegroup_number(UC_file)
    else:
        # Regular expressions to capture the unit cell parameters
        pattern = r"a = ([\d.]+) A.*?b = ([\d.]+) A.*?c = ([\d.]+) A.*?al = ([\d.]+) deg.*?be = ([\d.]+) deg.*?ga = ([\d.]+) deg"
        
        # Read the content of the file
        with open(UC_file, 'r') as file:
            file_content = file.read()

        # Search for the pattern in the file content
        match = re.search(pattern, file_content, re.DOTALL)

        if match:
            # Extract values from the match
            a = float(match.group(1))
            b = float(match.group(2))
            c = float(match.group(3))
            al = float(match.group(4))
            be = float(match.group(5))
            ga = float(match.group(6))
            return a, b, c, al, be, ga, "0"  # Default space group number
        else:
            raise ValueError("Unit cell parameters not found in the provided file.")
            return None, None, None, None, None, None, None

def extract_value_from_info(info_path, key, fallback=None, is_float=True, is_string=False):
    """Extract a value from the info.txt file based on the provided key.
    Args:
        info_path (str): Path to the info.txt file.
        key (str): The key to search for in the file.
        fallback: The value to return if the key is not found. Defaults to 0 for numeric values and an empty string for string values.
        is_float (bool): If True, the extracted value will be converted to float. Defaults
            to True.
        is_string (bool): If True, the extracted value will be treated as a string.
    Returns:
        The extracted value if found, otherwise the fallback value.
    """
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

def calculation_high_resolution(detector_distance, wavelength, N_pixels_to_the_short_edge=2462, N_pixels_to_the_long_edge=2526, pixel_size=0.000172):
    """Calculate the high resolution based on the detector distance, wavelength, and pixel dimensions.
    Args:
        detector_distance (float): The distance from the detector to the sample in mm.
        wavelength (float): The wavelength of the X-ray in Angstroms.
        N_pixels_to_the_short_edge (int): Number of pixels in the X direction.
        N_pixels_to_the_long_edge (int): Number of pixels in the Y direction.
    Returns:
        float: The calculated high resolution in Angstroms.
    """
    
    N_pixels_to_the_short_edge /= 2
    N_pixels_to_the_long_edge /= 2

    distance_to_the_short_edge = pixel_size * N_pixels_to_the_short_edge # [m] 
    distance_to_the_long_edge = pixel_size * N_pixels_to_the_long_edge # [m]

    resolution_to_the_short_edge = wavelength / (2* math.sin(0.5 * math.atan(distance_to_the_short_edge/detector_distance)))
    resolution_to_the_long_edge = wavelength / (2* math.sin(0.5 * math.atan(distance_to_the_long_edge/detector_distance)))

    return max(resolution_to_the_short_edge, resolution_to_the_long_edge)

def wait_until_file_is_readable(filepath, timeout=10):
    """Wait until a file is readable.
    Args:
        filepath (str): Path to the file to check.
        timeout (int): Maximum time to wait in seconds.
    """
    start_time = time.time()
    while True:
        try:
            with open(filepath, 'rb'):
                return  # File can be opened for reading
        except Exception as e:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Timeout: File {filepath} still not readable after {timeout} seconds. Error: {e}")
            time.sleep(0.5)  # Wait and retry

def retrieving_info_from_cbf(cbf_file):
    """Retrieve pixel size and dimensions from a CBF file.
    Args:
        cbf_file (str): Path to the CBF file.
    Returns:    
        tuple: A tuple containing the number of pixels in the short edge, long edge, and pixel size.
    Raises:
        TimeoutError: If the file is not readable within the specified timeout.
    """
    wait_until_file_is_readable(cbf_file, timeout=30)
    img = fabio.open(cbf_file)
    header = img.header
    if "X-Binary-Size-Fastest-Dimension" not in header or "X-Binary-Size-Second-Dimension" not in header:
        print(f"Error: Missing X-Binary-Size headers in {cbf_file}")
        N_PIXELS_TO_THE_SHORT_EDGE = 2462  # Default value
        N_PIXELS_TO_THE_LONG_EDGE = 2526   # Default value
        pixel_size = 0.000172  # Default value
    else:
        N_PIXELS_TO_THE_SHORT_EDGE = float(header["X-Binary-Size-Fastest-Dimension"])
        N_PIXELS_TO_THE_LONG_EDGE = float(header["X-Binary-Size-Second-Dimension"])
        lines = header["_array_data.header_contents"].splitlines()
        pixel_line = next((line for line in lines if "Pixel_size" in line), None)
        match = re.search(r"Pixel_size\s+([\deE\.\-]+)\s*m\s*x\s*([\deE\.\-]+)\s*m", pixel_line)
        if match:
            pixel_size = float(match.group(1))
    img.close()    
    return N_PIXELS_TO_THE_SHORT_EDGE, N_PIXELS_TO_THE_LONG_EDGE, pixel_size

def filling_template(folder_with_raw_data, current_data_processing_folder, ORGX=0, ORGY=0, position=None,
                    FIRST=1, LAST=10000, REFERENCE_DATA_SET="!REFERENCE_DATA_SET", DISTANCE_OFFSET=0, 
                    NAME_TEMPLATE_OF_DATA_FRAMES='blabla', command_for_data_processing='xds_par', 
                    XDS_INP_template=None, USER=None, RESERVED_NODE=None, sshPrivateKeyPath=None, 
                    sshPublicKeyPath=None
                    ):
    """Fills the geometry template with parameters extracted from info.txt and prepares for data processing."""
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
    #NFRAMES = extract_value_from_info(info_path, "frames", fallback=1, is_float=False)
    OSCILLATION_RANGE = extract_value_from_info(info_path, "degrees/frame")
    WAVELENGTH = extract_value_from_info(info_path, "wavelength")

    cell_matches = glob.glob(str(Path(folder_with_raw_data) / "*.cell"))
    if cell_matches:
        cell_file = cell_matches[0]
        a, b, c, alpha, beta, gamma, SPACE_GROUP_NUMBER = parse_UC_file(cell_file)
    else:
        pdb_matches = glob.glob(str(Path(folder_with_raw_data) / "*.pdb"))
        if pdb_matches:
            cell_file = pdb_matches[0]
            a, b, c, alpha, beta, gamma, SPACE_GROUP_NUMBER = parse_UC_file(cell_file)

    if REFERENCE_DATA_SET in ["!REFERENCE_DATA_SET", "None"]:
        REFERENCE_DATA_SET_matches = glob.glob(str(Path(folder_with_raw_data) / "XDS_ASCII.HKL"))
        if REFERENCE_DATA_SET_matches:
            REFERENCE_DATA_SET = REFERENCE_DATA_SET_matches[0]
        else:
            REFERENCE_DATA_SET = "!REFERENCE_DATA_SET"
    
    cbf_to_open = NAME_TEMPLATE_OF_DATA_FRAMES.replace("?????", "00001")
    N_PIXELS_TO_THE_SHORT_EDGE, N_PIXELS_TO_THE_LONG_EDGE, pixel_size = retrieving_info_from_cbf(cbf_to_open)
    high_res = calculation_high_resolution(DETECTOR_DISTANCE, WAVELENGTH, N_PIXELS_TO_THE_SHORT_EDGE, N_PIXELS_TO_THE_LONG_EDGE, pixel_size)

    template_data = {
        "DETECTOR_DISTANCE": DETECTOR_DISTANCE,
        "ORGX": ORGX,
        "ORGY": ORGY,
        "NAME_TEMPLATE_OF_DATA_FRAMES": NAME_TEMPLATE_OF_DATA_FRAMES,
        "OSCILLATION_RANGE": OSCILLATION_RANGE,
        "WAVELENGTH": WAVELENGTH,
        "FIRST": FIRST,
        "LAST": LAST, #assume the crystal is not dead by this time
        "REFERENCE_DATA_SET": REFERENCE_DATA_SET,
        "SPACE_GROUP_NUMBER": f"SPACE_GROUP_NUMBER = {SPACE_GROUP_NUMBER}" if SPACE_GROUP_NUMBER else "SPACE_GROUP_NUMBER = 0",
        "UNIT_CELL_CONSTANTS": f"UNIT_CELL_CONSTANTS = {a:.2f} {b:.2f} {c:.2f} {alpha:.2f} {beta:.2f} {gamma:.2f}" if all([a, b, c, alpha, beta, gamma]) else "!UNIT_CELL_CONSTANTS",
        "INCLUDE_RESOLUTION_RANGE": f"50.0 {high_res}", #default parameters
        "ROTATION_AXIS": "1.0 0.0 0.0" if position % 2 == 0 else "-1.0 0.0 0.0"
    }

    with open(current_data_processing_folder / 'xds/template.INP', 'r') as f:
        src = Template(f.read())
    with open(current_data_processing_folder / 'xds/XDS.INP', 'w') as f:
        f.write(src.substitute(template_data))

    os.remove(current_data_processing_folder / 'xds/template.INP')

    xds_start(os.path.join(current_data_processing_folder,'xds'), 'xds_par',
            USER, RESERVED_NODE, SLURM_PARTITION, sshPrivateKeyPath, sshPublicKeyPath)
    #running autoPROC
    command_for_data_processing = f"process -d {os.path.join(current_data_processing_folder,'autoPROC')} -i {folder_with_raw_data} > out.log"
    xds_start(os.path.join(current_data_processing_folder,'autoPROC'), f'{command_for_data_processing}',
            USER, ["maxwell"], SLURM_PARTITION, sshPrivateKeyPath, sshPublicKeyPath)
    
def group_cbf_by_position(folder):
    """Groups CBF files by their position and frame numbers.
    Args:
        folder (str): Path to the folder containing CBF files.
    Returns:
        dict: A dictionary where keys are position strings and values are dictionaries with 'start', 'end', and 'template'.
    """
    
    position_frames = defaultdict(list)
    templates = {}
    for filename in os.listdir(folder):
        if not filename.endswith(".cbf"):
            continue
        # Match pattern ending in _######_######.cbf
        match = re.search(r"^(.*)_(\d{6})_(\d{5})\.cbf$", filename)
        if not match:
            continue
        prefix, position_str, frame_str = match.groups()
        try:
            position = int(position_str)
            frame = int(frame_str)
        except ValueError:
            continue
        position_frames[position].append(frame)
        if position not in templates:
            # Reconstruct template using the matched prefix and position
            template = os.path.join(folder, f"{prefix}_{position_str}_?????.cbf")
            templates[position] = template
    results = {}
    for position, frames in position_frames.items():
        pos_str = f"{position:06d}"
        results[pos_str] = {
            "start": min(frames),
            "end": max(frames),
            "template": templates[position]
        }
    return results


def main():
    """Main function to process command line arguments and call the filling_template function."""
    folder_with_raw_data = sys.argv[1]
    
    current_data_processing_folder = sys.argv[2]
    os.makedirs(current_data_processing_folder, exist_ok=True)
    os.makedirs(os.path.join(current_data_processing_folder, 'xds'), exist_ok=True)
    os.makedirs(os.path.join(current_data_processing_folder, 'autoPROC'), exist_ok=True)
    
    ORGX = float(sys.argv[3]) if sys.argv[3] != "None" else 0
    ORGY = float(sys.argv[4]) if sys.argv[4] != "None" else 0
    DISTANCE_OFFSET = float(sys.argv[5])
    command_for_data_processing = sys.argv[6]
    XDS_INP_template = sys.argv[7]
    REFERENCE_DATA_SET = sys.argv[8] if sys.argv[8] != "None" else "!REFERENCE_DATA_SET"
    USER, RESERVED_NODE, SLURM_PARTITION, sshPrivateKeyPath, sshPublicKeyPath = sys.argv[9:13]

    grouped_cbf = group_cbf_by_position(folder_with_raw_data)

    if grouped_cbf:
        for position, data in grouped_cbf.items():
            NAME_TEMPLATE_OF_DATA_FRAMES = data['template']
            FIRST = data['start']
            LAST = data['end']
            processing_folder = os.path.join(current_data_processing_folder, position)
            os.makedirs(processing_folder, exist_ok=True)
            filling_template(folder_with_raw_data, processing_folder, ORGX, ORGY, position, 
                            FIRST, LAST, REFERENCE_DATA_SET, DISTANCE_OFFSET, NAME_TEMPLATE_OF_DATA_FRAMES,
                            command_for_data_processing, XDS_INP_template, USER, RESERVED_NODE,
                            sshPrivateKeyPath, sshPublicKeyPath)

            Path(processing_folder, 'flag.txt').touch()

if __name__ == "__main__":
    main()