#!/usr/bin/env python3
# coding: utf8
# Written by Galchenkova M.


"""
"""

import os
import sys
import time
import numpy as np 
from collections import defaultdict
import logging
import re
import argparse

import subprocess
from subprocess import call
import shlex

import glob
import shutil
import matplotlib.pyplot as plt

import warnings
warnings.filterwarnings("ignore")

os.nice(0)

class CustomFormatter(argparse.RawDescriptionHelpFormatter,
                      argparse.ArgumentDefaultsHelpFormatter):
    pass

def parse_cmdline_args():
    parser = argparse.ArgumentParser(
        description=sys.modules[__name__].__doc__,
        formatter_class=CustomFormatter)
    parser.add_argument('path_from', type=str, help="The path of folder/s that contain/s files")
    parser.add_argument('-f','--f', type=str, help='File with blocks')
    parser.add_argument('-p','--p', type=str, help="Pattern in name")

    parser.add_argument('-suf','--suf', type=str, help="Suffix for stream filename")
    parser.add_argument('-pref','--pref', type=str, help="Prefix for stream filename")
    
    parser.add_argument('-o', '--o', type=str, help="The name of folder where you want to move prev results")
    parser.add_argument('-r', '--r', action='store_true', help="Use this flag if you want to rerun indexing")
    
    parser.add_argument('-d', '--d', action='store_true', help="Use this flag if you want to run detector-shift")
    
    parser.add_argument('--s', default=False, action='store_true', help="Use this flag if you want to skip merging in case if joined streams is already created")
    parser.add_argument('--no-s', dest='s', action='store_false', help="Use this flag if you don not want to skip merging in case if joined streams is already created")
    parser.add_argument('-m', '--m', action='store_true' , help="Use this flag if you want to rerun merging manually. Be careful with prefix and suffix for new stream")
    return parser.parse_args()

def setup_logger():
   level = logging.INFO
   logger = logging.getLogger("app")
   logger.setLevel(level)
   log_file = 'rerun-merge-detector-shift-logFile.log'
   formatter = logging.Formatter('%(levelname)s - %(message)s')
   ch = logging.FileHandler(log_file)
   
   ch.setLevel(level)
   ch.setFormatter(formatter)
   logger.addHandler(ch)
   logger.info("Setup logger in PID {}".format(os.getpid()))

def creating_name_of_output_joined_stream(j_stream_dir, d_name, prefix, suffix):
    if len(prefix)>0 and len(suffix)>0:
        output = f'{os.path.join(j_stream_dir, prefix+"-"+str(d_name))}-{suffix}.stream'
    if len(prefix)>0 and len(suffix)==0:
        output = f'{os.path.join(j_stream_dir, prefix+"-"+str(d_name))}.stream'                        
    if len(prefix) == 0 and len(suffix)>0:
        output = f'{os.path.join(j_stream_dir, str(d_name))}-{suffix}.stream'
    if len(prefix) == 0 and len(suffix)==0:
        output = f'{os.path.join(j_stream_dir, str(d_name))}.stream'  
    return output

def get_geometry(stream_filename):
    geometry_filename = None
    try:
        command = f'grep -e indexamajig {stream_filename}'
        result = subprocess.check_output(shlex.split(command)).decode('utf-8').strip().split('\n')[0]
        geometry_filename = '/'+re.findall(r"\b\S+\.geom", result)[0]
    except subprocess.CalledProcessError:
        pass
    return geometry_filename

def ave_resolution_plot(stream_filename):
    path_to_plots = os.path.join(os.path.dirname(stream_filename), 'plots_res')

    if not os.path.exists(path_to_plots):
        os.mkdir(path_to_plots)

    output = os.path.join(path_to_plots, os.path.basename(stream_filename).split('.')[0]+'-ave-resolution.png')
    
    f = open(stream_filename)

    a = []

    while True:
        fline = f.readline()
        if not fline:
            break
        if fline.find("diffraction_resolution_limit") != -1:
            res = float(fline.split('= ')[1].split(' ')[0].rstrip("\r\n"))
            a.append(res)
            continue

    f.close()

    b = np.array(a)
    try:
        print("Mean: {:.2} nm^-1 = {:.2} A".format(np.mean(b),10.0/np.mean(b)))
        print("Best: {:.2} nm^-1 = {:.2} A".format(np.max(b),10.0/np.max(b)))
        print("Worst: {:.2} nm^-1 = {:.2} A".format(np.min(b),10.0/np.min(b)))
        print("Std deviation: {:.2} nm^-1".format(np.std(b)))

        fig3 = plt.figure()
        plt.hist(a,bins=30)
        plt.title('Resolution based on indexing results')
        plt.xlabel('Resolution / nm^-1')
        plt.ylabel('Frequency')
        plt.grid(True)
        #plt.show()
        fig3.savefig(output)
    except ValueError:
        logger = logging.getLogger('app')
        logger.info(f'No ave-res pic for {os.path.basename(stream_filename)}')


