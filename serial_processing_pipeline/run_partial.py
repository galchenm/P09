#!/usr/bin/env python3
# coding: utf8
# Written by Galchenkova M.

import os
import sys
import re
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
    parser.add_argument('turbo', type=str, help="Name of turbo indexer")
    parser.add_argument('-p','--p', type=str, help="Pattern in name")
    parser.add_argument('-ap','--ap', type=str, help="Additional pattern in name")
    parser.add_argument('-s','--s', type=str, help="Sample in name")
    parser.add_argument('-f','--f', type=str, help='File with blocks')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_cmdline_args()
    path_from = args.path_from
    turbo = args.turbo
    sample = args.s

    if args.f is None:
        streams = glob.glob(os.path.join(path_from,'*/j_stream/*.stream'))
    else:
        streams = []
        with open(args.f,'r') as f:
            for d in f:
                d = d.strip()
                
                for path, dirs, all_files in os.walk(path_from):
                    for di in dirs:
                        
                        if d == di:
                            print(di)
                            current_path = os.path.join(path, di)
                            s = glob.glob(os.path.join(current_path, 'j_stream/*.stream'))
                            streams += s    
    
    
    for l in streams:
        name_run = os.path.basename(l).split('.')[0]
        
        dirname = os.path.dirname(l)
        os.chdir(dirname)
        command = ''
        if sample is None:
            if args.p is None:
                if args.ap is None:
                    command = f'{turbo} {l}'
                    os.system(command)
                elif args.ap in name_run:
                    command = f'{turbo} {l}'
                    os.system(command)
            elif args.p in name_run:
                if args.ap is None:
                    command = f'{turbo} {l}'
                    os.system(command)
                elif args.ap in name_run:
                    command = f'{turbo} {l}'
                    os.system(command)                
        elif sample in name_run:
            if args.p is None:
                if args.ap is None:
                    command = f'{turbo} {l}'
                    os.system(command)
                elif args.ap in name_run:
                    command = f'{turbo} {l}'
                    os.system(command)
            elif args.p in name_run:
                if args.ap is None:
                    command = f'{turbo} {l}'
                    os.system(command)
                elif args.ap in name_run:
                    command = f'{turbo} {l}'
                    os.system(command)
    