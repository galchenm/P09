#!/usr/bin/env python3
# coding: utf8
import math
import json
import requests
import time
import re
from collections import defaultdict
from pathlib import Path
from google.oauth2 import service_account
import urllib.parse
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image
from pydrive.auth import GoogleAuth
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import numpy as np
import pandas as pd
import shlex
import subprocess
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
import glob
import os
import sys
import pylab
import window_plot_volume_res
import warnings
warnings.filterwarnings("ignore")



# Google Sheets API credentials
GOOGLE_SHEETS_CREDENTIALS = 'client_secret.json'

# Google Drive API token
TOKEN = "..."

TOKEN_ID = f"Bearer {TOKEN}"

def statistic_from_streams(stream):
    try:
        res_hits = subprocess.run(['grep', '-rc', 'hit = 1', stream], capture_output=True, text=True, check=True).stdout.strip().split('\n')
        hits = int(res_hits[0])
    except subprocess.CalledProcessError:
        hits = 0

    try:
        chunks = int(subprocess.run(['grep', '-c', 'Image filename', stream], capture_output=True, text=True, check=True).stdout.strip().split('\n')[0])
    except subprocess.CalledProcessError:
        chunks = 0

    try:
        res_indexed = subprocess.run(['grep', '-rc', 'Begin crystal', stream], capture_output=True, text=True, check=True).stdout.strip().split('\n')
        indexed = int(res_indexed[0])
    except subprocess.CalledProcessError:
        indexed = 0

    try:
        res_none_indexed_patterns = subprocess.run(['grep', '-rc', 'indexed_by = none', stream], capture_output=True, text=True, check=True).stdout.strip().split('\n')
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
    files_lst = list(Path(path_from).glob("*.lst?*"))
    streams = list(Path(path_from, "streams").glob("*.stream?*"))

    if len(files_lst) == 0 or len(streams) == 0:
        return False
    else:
        for file_lst in files_lst:
            filename = file_lst.name.replace('split-events-EV-', '').replace('split-events-EV', '').replace('split-events-', '').replace('events-', '')
            suffix = re.search(r'.lst\d+', filename).group()
            prefix = filename.replace(suffix, '')
            suffix = re.search(r'\d+', suffix).group()
            key_name = prefix + '-' + suffix
            dic_list[Path(path_from, key_name)] = file_lst

        for stream in streams:
            streamname = stream.name
            suffix = re.search(r'.stream\d+', streamname).group()
            prefix = streamname.replace(suffix, '')
            suffix = re.search(r'\d+', suffix).group()
            key_name = prefix + '-' + suffix
            dic_stream[Path(path_from, key_name)] = stream

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
                    command = "sbatch {}".format(k.name + '.sh')
                    os.system(command)

        for k in k_inter:
            lst = dic_list[k]
            k_lst = sum(1 for _ in open(lst, 'r') if len(_) > 0)
            stream = dic_stream[k]
            command = 'grep -ic "Image filename:" {}'.format(stream)
            process = subprocess.run(shlex.split(command), capture_output=True, text=True)
            k_stream = int(process.stdout.strip())

            if k_lst != k_stream:
                print("For {}: stream = {}, lst = {}".format(k, k_stream, k_lst))
                success = False
                if rerun:
                    os.chdir(os.path.dirname(k))
                    command = "sbatch {}".format(k.name + '.sh')
                    os.system(command)

    return True


def ave_resolution(stream):
    with open(stream, 'r') as f:
        a = [float(line.split('= ')[1].split(' ')[0].rstrip("\r\n")) for line in f if "diffraction_resolution_limit" in line]

    if not a:
        return 0

    b = np.array(a)
    try:
        mean_resolution = 10.0 / np.mean(b)
    except ValueError:
        return 0

    return "{:.2}".format(mean_resolution)


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


