#!/usr/bin/env python3
# coding: utf8
# Written by Galchenkova M.

import os
import sys
import re
from collections import defaultdict
import numpy as np
from multiprocessing import Pool, TimeoutError
import click
import glob

def prepare_blocks(blocks):
    d = defaultdict(dict)
    file = open(blocks, 'r')
    for line in file:
        tmp = line.strip().split(':')
        key, sample = tmp if len(tmp) > 1 else [tmp[0], ''] 
        d[key]['sample'] = sample
        
        blocks = re.findall(r"[\w]+[_\d]*", key)
        
        delimeter = re.findall(r"[-,]", key)
        if ',' in delimeter or len(blocks) == 1:
            d[key]['blocks'] = blocks
        else: #delimeter is '-'
            if len(blocks) > 2:
                print("WARNING: separate this line {} accroding to the rule of block file.\n".format(key))
            else:
                f,l = blocks
                if re.search(r"_",f) and re.search(r"_", l):
                    f_suf = re.sub(r"_",'', re.findall(r"_\d+",f)[0])
                    f_pref = re.sub(r"_",'', re.findall(r"\w+_",f)[0])
                    l_suf = re.sub(r"_",'', re.findall(r"_\d+",l)[0])
                    l_pref = re.sub(r"_",'', re.findall(r"\w+_",l)[0])

                    if f_pref != l_pref:
                        print("WARNING: this line {} could not be processed, because they have various prefix. Split these blocks into blocks with the same prefix!\n".format(key))
                        d[key]['blocks'] = []
                    else:
                        r = np.arange(int(f_suf), int(l_suf) + 1)
                        rr = [f_pref+"_"+str(i) for i in r]
                        d[key]['blocks'] = rr
                elif re.search(r"_",f) and not re.search(r"_", l) or not re.search(r"_",f) and re.search(r"_", l):
                    print("WARNING: this line {} could not be processed because parts have different type of name! Split them.\n".format(key))
                else:
                    if len(str(int(f)))!= len(str(int(l))) and len(f) == len(l):
                        pref = os.path.commonprefix([f,l])
                        d[key]['blocks'] = [pref + str(i) if len(pref + str(i)) == len(f) else pref + pref[0 : len(f) - len(pref + str(i))] + str(i) for i in np.arange(int(f), int(l) + 1)]
                    else:
                        pref = os.path.commonprefix([f,l])
                        
                        if len(pref)>0:
                            ff = f.replace(pref,'',1)
                            ll = l.replace(pref,'',1)
                            d[key]['blocks'] = [pref+str(i) for i in np.arange(int(ff), int(ll) + 1)]
                        else:
                            d[key]['blocks'] = [str(i) for i in np.arange(int(f), int(l) + 1)]
    
    return d
    


def creating_folder_structure(raw_processed_folder):
    
    if not(os.path.exists(raw_processed_folder)):
        print('Create new folder {}'.format(raw_processed_folder))
        os.mkdir(raw_processed_folder)
    if not(os.path.exists(os.path.join(raw_processed_folder, "error"))):
        os.mkdir(os.path.join(raw_processed_folder, "error"))
    if not(os.path.exists(os.path.join(raw_processed_folder, "streams"))):
        os.mkdir(os.path.join(raw_processed_folder, "streams"))
    if not(os.path.exists(os.path.join(raw_processed_folder, "j_stream"))):
        os.mkdir(os.path.join(raw_processed_folder, "j_stream"))
        os.mkdir(os.path.join(raw_processed_folder, "j_stream/error"))     

def creating_lists_for_blocks(parameters):
    global blocks_dict
    
    name_of_blocks, path_to_lists, path_from, path_to_raw_processed, pattern, file_extension, excluded = parameters
    
    try:
        blocks = blocks_dict[name_of_blocks]['blocks']
        
        sample = blocks_dict[name_of_blocks]['sample']
        filenameLST = os.path.join(path_to_lists,f'{name_of_blocks}-{sample}.lst') if len(sample)>0 else os.path.join(path_to_lists,f'{name_of_blocks}.lst')

        dirs = os.listdir(path_from)

        for di in dirs:
            
            if re.search(r"[\d]+[_\d]*", di):
                run_number = re.search(r"[\d]+[_\d]*", di).group()
                
                if run_number in blocks:
                    dir_from = os.path.join(path_from, di)
                    writing_to_lst([filenameLST, dir_from, path_to_raw_processed, pattern, file_extension, excluded])
    except KeyError:
        pass
'''
def writing_to_lst(parameters):
    filenameLST, dir_from, path_to_raw_processed, pattern, file_extension, excluded = parameters
    if os.path.exists(dir_from):
        files_of_interest = glob.glob(os.path.join(dir_from, f'*{file_extension}'))
        print(dir_from, len(files_of_interest))
        #print(files_of_interest)
        if len(files_of_interest) > 0:
            if pattern is not None:
                files_of_interest = [filename for filename in files_of_interest if (pattern in os.path.basename(filename))]
            if excluded is not None:
                files_of_interest = [filename for filename in files_of_interest if (excluded not in os.path.basename(filename))] 
            files_of_interest.sort()
            
            files_lst = open(filenameLST, 'a+')
            for f in files_of_interest:
                files_lst.write(f)
                files_lst.write("\n")
            files_lst.close()
            raw_processed_folder = os.path.join(path_to_raw_processed, os.path.basename(filenameLST).split('.')[0])
            creating_folder_structure(raw_processed_folder)
        else:
            print(f'This folder {dir_from} is empty')
    else:
        print(f'Check {dir_from}')
'''

