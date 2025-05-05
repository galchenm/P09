#!/usr/bin/env python3
# coding: utf8
# Written by: Galchenkova M. 


"""
python3 for_mask_creation.py -i /PATH/data -o /PATH/for_mask_creation.h5 -f cbf -n 1000
"""

import os
import sys
import h5py as h5
import numpy as np
import argparse
import glob
import fabio
os.nice(0)

class CustomFormatter(argparse.RawDescriptionHelpFormatter,
                      argparse.ArgumentDefaultsHelpFormatter):
    pass

def parse_cmdline_args():
    parser = argparse.ArgumentParser(
        description=sys.modules[__name__].__doc__,
        formatter_class=CustomFormatter)
    parser.add_argument('-i','--i', type=str, help="Path with files")
    parser.add_argument('-o','--o', type=str, help="The name of file for making mask")
    parser.add_argument('-f','--f', type=str, help="The format of hdf5 files (cxi/h5/nx5)")
    parser.add_argument('-pt','--pt', type=str, help="The pattern in names of hdf5 files (data, EuXFEL)")
    parser.add_argument('-s','--s', type=str, help="Single file")
    parser.add_argument('-n','--n', type=int, help="Num of patterns for the sum")
    parser.add_argument('-h5p','--h5p', type=str, help="hdf5 path for the cxi file data")

    return parser.parse_args()

def sum_hdf5(files):
    global n
    global path_cxi
    file_to_check_format = h5.File(files[0],'r')
    data_shape = file_to_check_format[path_cxi].shape
    
    file_to_check_format.close()
    
    if n is not None:
        Sum_Int = 0
        
        num = 0
        
        for ffile in files:
            
            file = h5.File(ffile, 'r')
            data = file[path_cxi]
            if num >= n:
                break
            if len(data_shape) > 2:
                
                Sum_Int += np.sum(data[:,],axis=0)
                
                num += data.shape[0]
                
                print(f'Now we processed {num} patterns')
            else:
                
                Sum_Int += data[:,]
                num += 1
                print(f'Now we processed {num} patterns')
            file.close()
    else:        
        Sum_Int = 0
        for file in files:
            file = h5.File(ffile, 'r')
            data = file[path_cxi]
            if len(data_shape) > 2:
                Sum_Int += np.sum(data[:,],axis=0)
            else:
                Sum_Int += data[:,]
            file.close()
    return Sum_Int

def sum_cbf(files):
    global n
    global path_cxi
    
    if n is not None:
        Sum_Int = 0
        
        num = 0
        print('I am here')
        for ffile in files:
            
            file = fabio.open(ffile)
            data = file.data
            data_shape = data.shape
            if num >= n:
                break
            if len(data_shape) > 2:
                
                Sum_Int += np.sum(data[:,],axis=0)
                
                num += data.shape[0]
                
                print(f'Now we processed {num} patterns')
            else:
                
                Sum_Int += data[()]
                num += 1
                print(f'Now we processed {num} patterns')
            file.close()
    else:        
        print('Warning: you are dealing with cbf files, you cannot process a single file for mask creation')
    return Sum_Int

if __name__ == "__main__":
    
    args = parse_cmdline_args()
    
    path_cxi = args.h5p
    
    file_extension = args.f
    single_file = args.s
    pattern = args.pt
    n = args.n
    input_path = args.i
    
    if single_file is None:
        files = glob.glob(os.path.join(input_path, f'*{file_extension}'))
    else:
        files = [single_file]
        
    if pattern is not None:
        files = [file for file in files if pattern in os.path.basename(file)]

    correct = True
    if single_file is not None and file_extension == 'cbf':
        print('Warning: you are dealing with cbf files, you cannot process a single file for mask creation')
        correct = False
    elif single_file is not None and file_extension != 'cbf':
        Sum_Int = sum_hdf5(files)
    elif n is not None and file_extension != 'cbf':
        Sum_Int = sum_hdf5(files)
    elif n is not None and file_extension == 'cbf':
        Sum_Int = sum_cbf(files)
    
    if correct:
        if args.o is not None:
            output_filename = args.o
        else:
            output_filename = 'forMask-v1.h5'
        f = h5.File(output_filename, 'w')
        f.create_dataset('/data', data=[np.array(Sum_Int)])
        f.close()
