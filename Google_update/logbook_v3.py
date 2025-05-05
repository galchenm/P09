#!/usr/bin/env python3
# coding: utf8

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import subprocess
import shlex
import os
import glob
import re
import time
from collections import defaultdict
from pathlib import Path
import pandas as pd
import numpy as np
import sys
import pylab
from mpl_toolkits.mplot3d import Axes3D
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import urllib.parse
import json
import requests

#https://developers.google.com/oauthplayground/?code=4/0AZEOvhUeNxyActECL1J6m-W1-33jebxIpR1VRHFKlJEM6VVsEDxZMNvFAX_XAh9iXKKYkw&scope=https://www.googleapis.com/auth/drive
token="..."
TOKEN_ID=f"Bearer {token}"

def statistic_from_streams(stream):
    try:
        res_hits = subprocess.check_output(['grep', '-rc', 'hit = 1', stream]).decode('utf-8').strip().split('\n')
        hits = int(res_hits[0])
    except subprocess.CalledProcessError:
        hits = 0

    try:
        chunks = int(subprocess.check_output(['grep', '-c', 'Image filename', stream]).decode('utf-8').strip().split('\n')[0])
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

                k = round((I_over_sigma - prev_I_over_sigma) / (res - prev_res), 3)
                b = round((res * prev_I_over_sigma - prev_res * I_over_sigma) / (res - prev_res), 3)

                try:
                    resolution = round((1 - b) / k, 3)

                except ZeroDivisionError:
                    return None
            else:
                print(f'Something wrong with data in {CORRECTLP}')
                return None

    return resolution


def running(path_from, rerun):
    dic_stream = defaultdict(list)
    dic_list = defaultdict(list)
    files_lst = glob.glob(os.path.join(path_from, "*.lst?*"))
    streams = glob.glob(os.path.join(path_from, "streams", "*.stream?*"))

    if len(files_lst) == 0 or len(streams) == 0:
        return False
    else:
        for file_lst in files_lst:
            filename = os.path.basename(file_lst).replace('split-events-EV-', '').replace('split-events-EV', '').replace('split-events-', '').replace('events-', '')
            suffix = re.search(r'.lst\d+', filename).group()
            prefix = filename.replace(suffix, '')
            suffix = re.search(r'\d+', suffix).group()
            key_name = prefix + '-' + suffix
            dic_list[os.path.join(path_from, key_name)] = file_lst

        for stream in streams:
            streamname = os.path.basename(stream)
            suffix = re.search(r'.stream\d+', streamname).group()
            prefix = streamname.replace(suffix, '')
            suffix = re.search(r'\d+', suffix).group()
            key_name = prefix + '-' + suffix
            dic_stream[os.path.join(path_from, key_name)] = stream

        mod_files_lst = dic_list.keys()
        mod_streams = dic_stream.keys()
        k_inter = set(mod_files_lst) & set(mod_streams)
        k_diff = set(mod_files_lst) - set(mod_streams)

        if len(k_diff) != 0:
            for k in k_diff:
                print("There is no streams for some {}".format(k))
                success = False

                if rerun:
                    os.chdir(os.path.dirname(k))
                    command = "sbatch {}".format(k + '.sh')
                    os.system(command)

        for k in k_inter:
            lst = dic_list[k]
            k_lst = len([line.strip() for line in open(lst, 'r').readlines() if len(line) > 0])
            stream = dic_stream[k]
            command = 'grep -ic "Image filename:" {}'.format(stream)
            process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
            k_stream = int(process.communicate()[0])

            if k_lst != k_stream:
                print("For {}: stream = {}, lst = {}".format(k, k_stream, k_lst))
                success = False
                if rerun:
                    os.chdir(os.path.dirname(k))
                    command = "sbatch {}".format(k + '.sh')
                    os.system(command)

    return True

def ave_resolution(stream):
    f = open(stream)

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
        mean_resolution = 10.0/np.mean(b)
    except ValueError:
        return 0
    return "{:.2}".format(mean_resolution)