def orientation_plot(stream_file_name, run):
    output_filename = run.replace("/", "_")
    markerSize = 0.5  # 2

    with open(stream_file_name, 'r') as f:
        stream = f.read()

    output_path = Path(stream_file_name).parent / 'plots_res'
    output_path.mkdir(exist_ok=True)
    out = output_path / (output_filename + "_astars_new.png")
    
    if not out.exists():
        print('Plotting')
        p = re.compile("astar = ([\+\-\d\.]* [\+\-\d\.]* [\+\-\d\.]*)")
        xStarStrings = p.findall(stream)
        aStars = np.array([list(map(float, x.split())) for x in xStarStrings])

        pylab.clf()

        fig = pylab.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(aStars[:, 0], aStars[:, 1], aStars[:, 2], marker=".", color="r", s=markerSize)
        pylab.title("astars")
        
        pylab.savefig(out)
        pylab.close()
    return str(out)


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
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SHEETS_CREDENTIALS, scope)
    client = gspread.authorize(creds)

    sheet = client.open(sheet_name).sheet1  # Open the spreadsheet

    try:
        list_of_hashes = sheet.get_all_records()
    except gspread.GSpreadException as e:
        print('Check your Google Sheets! There might be a duplication of the columns name!')
        return -1

    google_sheet = pd.DataFrame(list_of_hashes)
    google_runs = [str(i) for i in google_sheet['Run'].tolist() if len(str(i)) > 0]
    headers = google_sheet.columns.tolist()

    runs = [
        str(path.relative_to(processed_folder).parent).replace("\\", "/")
        for path in Path(processed_folder).rglob('CORRECT.LP')
        if path.exists() and 'indexamajig.' not in str(path)
    ] + [
        str(path.relative_to(processed_folder).parent).replace("\\", "/").replace('/streams', '')
        for path in Path(processed_folder).rglob('*stream?*')
        if path.exists() and 'indexamajig.' not in str(path.parent)
    ]


    
    runs = list(set(runs))
    runs.sort()
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
        plot_path_pref_orientation = ''
        plot_path_volume = ''
        plot_path_res = ''
        CORRECT_LP = Path(processed_folder, run, 'CORRECT.LP')
        XDS_INP = Path(processed_folder, run, 'XDS.INP')
        streams_path = Path(processed_folder, run, 'j_stream/*stream')

        if CORRECT_LP.exists():
            method = 'rotational'
            resolution = get_resolution(str(CORRECT_LP))
            command = f'grep -e "DATA_RANGE=" {str(XDS_INP)}'
            try:
                result = subprocess.run(shlex.split(command), capture_output=True, text=True)
                Number_of_patterns = int(result.stdout.strip().split(' ')[-1])
            except subprocess.CalledProcessError:
                pass
        else:
            method = 'serial'
            list_of_streams = glob.glob(str(streams_path))
            if list_of_streams:
                stream = max(list_of_streams, key=os.path.getctime)
                Number_of_patterns, Number_of_hits, Number_of_indexed_patterns, Number_of_indexed_crystals = statistic_from_streams(stream)
                if Number_of_indexed_crystals > 10:
                    resolution = ave_resolution(stream)
                    plot_path_pref_orientation = orientation_plot(stream, run)
                    
                    num_crystals_total, volume, res = window_plot_volume_res.reading_streamfile(stream)
                    if num_crystals_total is not None:
                        output_path = Path(stream).parent / 'plots_res'
                        output_path.mkdir(exist_ok=True)
                        run_name = run.replace('/','_')
                        print(f'{output_path}/{run_name}_volume.png')
                        plot_path_volume = window_plot_volume_res.plot_over_resolution(volume, picture_filename=f'{output_path}/{run_name}_volume.png', block_size = 4, label='UC volume, nm^3', title='Volume')
                        plot_path_res = window_plot_volume_res.plot_over_resolution(res, picture_filename=f'{output_path}/{run_name}_res.png', block_size = 4, label='Res, A', title='Resolution')
                    
            elif glob.glob(str(Path(processed_folder, run, '*.lst*'))):
                path_from = Path(processed_folder, run)
                if running(str(path_from), rerun):
                    files = glob.glob(str(Path(processed_folder, run, "streams/*.stream?*")))
                    stream = str(Path(processed_folder, run, "j_stream/joined.stream"))
                    
                    if not os.path.exists(stream):

                        command_line = "cat " + " ".join(files) + f' >> {stream}'
                        os.system(command_line)
                    Number_of_patterns, Number_of_hits, Number_of_indexed_patterns, Number_of_indexed_crystals = statistic_from_streams(stream)
                    if Number_of_indexed_crystals > 10:
                        resolution = ave_resolution(stream)
                        plot_path_pref_orientation = orientation_plot(stream, run)
                        num_crystals_total, volume, res = window_plot_volume_res.reading_streamfile(stream)
                        if num_crystals_total is not None:
                            output_path = Path(stream).parent / 'plots_res'
                            output_path.mkdir(exist_ok=True)
                            run_name = run.replace('/','_')
                            print(f'{output_path}/{run_name}_volume.png')
                            plot_path_volume = window_plot_volume_res.plot_over_resolution(volume, picture_filename=f'{output_path}/{run_name}_volume.png', block_size = 4, label='UC volume, nm^3', title='Volume')
                            plot_path_res = window_plot_volume_res.plot_over_resolution(res, picture_filename=f'{output_path}/{run_name}_res.png', block_size = 4, label='Res, A', title='Resolution')
                    
                else:
                    print('Not processed everything')
            else:
                print(f'No joined stream: {run}')

        google_sheet.loc[position, 'Method'] = method
        google_sheet.loc[position, 'Total N. of patterns'] = Number_of_patterns
        google_sheet.loc[position, 'Hits'] = Number_of_hits
        google_sheet.loc[position, 'Hitrate%'] = round(Number_of_hits / Number_of_patterns * 100, 3) if Number_of_patterns > 0 else 0
        google_sheet.loc[position, 'N. indexed patterns'] = Number_of_indexed_patterns
        google_sheet.loc[position, 'N. indexed crystals'] = Number_of_indexed_crystals
        google_sheet.loc[position, 'Resolution'] = str(resolution)
        
        if len(plot_path_pref_orientation) > 0:
            image_url = upload_image_to_google_drive(plot_path_pref_orientation)  # Upload the plot image to Google Drive
            google_sheet.loc[position, 'Orientation'] = f"{image_url}"
        else:
            google_sheet.loc[position, 'Orientation'] = ''

        if len(plot_path_volume) > 0:
            image_url = upload_image_to_google_drive(plot_path_volume)  # Upload the plot image to Google Drive
            google_sheet.loc[position, 'Volume/window'] = f"{image_url}"
        else:
            google_sheet.loc[position, 'Volume/window'] = ''

        if len(plot_path_res) > 0:
            image_url = upload_image_to_google_drive(plot_path_res)  # Upload the plot image to Google Drive
            google_sheet.loc[position, 'Resolution/window'] = f"{image_url}"
        else:
            google_sheet.loc[position, 'Resolution/window'] = ''
            
        values = google_sheet.values.tolist()

        # Convert the values to JSON using the custom encoder
        json_values = json.dumps(values, cls=CustomJSONEncoder)

        sheet.update([headers] + json.loads(json_values))
        

    time.sleep(25)


GOOGLE_SHEETS_NAME = sys.argv[1]
PROCESSED_FOLDER = sys.argv[2]

while True:
    update_google_sheet(GOOGLE_SHEETS_NAME, PROCESSED_FOLDER)
