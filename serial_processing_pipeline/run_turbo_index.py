#!/usr/bin/env python3
# coding: utf8
# Written by Galchenkova M.


import os
import sys

import argparse

from subprocess import call
import shlex

import glob


os.nice(0)

class CustomFormatter(argparse.RawDescriptionHelpFormatter,
                      argparse.ArgumentDefaultsHelpFormatter):
    pass

def parse_cmdline_args():
    parser = argparse.ArgumentParser(
        description=sys.modules[__name__].__doc__,
        formatter_class=CustomFormatter)
    parser.add_argument('path_from', type=str, help="The path of folder/s that contain/s files")
    parser.add_argument('path_to_list', type=str, help="Path to lists of files")
    parser.add_argument('turbo', type=str, help="Name of turbo indexer")
    parser.add_argument('-p','--p', type=str, help="Pattern in name")
    parser.add_argument('-f','--f', type=str, help='File with blocks')
    parser.add_argument('-r', '--r', default=False, action="store" , help="Use this flag if you want to rerun indexing")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_cmdline_args()
    path_from = args.path_from
    plists = args.path_to_list
    turbo = args.turbo
    pattern = args.p
    
    if args.f is not None:
        lists = []
        
        with open(args.f, 'r') as file:
            for line in file:
               line = line.strip()
               lists += glob.glob(os.path.join(plists,f'{line}.lst'))
    else:
        lists = glob.glob(os.path.join(plists,'*.lst'))
    
    #print(lists)
    
    for l in lists:
        name_run = os.path.basename(l).split('.')[0]

        process_run = os.path.join(path_from, name_run)
        
        if pattern is None:
           
           if os.path.exists(process_run):
               
               os.chdir(process_run)
               streams = glob.glob('streams/*')
               
              
               if len(streams)!= 0 and not(args.r):
                   
                   delete = input(f'Type y if you want to rerun {process_run}, otherwise, enter n: ')
                   if delete == 'y':
                        indexamajig = glob.glob('indexamajig*')
                        if len(indexamajig) == 0:
                            command = 'rm *.* streams/* error/*'
                        else:
                            command = 'rm -r indexamajig* *.* streams/* error/*'
                        os.system(command)
                        command = f'{turbo} {l}'
                        os.system(command)
                   else:
                        pass #print('you do not want to delete')
               elif len(streams)!= 0 and args.r:
                   indexamajig = glob.glob('indexamajig*')
                   if len(indexamajig) == 0:
                       command = 'rm *.* streams/* error/*'
                   else:
                       command = 'rm -r indexamajig* *.* streams/* error/*'
                   os.system(command)
                   command = f'{turbo} {l}'
                   os.system(command)
               else:
                   if not(args.r):
                       ex = input(f'Type y if you want to run {process_run}, otherwise, enter n: ')
                       if ex == 'y':
                           command = f'{turbo} {l}'
                           os.system(command)
                   else:
                       command = f'{turbo} {l}'
                       os.system(command)
        elif pattern is not None and pattern in name_run:
           print(name_run)
           if os.path.exists(process_run):
               
               os.chdir(process_run)
               streams = glob.glob('streams/*')
               
               if len(streams) != 0 and not(args.r):
                   delete = input(f'Type y if you want to rerun {process_run}, otherwise, enter n: ')
                   if delete == 'y':
                       indexamajig = glob.glob('indexamajig*')
                       if len(indexamajig) == 0:
                           command = 'rm *.* streams/* error/*'
                       else:
                           command = 'rm -r indexamajig* *.* streams/* error/*'
                       os.system(command)
                       command = f'{turbo} {l}'
                       os.system(command)
               elif len(streams)!= 0 and args.r:
                   indexamajig = glob.glob('indexamajig*')
                   if len(indexamajig) == 0:
                       command = 'rm *.* streams/* error/*'
                   else:
                       command = 'rm -r indexamajig* *.* streams/* error/*'
                   os.system(command)
                   command = f'{turbo} {l}'
                   os.system(command)
               else:
                    command = f'{turbo} {l}'
                    os.system(command)
       