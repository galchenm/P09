#!/usr/bin/env python3
# coding: utf8
# python3 logbook_v2.py  /asap3/petra3/gpfs/p09/2023/data/11016752/processed/yefanov/galchenm/processed_new

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import re
import time
import numpy as np
import os
import sys
import glob
import subprocess
from pathlib import Path
from collections import defaultdict
import shlex


NAME_GOOGLE_SHEET = "11016750" #the name of sheets
rerun = False #this option is for remerging streams for re-processed serial data

processed_folder = sys.argv[1]

def statistic_from_streams(stream):
    try:
        res_hits = subprocess.check_output(['grep', '-rc', 'hit = 1', stream]).decode('utf-8').strip().split('\n')
        hits = int(res_hits[0])
    except subprocess.CalledProcessError:
        hits = 0

    try:
        chunks = int(subprocess.check_output(['grep', '-c', 'Image filename', stream]).decode('utf-8').strip().split('\n')[0]) #len(res_hits)
    except subprocess.CalledProcessError:
        chunks = 0

    try:
        res_indexed = subprocess.check_output(['grep', '-rc', 'Begin crystal', stream]).decode('utf-8').strip().split('\n')
        indexed = int(res_indexed[0])
    except subprocess.CalledProcessError:
        indexed = 0

    try:
        res_none_indexed_patterns = subprocess.check_output(['grep', '-rc', 'indexed_by = none', stream]).decode('utf-8').strip().split('\n')
        none_indexed_patterns = int(res_none_indexed_patterns[0])
    except subprocess.CalledProcessError:
        none_indexed_patterns = 0


    indexed_patterns = chunks - none_indexed_patterns

    #print_line = f'{stream:<20}; num patterns/hits = {str(chunks)+"/"+str(hits):^10}; indexed patterns/indexed crystals = {str(indexed_patterns)+"/"+str(indexed):^10}'
    return chunks, hits, indexed_patterns, indexed

def get_resolution(CORRECTLP):
    resolution = 0
    index1 = None
    index2 = None
    
    with open(CORRECTLP, 'r') as stream:
        lines = stream.readlines()
        for line in lines:
            
            if line.startswith(' RESOLUTION RANGE  I/Sigma  Chi^2  R-FACTOR  R-FACTOR  NUMBER ACCEPTED REJECTED\n'):
                index1 = lines.index(line)
            if line.startswith('   --------------------------------------------------------------------------\n'):
                index2 = lines.index(line)
                break
        
        if index1 is None or index2 is None:
            return -200000
        else:
            i_start = index1+3
            l = re.sub(r"\s+", "**", lines[i_start].strip('\n')).split('**')[1:]
            
            if len(l) == 9:
                res, I_over_sigma = float(l[0]), float(l[2])
                prev_res, prev_I_over_sigma = 0., 0.
                
                if I_over_sigma < 1:
                    return None
                
                while I_over_sigma >= 1. and i_start < index2:
                    if I_over_sigma == 1.:
                        return res

                    prev_res, prev_I_over_sigma = res, I_over_sigma
                    i_start += 1
                    l = re.sub(r"\s+", "**", lines[i_start].strip('\n')).split('**')[1:]
                    try:
                        res, I_over_sigma = float(l[0]), float(l[2])
                    except ValueError:
                        return prev_res
                
                
                
                k = round((I_over_sigma - prev_I_over_sigma)/(res - prev_res),3)
                b = round((res*prev_I_over_sigma - prev_res*I_over_sigma)/(res-prev_res),3)
                
                try:
                    resolution = round((1-b)/k,3)
                    
                except ZeroDivisionError:
                    return None
            else:
                print(f'Something wrong with data in {CORRECTLP}')
                return None

    return resolution


def running(path_from, rerun):
    #print('Rerun ', rerun) # type(rerun) = bool
    dic_stream = defaultdict(list)
    dic_list = defaultdict(list)
    print(path_from)
    files_lst = glob.glob(os.path.join(path_from,"*.lst?*"))
    
    streams = glob.glob(os.path.join(path_from,"streams", "*.stream?*"))
    print(len(files_lst))
    success = True
    print(len(streams))
    if len(files_lst) == 0 or len(streams) == 0:
        #print("Run {} has not been processed yet".format(path_from))
        return False
    else:
        
        for file_lst in files_lst:
            filename = os.path.basename(file_lst).replace('split-events-EV-','').replace('split-events-EV','').replace('split-events-','').replace('events-','')

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
        
        print(mod_files_lst)
        print(mod_streams)
        k_inter = set(mod_files_lst) & set(mod_streams)
        k_diff = set(mod_files_lst) - set(mod_streams) #there is no streams for some lst files

        
        
        if len(k_diff) != 0:
            for k in k_diff:
                print("There is no streams for some {}".format(k))
                success = False
                
                if rerun == True:
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
                print("For {}: stream = {}, lst = {}".format(k, k_stream, k_lst))
                success = False
                if rerun == True:
                    os.chdir(os.path.dirname(k))
                    command = "sbatch {}".format(k+'.sh')
                    os.system(command)

    return success

