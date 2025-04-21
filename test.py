import requests

headers = {
    "x-api-key": "your-secret-key-here",
    "Origin": ""
}

response = requests.get("http://localhost:8000/cdn/test.txt", headers=headers)
print(response.status_code)
print(response.text)