def detector_shift(filename, geom, rerun_detector_shift):
    # Determine the mean shifts
    x_shifts = []
    y_shifts = []
    z_shifts = []
    mean_x = 0
    mean_y = 0

    prog1 = re.compile("^predict_refine/det_shift\sx\s=\s([0-9\.\-]+)\sy\s=\s([0-9\.\-]+)\smm$")
    prog2 = re.compile("^predict_refine/clen_shift\s=\s([0-9\.\-]+)\smm$")

    f = open(filename, 'r')

    while True:

        fline = f.readline()
        if not fline:
            break

        match = prog1.match(fline)
        if match:
            xshift = float(match.group(1))
            yshift = float(match.group(2))
            x_shifts.append(xshift)
            y_shifts.append(yshift)

        match = prog2.match(fline)
        if match:
            zshift = float(match.group(1))
            z_shifts.append(zshift)

    f.close()

    mean_x = sum(x_shifts) / len(x_shifts)
    mean_y = sum(y_shifts) / len(y_shifts)
    print('Mean shifts: dx = {:.2} mm,  dy = {:.2} mm'.format(mean_x,mean_y))
    
    if rerun_detector_shift:
        # Apply shifts to geometry
        print("Apply shifts to geometry")
        out = geom.split('.')[0] + f'-{os.path.basename(os.path.dirname(os.path.dirname(filename)))}.geom'
        
        print('Applying corrections to {}, output filename {}'.format(geom,out))
        print('Shifts: dx = {:.2} mm,  dy = {:.2} mm'.format(mean_x, mean_y))
        g = open(geom, 'r')
        h = open(out, 'w')
        panel_resolutions = {}

        prog1 = re.compile("^\s*res\s+=\s+([0-9\.]+)\s")
        prog2 = re.compile("^\s*(.*)\/res\s+=\s+([0-9\.]+)\s")
        prog3 = re.compile("^\s*(.*)\/corner_x\s+=\s+([0-9\.\-]+)\s")
        prog4 = re.compile("^\s*(.*)\/corner_y\s+=\s+([0-9\.\-]+)\s")
        default_res = 0
        while True:

            fline = g.readline()
            if not fline:
                break

            match = prog1.match(fline)
            if match:
                default_res = float(match.group(1))
                h.write(fline)
                continue

            match = prog2.match(fline)
            if match:
                panel = match.group(1)
                panel_res = float(match.group(2))
                default_res =  panel_res
                panel_resolutions[panel] = panel_res
                h.write(fline)
                continue

            match = prog3.match(fline)
            if match:
                panel = match.group(1)
                panel_cnx = float(match.group(2))
                if panel in panel_resolutions:
                    res = panel_resolutions[panel]
                else:
                    res = default_res
                    print('Using default resolution ({} px/m) for panel {}, shift {}'.format(res, panel, mean_x*res*1e-3))
                h.write('%s/corner_x = %f\n' % (panel,panel_cnx+(mean_x*res*1e-3)))
                continue

            match = prog4.match(fline)
            if match:
                panel = match.group(1)
                panel_cny = float(match.group(2))
                if panel in panel_resolutions:
                    res = panel_resolutions[panel]
                else:
                    res = default_res
                    print('Using default resolution ({} px/m) for panel {}, shift {}'.format(res, panel, mean_y*res*1e-3))
                h.write('%s/corner_y = %f\n' % (panel,panel_cny+(mean_y*res*1e-3)))
                continue

            h.write(fline)

        g.close()
        h.close()
        print('Saved new geometry')
    else:
        print("Don't apply shifts to geometry")
        
    def plotNewCentre(x, y):
        circle1 = plt.Circle((x,y),.1,color='r',fill=False)
        fig.gca().add_artist(circle1)
        plt.plot(x, y, 'b8', color='m')
        plt.grid(True)

    def onclick(event):
        global mean_x
        global mean_y
        print('New shifts: dx = {:.2} mm,  dy = {:.2} mm'.format(event.xdata, event.ydata))
        print('Shifts will be applied to geometry file when you close the graph window')
        mean_x = event.xdata
        mean_y = event.ydata
        plotNewCentre(mean_x, mean_y)

    nbins = 200
    H, xedges, yedges = np.histogram2d(x_shifts,y_shifts,bins=nbins)
    H = np.rot90(H)
    H = np.flipud(H)
    Hmasked = np.ma.masked_where(H==0,H)

    # Plot 2D histogram using pcolor
    plt.ion()
    fig2 = plt.figure()
    cid = fig2.canvas.mpl_connect('button_press_event', onclick)
    plt.pcolormesh(xedges,yedges,Hmasked)
    plt.title('Detector shifts according to prediction refinement')
    plt.xlabel('x shift / mm')
    plt.ylabel('y shift / mm')
    plt.plot(0, 0, 'bH', color='c')
    fig = plt.gcf()
    cbar = plt.colorbar()
    cbar.ax.set_ylabel('Counts')
    plotNewCentre(mean_x, mean_y)
    #plt.show(block=True)

    path_to_plots = os.path.join(os.path.dirname(filename), 'plots_res')

    if not os.path.exists(path_to_plots):
        os.mkdir(path_to_plots)

    output = os.path.join(path_to_plots, os.path.basename(filename).split('.')[0]+'-detector-shift.png')

    print(output)
    fig2.savefig(output)    

