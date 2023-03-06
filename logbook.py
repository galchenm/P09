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

NAME_GOOGLE_SHEET = "TEST_P09"
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
    
    #runs = [path[len(processed_folder)+1:].split('/j_stream')[0] for path in glob.glob(f'{processed_folder}/**/*.stream', recursive=True)] + [path[len(processed_folder)+1:].replace('/CORRECT.LP', '') for path in glob.glob(f'{processed_folder}/**/CORRECT.LP', recursive=True)]
    runs = [os.path.dirname(str(path))[len(processed_folder)+1:] for path in Path(processed_folder).rglob('CORRECT.LP')] + [os.path.dirname(str(path))[len(processed_folder)+1:] for path in Path(processed_folder).rglob('*stream')]
    
    
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
        streams_path = os.path.join(processed_folder, run, 'j_stream/*stream')
        
        if os.path.exists(CORRECT_LP):
            method = 'rotational'
            resolution = get_resolution(CORRECT_LP)
        else:
            method = 'serial'
            list_of_streams = glob.glob(streams_path)
            if len(list_of_streams) > 0:
                stream = max(list_of_streams, key=os.path.getctime)
                Number_of_patterns, Number_of_hits, Number_of_indexed_patterns, Number_of_indexed_crystals = statistic_from_streams(stream)
        
        google_sheet.loc[position, 'Method'] = method
        google_sheet.loc[position, 'Total N. of patterns'] = Number_of_patterns
        google_sheet.loc[position, 'Hits'] = Number_of_hits
        google_sheet.loc[position, 'Hitrate%'] = Number_of_hits / Number_of_patterns * 100 if Number_of_patterns > 0 else 0
        google_sheet.loc[position, 'N. indexed patterns'] = Number_of_indexed_patterns
        google_sheet.loc[position, 'N. indexed crystals'] = Number_of_indexed_crystals
        google_sheet.loc[position, 'Resolution'] = str(resolution)
        
        google_sheet.fillna('', inplace=True)
    
    sheet.update([google_sheet.columns.values.tolist()] + google_sheet.values.tolist())
    time.sleep(5)
    
while True:
    update_sheets()