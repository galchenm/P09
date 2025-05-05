'''
import json
import requests

headers = {
    "Authorization": "..."
}

para = {
    "name": "samplefile.png",
    "parents": ["..."]
}

files = {
    'data': ('metadata', json.dumps(para), 'application/json;charset=UTF-8'),
    'file': open('./image.png', 'rb')
}

r = requests.post(
    "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
    headers=headers,
    files=files
)
'''
import json
import requests

headers = {
    "Authorization": "..."
}

para = {
    "name": "samplefile.png",
    "parents": ["..."]
}

files = {
    'data': ('metadata', json.dumps(para), 'application/json;charset=UTF-8'),
    'file': open('./image.png', 'rb')
}

response = requests.post(
    "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
    headers=headers,
    files=files
)

if response.status_code == 200:
    file_data = response.json()
    file_id = file_data.get("id")
    print("File ID:", file_id)
else:
    print("Error:", response.status_code, response.text)
