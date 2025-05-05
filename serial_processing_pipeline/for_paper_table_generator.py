#!/usr/bin/env python3
# coding: utf8
# Written by Galchenkova M.

import os
import sys
import glob
import re
import pandas as pd
import numpy as np
import argparse
from collections import defaultdict
import subprocess

os.nice(0)
indexes = ['Num. patterns/Num. hits', 'Indexed patterns/Indexed crystals', 'CC* intersects with Rsplit at', 'Resolution', 'Rsplit (%)', 'CC1/2', 'CC*', 'CCano', 'SNR', 'Completeness (%)', 'Multiplicity','Total Measurements' ,'Unique Reflections', 'Wilson B-factor']

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
    parser.add_argument('path_from', type=str, help="The path of folder/s that contain/s files")
    parser.add_argument('output', type=str, help="Path to lists of files")
    parser.add_argument('-f','--f', type=str, help='File with blocks')
    parser.add_argument('-p','--p', type=str, help='Pattern in filename or path')
    return parser.parse_args()

def parse_err(name_of_run, filename, CCstar_dat_file):
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
    CCano = None
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
            if line.startswith('Overall CCano ='):
                CCano = line.split('=')[-1].strip()
    
    shell, CCstar_shell, Rsplit_shell, CC_shell, max_shell, min_shell, SNR_shell, Completeness_shell, unique_refs_shell, multiplicity_shell = outer_shell(CCstar_dat_file)
    
    data_info[name_of_run]['Resolution'] = resolution + f' ({max_shell} - {min_shell})'
    data_info[name_of_run]['Rsplit (%)'] = Rsplit + f' ({Rsplit_shell})'
    data_info[name_of_run]['CC1/2'] =  CC + f' ({CC_shell})'
    data_info[name_of_run]['CC*'] = CCstar  + f' ({CCstar_shell})'
    data_info[name_of_run]['CCano'] = CCano
    data_info[name_of_run]['SNR'] =  snr  + f' ({SNR_shell})'
    data_info[name_of_run]['Completeness (%)'] = completeness  + f' ({Completeness_shell})'
    data_info[name_of_run]['Multiplicity'] =  multiplicity  + f' ({multiplicity_shell})'
    data_info[name_of_run]['Total Measurements'] =  total_measuremenets
    data_info[name_of_run]['Unique Reflections'] =  unique_reflections  + f' ({unique_refs_shell})'
    data_info[name_of_run]['Wilson B-factor'] = Wilson_B_factor
        

def outer_shell(CCstar_dat_file):
    shell, CCstar_shell = '',''
    with open(CCstar_dat_file, 'r') as file:
        for line in file:
            line = re.sub(' +',' ', line.strip()).split(' ')
            CCstar_shell = line[1]
            shell = line[3]
    
    max_shell, min_shell, SNR_shell, Completeness_shell, unique_refs_shell, multiplicity_shell = '','', '', '', '', ''
    SNR_dat_file = CCstar_dat_file.replace('CCstar', 'SNR')
    with open(SNR_dat_file, 'r') as file:
        for line in file:
            line = re.sub(' +',' ', line.strip()).split(' ')
            unique_refs_shell, Completeness_shell, multiplicity_shell, SNR_shell, max_shell, min_shell = line[1], line[3], line[5], line[6], line[-2], line[-1]

    
    Rsplit_dat_file = CCstar_dat_file.replace("CCstar","Rsplit")
    Rsplit_shell = ''
    with open(Rsplit_dat_file, 'r') as file:
        for line in file:
            line = re.sub(' +',' ', line.strip()).split(' ')
            Rsplit_shell = line[1]
            
    CC_dat_file = CCstar_dat_file.replace("CCstar","CC")
    CC_shell = ''
    with open(CC_dat_file, 'r') as file:
        for line in file:
            line = re.sub(' +',' ', line.strip()).split(' ')
            CC_shell = line[1]
    
    return shell, round(float(CCstar_shell),3), round(float(Rsplit_shell),3), round(float(CC_shell),3), round(10/float(max_shell),2), round(10/float(min_shell),2), round(float(SNR_shell),3), round(float(Completeness_shell),3), unique_refs_shell, multiplicity_shell  

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