def statistics(stream): #TO CHANGE
    logger = logging.getLogger('app')
    try:
        res_hits = subprocess.check_output(['grep', '-rc', 'hit = 1',stream]).decode('utf-8').strip().split('\n')
        hits = int(res_hits[0])
    except subprocess.CalledProcessError:
        hits = 0
        
    try:
        chunks = int(subprocess.check_output(['grep', '-c', 'Image filename',stream]).decode('utf-8').strip().split('\n')[0]) #len(res_hits)
    except subprocess.CalledProcessError:
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

    print_line = f'{stream:<20}; num patterns/hits = {str(chunks)+"/"+str(hits):^10}; indexed patterns/indexed crystals = {str(indexed_patterns)+"/"+str(indexed):^10}'
    logger.info(print_line)
    return indexed


def join_streams(streams_dir, j_stream_dir, output_stream_name, rerun_detector_shift):
    logger = logging.getLogger('app')
    current_path = os.path.dirname(streams_dir)
    if os.path.exists(streams_dir):
        os.chdir(streams_dir)
        files = glob.glob("*.stream?*")
        if len(files) > 0:
            files = [os.path.abspath(file) for file in files]
            
            command_line = "cat " + " ".join(files) + f' >> {output_stream_name}'
            os.system(command_line)
            logger.info("Run the command line: {}".format(command_line))
            geometry_filename = get_geometry(output_stream_name)
            #print(geometry_filename)
            if geometry_filename is not None:
                Nindexed = statistics(output_stream_name)
                if Nindexed>=100:
                    ave_resolution_plot(output_stream_name)
                    detector_shift(output_stream_name, geometry_filename, rerun_detector_shift)
                else:
                    logger.info("There is not enough indexed for {}".format(output_stream_name))
                #command = f"python3 /gpfs/cfel/group/cxi/scratch/data/2020/EXFEL-2019-Schmidt-Mar-p002450/scratch/galchenm/scripts_for_work/auto_merge_streams/detector-shift {output_stream_name}"
                #os.system(command)
            else:
                logger.info("There is a problem with geometry in : {}".format(output_stream_name))
            
        else:
            logger.info("There is no streams in {}".format(current_path))
    else:
        logger.info("There is something wrong with file structure in {}".format(current_path))