'''
def upload_image_to_google_drive(image_path):
    image_url = ""
    headers = {
        "Authorization": TOKEN_ID
    }
    para = {
        "name": os.path.basename(image_path),
        "parents": ["1NGUAdDcPr3gocv4fAiTFxHK35c67gKGA"]
    }

    files = {
        'data': ('metadata', json.dumps(para), 'application/json;charset=UTF-8'),
        'file': open(image_path, 'rb')
    }

    response = requests.post(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
        headers=headers,
        files=files
    )

    if response.status_code == 200:
        file_data = response.json()
        file_id = file_data.get("id")
        

        # Get the URL for viewing the file in Google Drive
        #view_url = f"https://drive.google.com/file/d/{file_id}/view"
        image_url = f"https://drive.google.com/uc?id={file_id}" #view_url.replace('/view', '/preview')
    else:
        print("Error:", response.status_code, response.text)

    
    return image_url
'''

def upload_image_to_google_drive(image_path):
    image_url = ""
    headers = {
        "Authorization": TOKEN_ID
    }
    para = {
        "name": os.path.basename(image_path),
        "parents": ["1NGUAdDcPr3gocv4fAiTFxHK35c67gKGA"]
    }

    # Check if the file with this name already exists in the folder
    query_params = f"name='{para['name']}' and '{para['parents'][0]}' in parents and trashed=false"
    query_params = urllib.parse.quote(query_params)
    query_url = f"https://www.googleapis.com/drive/v3/files?q={query_params}"

    response = requests.get(query_url, headers=headers)

    if response.status_code == 200:
        file_data = response.json()
        files = file_data.get("files", [])
        if files:
            # File with the same name already exists
            file_id = files[0].get("id")
            image_url = f"https://drive.google.com/uc?id={file_id}"
            return image_url

    # File doesn't exist or hasn't been uploaded yet, proceed with upload
    files = {
        'data': ('metadata', json.dumps(para), 'application/json;charset=UTF-8'),
        'file': open(image_path, 'rb')
    }

    upload_response = requests.post(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
        headers=headers,
        files=files
    )

    if upload_response.status_code == 200:
        file_data = upload_response.json()
        file_id = file_data.get("id")
        image_url = f"https://drive.google.com/uc?id={file_id}"
    else:
        print("Error:", upload_response.status_code, upload_response.text)

    return image_url


 
def orientation_plot(streamFileName, run):

    output_filename = run.replace("/","_")
    markerSize = 0.5 #2


    f = open(streamFileName, 'r')
    stream = f.read()
    f.close()

    output_path = os.path.dirname(os.path.abspath(streamFileName))  + '/plots_res'
    if not os.path.exists(output_path):
        os.mkdir(output_path)

    print(output_path)
    colors = ["r", "g", "b"]
    xStarNames = ["astar","bstar","cstar"]
    for i in np.arange(3):
        p = re.compile(xStarNames[i] + " = ([\+\-\d\.]* [\+\-\d\.]* [\+\-\d\.]*)")
        xStarStrings = p.findall(stream)

        xStars = np.zeros((3, len(xStarStrings)), float)

        for j in np.arange(len(xStarStrings)):
            xStars[:,j] = np.array([float(s) for s in xStarStrings[j].split(' ')])
        pylab.clf()

        fig = pylab.figure()
        ax = Axes3D(fig)
        ax.scatter(xStars[0,:],xStars[1,:],xStars[2,:], marker=".", color=colors[i], s=markerSize)
        pylab.title(xStarNames[i] + "s")

        out = os.path.join(output_path, output_filename + "_" + xStarNames[i])+'.png'
        if not os.path.exists(out):
            pylab.savefig(out)
    pylab.close()
    return out

import math
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, float):
            if obj == float('inf') or obj == float('-inf') or math.isnan(obj):
                return None
            elif obj < -1e100 or obj > 1e100:
                return None
        return super().default(obj)