def update_sheets():
    print("updating...\n")
    
    google_fields = ['Run', 'Method', 'Total N. of patterns', 'Hits', 'Hitrate%', 'N. indexed patterns', 'N. indexed crystals', 'Resolution'] #list(fields.keys())
    google_run_field = google_fields['run' in google_fields or 'Run' in google_fields]
    
    
    scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]

    creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
    client = gspread.authorize(creds)

    sheet = client.open(NAME_GOOGLE_SHEET).sheet1  # Open the spreadhseet

    # Extract and print all of the values
    list_of_hashes = sheet.get_all_records()


    google_sheet = pd.DataFrame(list_of_hashes)
    
    google_runs = [i for i in google_sheet[google_run_field].tolist() if len(str(i)) > 0]
    headers = google_sheet.columns.tolist()
    
    runs = [os.path.dirname(str(path))[len(processed_folder)+1:] for path in Path(processed_folder).rglob('CORRECT.LP')] + [os.path.dirname(str(path))[len(processed_folder)+1:].replace('/streams','') for path in Path(processed_folder).rglob('*stream?*')]
    
    #print([os.path.dirname(str(path))[len(processed_folder)+1:].replace('/streams','') for path in Path(processed_folder).rglob('*stream?*')])
    for run in runs:
        
        if run not in google_runs:
            position = len(google_runs) + 2
            google_runs.append(run)
        else:
            position = google_sheet[google_run_field] == run
        
        google_sheet.loc[position, 'Run'] = run
        
        Number_of_patterns = 0
        Number_of_hits = 0
        Hitrate = 0
        Number_of_indexed_patterns = 0
        Number_of_indexed_crystals = 0
        method = 0
        resolution = 0
        
        CORRECT_LP = os.path.join(processed_folder, run, 'CORRECT.LP')
        XDS_INP = os.path.join(processed_folder, run, 'XDS.INP')
        streams_path = os.path.join(processed_folder, run, 'j_stream/*stream')
        
        if os.path.exists(CORRECT_LP):
            method = 'rotational'
            resolution = get_resolution(CORRECT_LP)
            command = f' grep -e "DATA_RANGE=" {XDS_INP}'
            result = subprocess.check_output(shlex.split(command)).decode('utf-8').strip().split('\n')[0]
            Number_of_patterns = int(result.split(' ')[-1])
        else:
            method = 'serial'
            list_of_streams = glob.glob(streams_path)
            if len(list_of_streams) > 0:
                stream = max(list_of_streams, key=os.path.getctime)
                Number_of_patterns, Number_of_hits, Number_of_indexed_patterns, Number_of_indexed_crystals = statistic_from_streams(stream)
            elif len(glob.glob(os.path.join(processed_folder, run, '*.lst*'))) > 0: #we check if there any processed files at least
                path_from = os.path.join(processed_folder, run)
                if running(path_from, rerun):
                    files = glob.glob(os.path.join(processed_folder, run, "streams/*.stream?*"))
                    stream = os.path.join(processed_folder, run, "j_stream/joined.stream")
                    command_line = "cat " + " ".join(files) + f' >> {stream}'
                    print(f'CAT STREAM HERE {os.path.join(processed_folder, run)}')
                    os.system(command_line)
                    Number_of_patterns, Number_of_hits, Number_of_indexed_patterns, Number_of_indexed_crystals = statistic_from_streams(stream)
                else:
                    print('not processed everything')
            else:
                print(f'No joined stream: {run}')
        google_sheet.loc[position, 'Method'] = method
        google_sheet.loc[position, 'Total N. of patterns'] = Number_of_patterns
        google_sheet.loc[position, 'Hits'] = Number_of_hits
        google_sheet.loc[position, 'Hitrate%'] = Number_of_hits / Number_of_patterns * 100 if Number_of_patterns > 0 else 0
        google_sheet.loc[position, 'N. indexed patterns'] = Number_of_indexed_patterns
        google_sheet.loc[position, 'N. indexed crystals'] = Number_of_indexed_crystals
        google_sheet.loc[position, 'Resolution'] = str(resolution)
        
        google_sheet.fillna('', inplace=True)
    
    sheet.update([google_sheet.columns.values.tolist()] + google_sheet.values.tolist())
    time.sleep(25)
    
while True:
    update_sheets()