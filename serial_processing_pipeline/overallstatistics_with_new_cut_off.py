#!/usr/bin/env python3
#coding: utf8
#Written by Galchenkova M.

"""

"""

import os
import sys
import time
import numpy as np 
import pandas as pd
import subprocess
import shlex
import sys
import re
import time
import argparse
from collections import defaultdict

os.nice(0)

indexes = ['CC* intersects with Rsplit at', 'Resolution', 'Rsplit (%)', 'CC1/2', 'CC*', 'SNR', 'Completeness (%)', 'Multiplicity', 'Total Measurements' , 'Unique Reflections','Wilson B-factor', 'Outer shell info']

x_arg_name = 'd'
y_arg_name = 'CC*'
y_arg_name2 = 'Rsplit/%'

data_info = defaultdict(dict)


class CustomFormatter(argparse.RawDescriptionHelpFormatter,
                      argparse.ArgumentDefaultsHelpFormatter):
    pass

def parse_cmdline_args():
    parser = argparse.ArgumentParser(
        description=sys.modules[__name__].__doc__,
        formatter_class=CustomFormatter)
    parser.add_argument('hkl_input', type=str, help="hkl file")
    parser.add_argument('-r', '--resolution', default=1.6, type=float, help="Resolution to cut off")
    parser.add_argument('-n', '--nshells', default=10, type=int,  help="Number of shells")
    parser.add_argument('-p', '--pdb', type=str,  help="Unit cell file or pdb")
    parser.add_argument('-s', '--symmetry', type=str,  help="Symmetry of the sample")
    return parser.parse_args()

def get_UC(hkl_input_file):
    UC_filename = None
    try:
        command = f'grep -e indexamajig {hkl_input_file}'
        result = subprocess.check_output(shlex.split(command)).decode('utf-8').strip().split('\n')[0]
        UC_filename = '/'+re.findall(r"\b\S+\.cell", result)[0] if len(re.findall(r"\b\S+\.cell", result)) > 0 else re.findall(r"\b\S+\.pdb", result)[0]
    except subprocess.CalledProcessError:
        pass
    return UC_filename

def get_pg(hkl_input_file):
    point_group = None
    try:
        command = f'grep -e Symmetry {hkl_input_file}'
        result = subprocess.check_output(shlex.split(command)).decode('utf-8').strip().split('\n')[0]
        point_group = result.split(': ')[-1].strip()
    except subprocess.CalledProcessError:
        pass
    return point_group

def run_partialator(hkl_input_file, highres, pg, pdb, nsh):
    path = os.path.dirname(os.path.abspath(hkl_input_file))
    os.chdir(path)
    print(f'We are in {os.getcwd()}')
    data = os.path.basename(hkl_input_file).split('.')[0]
    
    if os.path.exists(f'{data}.hkl1') and os.path.exists(f'{data}.hkl2'):
    
        print('SBATCH PROCESS\n')
        job_file = os.path.join(path,"%s.sh" % data)
        with open(job_file, 'w+') as fh:
            fh.writelines("#!/bin/sh\n")
            fh.writelines("#SBATCH --job=%s\n" % data)
            fh.writelines("#SBATCH --partition=upex\n")
            fh.writelines("#SBATCH --time=12:00:00\n")
            fh.writelines("#SBATCH --nodes=1\n")
            fh.writelines("#SBATCH --nice=100\n")
            fh.writelines("#SBATCH --mem=500000\n")
            fh.writelines("#SBATCH --output=%s.out\n" % data)
            fh.writelines("#SBATCH --error=%s.err\n" % data)
            fh.writelines("source /etc/profile.d/modules.sh\n")
            fh.writelines("module load xray\n")


            fh.writelines("module load hdf5/1.10.5\n")
            fh.writelines("module load anaconda3/5.2\n")
            fh.writelines("module load maxwell crystfel\n")
            fh.writelines("export QT_QPA_PLATFORM=offscreen\n") 


            command = f"compare_hkl -p {pdb} -y {pg} --highres={highres} --nshells={nsh} --fom=CCstar --shell-file={data}_CCstar.dat {data}.hkl1 {data}.hkl2\n"
            fh.writelines(command)

            command = f"compare_hkl -p {pdb} -y {pg} --highres={highres} --nshells={nsh} --fom=Rsplit --shell-file={data}_Rsplit.dat {data}.hkl1 {data}.hkl2\n"
            fh.writelines(command)

            command = f"compare_hkl -p {pdb} -y {pg} --highres={highres} --nshells={nsh} --fom=CC --shell-file={data}_CC.dat {data}.hkl1 {data}.hkl2\n"
            fh.writelines(command)

            command = f"compare_hkl -p {pdb} -y {pg} --highres={highres} --nshells={nsh} --fom=CCano --shell-file={data}_CCano.dat {data}.hkl1 {data}.hkl2\n"
            fh.writelines(command)

            command = f"check_hkl -p {pdb} -y {pg} --highres={highres} --nshells={nsh} --shell-file={data}_SNR.dat {data}.hkl\n"
            fh.writelines(command)

            command = f"check_hkl -p {pdb} -y {pg} --highres={highres} --nshells={nsh} --wilson --shell-file={data}_Wilson.dat {data}.hkl\n"
            fh.writelines(command)
            
            max_dd = round(10./highres,3)

            command = f"python3 /gpfs/cfel/group/cxi/scratch/data/2020/EXFEL-2019-Schmidt-Mar-p002450/scratch/galchenm/scripts_for_work/plot_func/many_plots-upt-v2.py -i {data}_CCstar.dat -x '1/d' -y 'CC*' -o {data}.png -add_nargs {data}_Rsplit.dat -yad 'Rsplit/%' -x_lim_dw 1. -x_lim_up {max_dd} -t {data} -legend {data} >> output.err\n"
            fh.writelines(command)
            
        os.system("sbatch %s" % job_file)
        return "%s_CCstar.dat" % data, "%s.err" % data
    else:
        print('You do not have hkl1 and/or hkl2 files')
        return None, None