def merge_streams(current_path, rerun_manually, skip, prefix, suffix, output_path_for_prev_results, rerun_detector_shift):
    logger = logging.getLogger('app')
    
    if prefix is None:
        prefix = ''
    if suffix is None:
        suffix = ''    
    
    streams_dir = os.path.join(current_path, "streams")
    j_stream_dir = os.path.join(current_path, "j_stream")
    d_name = os.path.basename(current_path)
    
    if not(os.path.exists(j_stream_dir)):
        os.mkdir(j_stream_dir)
        
    output_stream_name = creating_name_of_output_joined_stream(j_stream_dir, d_name, prefix, suffix)
    
    if skip:
        if os.path.exists(output_stream_name): #skip it because joined stream with the same name exists
            print(f'You have already a joined stream with this name for {os.path.basename(current_path)}')
            logger.info(f'You have already a joined stream for {os.path.basename(current_path)}')
            return
        elif len(glob.glob(os.path.join(j_stream_dir, "*.stream"))) != 0: # if joined stream exists but with another name, you should move all results to another folder
            print(f'move existed one to prev_results subfolder in {os.path.join(j_stream_dir, output_path_for_prev_results)}')
            if not(os.path.exists(os.path.join(j_stream_dir, output_path_for_prev_results))):
                os.mkdir(os.path.join(j_stream_dir, output_path_for_prev_results))
            destination = os.path.join(j_stream_dir, output_path_for_prev_results)
            
            
            for f in glob.glob(os.path.join(j_stream_dir, "*.*")):
                shutil.move(f, destination)
            join_streams(streams_dir, j_stream_dir, output_stream_name, rerun_detector_shift)
            
        else: #here because you don't have a joined stream
            print(f'You do not have already a joined stream for {os.path.basename(current_path)}')
            join_streams(streams_dir, j_stream_dir, output_stream_name, rerun_detector_shift) #(streams_dir, j_stream_dir, d_name, prefix, suffix)
        
    elif not(skip) and rerun_manually:
        if os.path.exists(output_stream_name):
            print(f'You have already a joined stream with this name for {os.path.basename(current_path)}')
            cat = input(f'Type y if you want to cat a new stream for {os.path.basename(current_path)}, otherwise, enter n: ').lower()
            if cat == 'y':
                output_stream_name = input(f'Type a new name for joined stream (for instance, xg-thau-104.stream): ').lower()
                join_streams(streams_dir, j_stream_dir, output_stream_name, rerun_detector_shift)
        elif len(glob.glob(os.path.join(j_stream_dir, "*.stream"))) != 0:
            cat = input(f'Type y if you want to cat a new stream for {os.path.basename(current_path)}, otherwise, enter n: ').lower()
            if cat == 'y':
                if not(os.path.exists(os.path.join(j_stream_dir, output_path_for_prev_results))):
                    os.mkdir(os.path.join(j_stream_dir, output_path_for_prev_results))
                destination = os.path.join(j_stream_dir, output_path_for_prev_results)
                
                #for f in glob.glob(os.path.join(j_stream_dir, "*.stream")):
                for f in glob.glob(os.path.join(j_stream_dir, "*.*")):
                    shutil.move(f, destination)
                    
                join_streams(streams_dir, j_stream_dir, output_stream_name, rerun_detector_shift) #(streams_dir, j_stream_dir, d_name, prefix, suffix)
        else: #here because you don't have a joined stream
            join_streams(streams_dir, j_stream_dir, output_stream_name, rerun_detector_shift) #(streams_dir, j_stream_dir, d_name, prefix, suffix)
            
    else: # move all existed joined streams and results to another folder
        if len(glob.glob(os.path.join(j_stream_dir, "*.stream"))) != 0:
            print(f'You have already a joined stream for {os.path.basename(current_path)}')
            print(f'Move existed one to prev_results subfolder in {os.path.join(j_stream_dir, output_path_for_prev_results)}')
            if not(os.path.exists(os.path.join(j_stream_dir, output_path_for_prev_results))):
                os.mkdir(os.path.join(j_stream_dir, output_path_for_prev_results))
            destination = os.path.join(j_stream_dir, output_path_for_prev_results)
            
            #for f in glob.glob(os.path.join(j_stream_dir, "*.stream")):
            for f in glob.glob(os.path.join(j_stream_dir, "*.*")):
                shutil.move(f, destination)
                
            join_streams(streams_dir, j_stream_dir, output_stream_name, rerun_detector_shift) #(streams_dir, j_stream_dir, d_name, prefix, suffix)
        else: #here because you don't have a joined stream
            print(f'You do not have already a joined stream for {os.path.basename(current_path)}')
            join_streams(streams_dir, j_stream_dir, output_stream_name, rerun_detector_shift) #(streams_dir, j_stream_dir, d_name, prefix, suffix)