def update_google_sheet(sheet_name, processed_folder, rerun=False):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
    client = gspread.authorize(creds)

    sheet = client.open(sheet_name).sheet1  # Open the spreadsheet

    list_of_hashes = sheet.get_all_records()
    google_sheet = pd.DataFrame(list_of_hashes)
    google_runs = [i for i in google_sheet['Run'].tolist() if len(str(i)) > 0]
    headers = google_sheet.columns.tolist()
    
    #runs = [os.path.dirname(str(path))[len(processed_folder) + 1:] for path in Path(processed_folder).rglob('CORRECT.LP')] + [os.path.dirname(str(path))[len(processed_folder) + 1:].replace('/streams', '') for path in Path(processed_folder).rglob('*stream?*') if 'indexamajig.' not in str(path)]
    
    runs = [
            os.path.dirname(str(path))[len(processed_folder) + 1:]
            for path in Path(processed_folder).rglob('CORRECT.LP')
            if 'indexamajig.' not in str(path.parent)
        ] + [
            os.path.dirname(str(path))[len(processed_folder) + 1:].replace('/streams', '')
            for path in Path(processed_folder).rglob('*stream?*')
            if 'indexamajig.' not in str(path.parent)
        ]

    
    runs = list(set(runs))
    print(f'Processed {len(runs)} runs')
    for run in runs:
        print(run)
        if run not in google_runs:
            position = len(google_runs) + 2
            google_runs.append(run)
        else:
            position = google_sheet['Run'] == run

        google_sheet.loc[position, 'Run'] = run

        Number_of_patterns = 0
        Number_of_hits = 0
        Hitrate = 0
        Number_of_indexed_patterns = 0
        Number_of_indexed_crystals = 0
        method = 0
        resolution = 0
        plot_path = ''
        CORRECT_LP = os.path.join(processed_folder, run, 'CORRECT.LP')
        XDS_INP = os.path.join(processed_folder, run, 'XDS.INP')
        streams_path = os.path.join(processed_folder, run, 'j_stream/*stream')
        
        if os.path.exists(CORRECT_LP):
            method = 'rotational'
            resolution = get_resolution(CORRECT_LP)
            command = f' grep -e "DATA_RANGE=" {XDS_INP}'
            try:
                result = subprocess.check_output(shlex.split(command)).decode('utf-8').strip().split('\n')[0]
                Number_of_patterns = int(result.split(' ')[-1])
            except subprocess.CalledProcessError:
                pass
        else:
            method = 'serial'
            list_of_streams = glob.glob(streams_path)
            if len(list_of_streams) > 0:
                stream = max(list_of_streams, key=os.path.getctime)
                Number_of_patterns, Number_of_hits, Number_of_indexed_patterns, Number_of_indexed_crystals = statistic_from_streams(stream)
                if Number_of_indexed_crystals > 0:
                    resolution = ave_resolution(stream)
                    plot_path = orientation_plot(stream, run)
            elif len(glob.glob(os.path.join(processed_folder, run, '*.lst*'))) > 0:
                path_from = os.path.join(processed_folder, run)
                if running(path_from, rerun):
                    files = glob.glob(os.path.join(processed_folder, run, "streams/*.stream?*"))
                    stream = os.path.join(processed_folder, run, "j_stream/joined.stream")
                    print(stream)
                    command_line = "cat " + " ".join(files) + f' >> {stream}'
                    os.system(command_line)
                    Number_of_patterns, Number_of_hits, Number_of_indexed_patterns, Number_of_indexed_crystals = statistic_from_streams(stream)
                    if Number_of_indexed_crystals > 0:
                        resolution = ave_resolution(stream)
                        plot_path = orientation_plot(stream, run)
                else:
                    print('not processed everything')
            else:
                print(f'No joined stream: {run}')
        print(method)
        google_sheet.loc[position, 'Method'] = method
        google_sheet.loc[position, 'Total N. of patterns'] = Number_of_patterns
        google_sheet.loc[position, 'Hits'] = Number_of_hits
        google_sheet.loc[position, 'Hitrate%'] = round(Number_of_hits / Number_of_patterns * 100, 3) if Number_of_patterns > 0 else 0
        google_sheet.loc[position, 'N. indexed patterns'] = Number_of_indexed_patterns
        google_sheet.loc[position, 'N. indexed crystals'] = Number_of_indexed_crystals
        google_sheet.loc[position, 'Resolution'] = str(resolution)
        if len(plot_path) > 0 :
            
            image_url = upload_image_to_google_drive(plot_path)  # Upload the plot image to Google Drive
            
            google_sheet.loc[position, 'Orientation'] = f"{image_url}" #f'=IMAGE(("{image_url}"))'.replace("'=","=")
        else:
            google_sheet.loc[position, 'Orientation'] = ''
        values = google_sheet.values.tolist()
    
        #sheet.update([headers] + values)
        # Convert the values to JSON using the custom encoder
        json_values = json.dumps(values, cls=CustomJSONEncoder)
    
        sheet.update([headers] + json.loads(json_values))
    time.sleep(25)
    

while True:
    update_google_sheet("Test2", "/asap3/petra3/gpfs/p09/2023/data/11016750/processed/galchenm/processed_test")