def parse_err(name_of_run, filename):
    resolution = ''
    Rsplit = ''
    CC = ''
    CCstar = ''
    snr = ''
    completeness = ''
    multiplicity = '' # it is the same as redanduncy
    total_measuremenets = ''
    unique_reflections = ''
    Wilson_B_factor = ''
    with open(filename, 'r') as file:
        for line in file:
            
            if line.startswith('Overall CC* = '):
                CCstar = re.search(r'\d+\.\d+',line).group(0)
            if line.startswith('Overall Rsplit = '):
                Rsplit = re.search(r'\d+\.\d+',line).group(0)
            if line.startswith('Overall CC = '):
                CC = re.search(r'\d+\.\d+',line).group(0)
            if line.startswith('Fixed resolution range: '):
                resolution = line[line.find("(")+1:line.find(")")].replace('to','-').replace('Angstroms','').strip()
            if ' measurements in total.' in line:
                total_measuremenets = re.search(r'\d+', line).group(0)
            if ' reflections in total.' in line:
                unique_reflections = re.search(r'\d+', line).group(0)
            if line.startswith('Overall <snr> ='):
                snr = re.search(r'\d+\.\d+',line).group(0)
            if line.startswith('Overall redundancy ='):
                multiplicity = re.search(r'\d+\.\d+',line).group(0)                
            if line.startswith('Overall completeness ='):
                completeness = re.search(r'\d+\.\d+',line).group(0)
            if line.startswith('B ='):
                Wilson_B_factor = re.search(r'\d+\.\d+',line).group(0) if re.search(r'\d+\.\d+',line) is not None else ''
    
    data_info[name_of_run]['Resolution'] = resolution
    data_info[name_of_run]['Rsplit (%)'] = Rsplit
    data_info[name_of_run]['CC1/2'] =  CC
    data_info[name_of_run]['CC*'] = CCstar
    data_info[name_of_run]['SNR'] =  snr
    data_info[name_of_run]['Completeness (%)'] = completeness
    data_info[name_of_run]['Multiplicity'] =  multiplicity
    data_info[name_of_run]['Total Measurements'] =  total_measuremenets
    data_info[name_of_run]['Unique Reflections'] =  unique_reflections
    data_info[name_of_run]['Wilson B-factor'] = Wilson_B_factor
        

def outer_shell(CCstar_dat_file):
    shell, CCstar_shell = '',''
    with open(CCstar_dat_file, 'r') as file:
        for line in file:
            line = re.sub(' +',' ', line.strip()).split(' ')
            CCstar_shell = line[1]
            shell = line[3]
    return shell, CCstar_shell