def compare_lists_with_streams(path_from, rerun, rerun_merge, skip, m_prefix, m_suffix, output_path_for_prev_results, rerun_detector_shift):
    logger = logging.getLogger('app')
    
    dic_stream = defaultdict(list)
    dic_list = defaultdict(list)
    
    files_lst = glob.glob(os.path.join(path_from,"*.lst?*"))
    streams = glob.glob(os.path.join(path_from,"streams/*.stream?*"))
    
    
    success = True

    if len(files_lst) == 0:# or len(streams) == 0:
        logger.info("Run {} has not been processed yet".format(path_from))
        success = False
    else:
        
        for file_lst in files_lst:
            filename = os.path.basename(file_lst).replace('split-events-EV-','').replace('split-events-','').replace('events-','')

            suffix = re.search(r'.lst\d+', filename).group()
            prefix = filename.replace(suffix,'')

            suffix = re.search(r'\d+', suffix).group()

            key_name = prefix+'-'+suffix
            dic_list[os.path.join(path_from, key_name)] = file_lst
        
        for stream in streams:

            streamname = os.path.basename(stream)
            suffix = re.search(r'.stream\d+', streamname).group()
            prefix = streamname.replace(suffix,'')
            
            suffix = re.search(r'\d+', suffix).group()
            
            key_name = prefix+'-'+suffix
            dic_stream[os.path.join(path_from,key_name)] = stream

        mod_files_lst = dic_list.keys()
        mod_streams = dic_stream.keys()
        
        
        k_inter = set(mod_files_lst) & set(mod_streams)
        k_diff = set(mod_files_lst) - set(mod_streams) #there is no streams for some lst files
        
        if len(k_diff) != 0:
            for k in k_diff:
                logger.info("There is no streams for some {}".format(k))
                success = False
                
                if rerun:
                    os.chdir(os.path.dirname(k))
                    command = "sbatch {}".format(k+'.sh')
                    
                    os.system(command)
                
        for k in k_inter:
            
            lst = dic_list[k]

            k_lst =  len([line.strip() for line in open(lst, 'r').readlines() if len(line)>0])
            stream =  dic_stream[k]

            command = 'grep -ic "Image filename:" {}'.format(stream)
            process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
            k_stream = int(process.communicate()[0])

            if k_lst != k_stream:
                logger.info("For {}: stream = {}, lst = {}".format(k, k_stream, k_lst))
                success = False
                if rerun:
                    
                    os.chdir(os.path.dirname(k))
                    command = "sbatch {}".format(k+'.sh')
                    
                    os.system(command)
    if success:
        print(f'All processed correctly in {os.path.basename(path_from)}')
        merge_streams(path_from, rerun_merge, skip, m_prefix, m_suffix, output_path_for_prev_results, rerun_detector_shift)
    elif not success and not rerun:
        print(f'Not all processed correctly in {os.path.basename(path_from)}, but we still merge streams')
        merge_streams(path_from, rerun_merge, skip, m_prefix, m_suffix, output_path_for_prev_results, rerun_detector_shift)
    else:
        print(f'Check log file. Not all processed correctly in {os.path.basename(path_from)}')
        
def process_path(path, rerun, rerun_merge, skip, prefix, suffix, output_path_for_prev_results, rerun_detector_shift):
    compare_lists_with_streams(path, rerun, rerun_merge, skip, prefix, suffix, output_path_for_prev_results, rerun_detector_shift) 
        
def main():
    args = parse_cmdline_args()
    rerun = args.r
    pattern = args.p
    rerun_merge = args.m
    prefix = args.pref
    suffix = args.suf
    skip = args.s
    rerun_detector_shift = args.d
    
    if args.o is not None:
        output_path_for_prev_results = args.o
    else:
        output_path_for_prev_results = 'prev_res'
    
    logger = logging.getLogger('app')
    logger.info("main")
    path_from = os.path.abspath(args.path_from)
    all_directories = os.listdir(path_from) 
    print(len(all_directories))
    if pattern:
        all_directories = [os.path.join(path_from, dir) for dir in all_directories if pattern in dir]
    print(len(all_directories))


    if args.f is None:
        if len(glob.glob(os.path.join(path_from, '*.lst*')))!=0:
            process_path(all_directories, rerun, rerun_merge, skip, prefix, suffix, output_path_for_prev_results, rerun_detector_shift)
        else:
            for path in all_directories:
                print(path, len(glob.glob(os.path.join(path, '*.lst*'))))
                if len(glob.glob(os.path.join(path, '*.lst*')))!=0:
                    process_path(path, rerun, rerun_merge, skip, prefix, suffix, output_path_for_prev_results, rerun_detector_shift)                    
    else:
        with open(args.f,'r') as f:
            for d in f:
                d = d.strip()
                if len(d) > 0:
                    for path in all_directories:
                        if len(glob.glob(os.path.join(path, '*.lst*')))!=0 and d in os.path.basename(path):
                            process_path(path, rerun, rerun_merge, skip, prefix, suffix, output_path_for_prev_results, rerun_detector_shift)

setup_logger()

if __name__ == "__main__":
    main()     