def parsing_stream(stream):
    try:
        res_hits = subprocess.check_output(['grep', '-rc', 'hit = 1', stream]).decode('utf-8').strip().split('\n')
        hits = int(res_hits[0])
        chunks = int(subprocess.check_output(['grep', '-c', 'Image filename',stream]).decode('utf-8').strip().split('\n')[0]) #len(res_hits)

    except subprocess.CalledProcessError:
        hits = 0
        chunks = 0

    try:
        res_indexed = subprocess.check_output(['grep', '-rc', 'Begin crystal',stream]).decode('utf-8').strip().split('\n')
        indexed = int(res_indexed[0])
    except subprocess.CalledProcessError:
        indexed = 0

    try:
        res_none_indexed_patterns = subprocess.check_output(['grep', '-rc', 'indexed_by = none',stream]).decode('utf-8').strip().split('\n')
        none_indexed_patterns = int(res_none_indexed_patterns[0])
    except subprocess.CalledProcessError:
        none_indexed_patterns = 0

    indexed_patterns = chunks - none_indexed_patterns
    
    return chunks, hits, indexed_patterns, indexed 



def processing(CCstar_dat_files):
    global main_path
    
    for CCstar_dat_file in CCstar_dat_files:    
        name_of_run = os.path.basename(CCstar_dat_file).split(".")[0].replace("_CCstar","")
        data_info[name_of_run] = {i:'' for i in indexes}
        print(name_of_run)
        Rsplit_dat_file = CCstar_dat_file.replace("CCstar","Rsplit")
        
        data_info[name_of_run]['CC* intersects with Rsplit at'] = f'{calculating_max_res_from_Rsplit_CCstar_dat(CCstar_dat_file, Rsplit_dat_file)}'        
        
        stream = CCstar_dat_file.replace("_CCstar.dat",".stream")
        
        if not os.path.exists(stream):
            streams = glob.glob(os.path.join(os.path.dirname(CCstar_dat_file), '*stream'))
            for st in streams:
                tmp_st = os.path.basename(st).split('.')[0]
                if tmp_st+'_' in name_of_run or tmp_st+'-' in name_of_run:
                    stream = st
                    break

        print(f'For CCstar: {os.path.basename(CCstar_dat_file)} \nmathcing stream: {os.path.basename(stream)}\n\n')
        chunks, hits, indexed_patterns, indexed = parsing_stream(stream)
        
        data_info[name_of_run]['Num. patterns/Num. hits'] = str(chunks)+"/"+str(hits)
        data_info[name_of_run]['Indexed patterns/Indexed crystals'] = str(indexed_patterns)+"/"+str(indexed)
        

        filename_to_parse = glob.glob(f'{main_path}/**/{os.path.basename(CCstar_dat_file).replace("_CCstar.dat","*.err")}', recursive=True)
        
        if len(filename_to_parse)>0:
            filename_to_parse = max(filename_to_parse, key=os.path.getctime)
            
            parse_err(name_of_run, filename_to_parse, CCstar_dat_file)


if __name__ == "__main__":

    args = parse_cmdline_args()
    main_path = args.path_from
    output = args.output
    
    if args.f is not None:
        with open(args.f, 'r') as file:
            for line in file:

                
                CCstar_dat_files = glob.glob(f'{main_path}/*{line.strip()}*/**/*CCstar.dat', recursive=True)
                CCstar_dat_files = list(filter(lambda x: (args.p in x), CCstar_dat_files)) if args.p is not None else CCstar_dat_files
                
                processing(CCstar_dat_files)
    else:
        CCstar_dat_files = glob.glob(os.path.join(main_path, '*CCstar.dat'))
        if len(CCstar_dat_files) > 0:
            
            processing(CCstar_dat_files)
        else:    
            for path, dirs, all_files in os.walk(main_path):
                
                CCstar_dat_files = glob.glob(os.path.join(path, '*CCstar.dat'), recursive=True)
                CCstar_dat_files = list(filter(lambda x: (args.p in x), CCstar_dat_files)) if args.p is not None else CCstar_dat_files
                
                if len(CCstar_dat_files)>0:
                    processing(CCstar_dat_files)
    
    df = pd.DataFrame.from_dict(data_info)
    print(df)
    df.to_csv(output, sep=';')