def get_xy(file_name, x_arg_name, y_arg_name):
    x = []
    y = []

    with open(file_name, 'r') as stream:
        for line in stream:
            if y_arg_name in line:
                tmp = line.replace('1/nm', '').replace('# ', '').replace('centre', '').replace('/ A', '').replace(' dev','').replace('(A)','')
                tmp = tmp.split()
                y_index = tmp.index(y_arg_name)
                x_index = tmp.index(x_arg_name)

            else:
                tmp = line.split()
                
                x.append(float(tmp[x_index]) if not np.isnan(float(tmp[x_index])) else 0. )
                y.append(float(tmp[y_index]) if not np.isnan(float(tmp[y_index])) else 0. )

    x = np.array(x)
    y = np.array(y)

    list_of_tuples = list(zip(x, y))
    
    df = pd.DataFrame(list_of_tuples, 
                  columns = [x_arg_name, y_arg_name])
    
    df = df[df[y_arg_name].notna()]
    df = df[df[y_arg_name] >= 0.]
    return df[x_arg_name], df[y_arg_name]

def calculating_max_res_from_Rsplit_CCstar_dat(CCstar_dat_file, Rsplit_dat_file):
    d_CCstar, CCstar = get_xy(CCstar_dat_file, x_arg_name, y_arg_name)
    CCstar *= 100
    
    d_Rsplit, Rsplit = get_xy(Rsplit_dat_file, x_arg_name, y_arg_name2)
    
    i = 0

    CC2, d2 = CCstar[0], d_CCstar[0]
    CC1, d1 = 0., 0.

    Rsplit2 = Rsplit[0]
    Rsplit1 = 0.

    while Rsplit[i]<=CCstar[i] and i < len(d_CCstar):
        CC1, d1, Rsplit1 = CC2, d2, Rsplit2
        i+=1
        try:
            CC2, d2, Rsplit2 = CCstar[i], d_CCstar[i], Rsplit[i]
        except:
            return -1000            
        if Rsplit[i]==CCstar[i]:
            resolution = d_CCstar[i]
            return resolution
            
    k1 = round((CC2-CC1)/(d2-d1),3)
    b1 = round((CC1*d2-CC2*d1)/(d2-d1),3)     

    k2 = round((Rsplit2-Rsplit1)/(d2-d1),3)
    b2 = round((Rsplit1*d2-Rsplit2*d1)/(d2-d1),3)

    resolution = round(0.98*(b2-b1)/(k1-k2),3)
    return resolution

def processing(CCstar_dat_file, eror_filename_to_parse):

    name_of_run = os.path.basename(CCstar_dat_file).split(".")[0].replace("_CCstar","")
    data_info[name_of_run] = {i:'' for i in indexes}
    
    Rsplit_dat_file = CCstar_dat_file.replace("CCstar","Rsplit")
    
    data_info[name_of_run]['CC* intersects with Rsplit at'] = f'{calculating_max_res_from_Rsplit_CCstar_dat(CCstar_dat_file, Rsplit_dat_file)}'
    
    shell, CCstar_shell = outer_shell(CCstar_dat_file)
    data_info[name_of_run]['Outer shell info'] = f'{shell} - {CCstar_shell}'
    
    parse_err(name_of_run, eror_filename_to_parse)
    
if __name__ == "__main__":
    args = parse_cmdline_args()
    hkl_input_file = args.hkl_input
    highres = args.resolution
    nsh = args.nshells
    pdb = get_UC(hkl_input_file) if args.pdb is None else args.pdb
    pg = get_pg(hkl_input_file) if args.symmetry is None else args.symmetry
    
    if pdb is None or pg is None:
        print('Your hkl does not contain cell or pdb file or Your hkl does not contain information about symmetry. Also you did not provide this information.')
    else:
        CCstar_dat_file, eror_filename_to_parse = run_partialator(hkl_input_file, highres, pg, pdb, nsh)
        
        while not(os.path.exists(CCstar_dat_file)) and not(os.path.exists(eror_filename_to_parse)):
            time.sleep(5.0)
        
        processing(CCstar_dat_file, eror_filename_to_parse)
        
        df = pd.DataFrame.from_dict(data_info)
        print(df)
        output = "%s_overall_statistics.txt" % hkl_input_file.split('.')[0]
        df.to_csv(output, sep=';')