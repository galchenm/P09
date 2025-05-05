'''
import json
import requests

headers = {
    "Authorization": "Bearer ya29.a0AbVbY6OBQRtuwdw2fFcJSQHTdzNmibtqv8u3E_fGc2VpYz84NAtOM3lDn5lUv2nyO8NIeFz30M0IL_m7WwYsARH05IK05xzZ4dlvPuY3DgZ0f1g7A8lTjYdj8w4mtjk2WeZjb-OrkggSN2YqUKk5Bsbd95pNsSgaCgYKAcESARESFQFWKvPlA9MF7dhj4-JEd_buiBps-w0166"
}

para = {
    "name": "samplefile.png",
    "parents": ["1NGUAdDcPr3gocv4fAiTFxHK35c67gKGA"]
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
    "Authorization": "Bearer ya29.a0AbVbY6OBQRtuwdw2fFcJSQHTdzNmibtqv8u3E_fGc2VpYz84NAtOM3lDn5lUv2nyO8NIeFz30M0IL_m7WwYsARH05IK05xzZ4dlvPuY3DgZ0f1g7A8lTjYdj8w4mtjk2WeZjb-OrkggSN2YqUKk5Bsbd95pNsSgaCgYKAcESARESFQFWKvPlA9MF7dhj4-JEd_buiBps-w0166"
}

para = {
    "name": "samplefile.png",
    "parents": ["1NGUAdDcPr3gocv4fAiTFxHK35c67gKGA"]
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