def writing_to_lst(parameters):
    filenameLST, files_of_interest, path_to_raw_processed, pattern, file_extension, excluded = parameters
    
    #files_of_interest = glob.glob(os.path.join(dir_from, f'*{file_extension}'))

    if len(files_of_interest) > 0:
        if pattern is not None:
            files_of_interest = [filename for filename in files_of_interest if (pattern in filename)]
        if excluded is not None:
            print(excluded)
            files_of_interest = [filename for filename in files_of_interest if excluded not in filename] 
        files_of_interest.sort()
        
        files_lst = open(filenameLST, 'a+')
        for f in files_of_interest:
            files_lst.write(f)
            files_lst.write("\n")
        files_lst.close()
        raw_processed_folder = os.path.join(path_to_raw_processed, os.path.basename(filenameLST).split('.')[0])
        creating_folder_structure(raw_processed_folder)

def folder_to_list_of_files(parameters):
    path_to_lists, path_from, path_to_raw_processed, pattern, file_extension, excluded = parameters
    
    for dir_from, dirs, all_files in os.walk(path_from):
        
        files_of_interest = glob.glob(os.path.join(dir_from, f'*{file_extension}'))
        if len(files_of_interest)>0:
            filenameLST = os.path.join(path_to_lists, dir_from[len(path_from)+1:].replace('/','_')+'.lst') #os.path.join(path_to_lists, f'{os.path.basename(di)}.lst')
            #writing_to_lst_old([filenameLST, dir_from, path_to_raw_processed, pattern, file_extension, excluded])
            writing_to_lst([filenameLST, files_of_interest, path_to_raw_processed, pattern, file_extension, excluded])
        else:
            print(f'This folder {dir_from} is empty')
            
@click.command(context_settings=dict(help_option_names=["-h", "--help"]))


@click.option(
    "-i",
    "--i",
    "path_from",
    nargs=1,
    type=click.Path(exists=True),
)


@click.option(
    "-l",
    "--l",
    "path_to_lists",
    nargs=1,
    type=str,
    default=None,
    required=False,
)

@click.option(
    "-r",
    "--r",
    "path_to_raw_processed",
    nargs=1,
    type=str,
    default=None,
    required=False,
)

@click.option(
    "-o",
    "--o",
    "path_to_output",
    nargs=1,
    type=str,
    default=None,
    required=False,
)

@click.option(
    "--p",
    "-p",
    "pattern",
    nargs=1,
    type=str,
    default=None,
    required=False,
)

@click.option(
    "--fe",
    "-fe",
    "file_extension",
    nargs=1,
    type=str,
    default='h5',
    required=False,
)

@click.option(
    "--e",
    "-e",
    "excluded",
    nargs=1,
    type=str,
    default=None,
    required=False,
)

@click.option(
    "-b",
    "--b",
    "blocks",
    nargs=1,
    type=str,
    default=None,
    required=False,
)


def main(blocks, path_from, path_to_output, path_to_lists, path_to_raw_processed, pattern, file_extension, excluded):
    global blocks_dict
    print(path_to_output)
    if path_to_output is not None and not(os.path.exists(path_to_output)):
        os.makedirs(path_to_output, exist_ok=True)
        path_to_lists = os.path.join(path_to_output, 'lists')
        path_to_raw_processed = os.path.join(path_to_output, 'processed')
        os.makedirs(path_to_lists, exist_ok=True)
        os.makedirs(path_to_raw_processed, exist_ok=True)
    elif path_to_output is not None and os.path.exists(path_to_output):
        path_to_lists = os.path.join(path_to_output, 'lists')
        path_to_raw_processed = os.path.join(path_to_output, 'processed')
        if not(os.path.exists(path_to_lists)):
            os.makedirs(path_to_raw_processed, exist_ok=True)
        if not(os.path.exists(path_to_raw_processed)):
            os.makedirs(path_to_raw_processed, exist_ok=True)
            
    elif path_to_output is None:
        if path_to_lists is not None and not(os.path.exists(path_to_lists)):
            os.makedirs(path_to_lists, exist_ok=True)
        elif path_to_lists is None:
            print('You have to specify at least the path where you want to store results of data processing, or seperately path to list of files and processed results')
            return
        if path_to_raw_processed is not None and not(os.path.exists(path_to_raw_processed)):
            os.makedirs(path_to_raw_processed, exist_ok=True)
        
        
    if len(glob.glob(os.path.join(path_to_lists, '*lst'))) > 0:
        
        for filenameLST in glob.glob(os.path.join(path_to_lists, '*lst')):
            if blocks is not None:
                if os.path.basename(filenameLST) != os.path.basename(blocks):
                    os.remove(filenameLST)
            else:
                os.remove(filenameLST)
    if blocks is not None:

        blocks_dict = prepare_blocks(blocks)
        name_of_blocks = blocks_dict.keys()
        
        with Pool(processes=10) as pool:
            pool.map(creating_lists_for_blocks, zip(name_of_blocks, [path_to_lists]*len(name_of_blocks), [path_from]*len(name_of_blocks), [path_to_raw_processed]*len(name_of_blocks),[pattern]*len(name_of_blocks), [file_extension]*len(name_of_blocks), [excluded]*len(name_of_blocks)))
    else:
        folder_to_list_of_files([path_to_lists, path_from, path_to_raw_processed, pattern, file_extension, excluded])        
    print('Finished')

if __name__ == "__main__":  
    main()