import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("LANGFLOW_API_KEY")

url = "http://localhost:7860/api/v1/run/dec6471d-021e-41b4-9f74-2d7afcaaa95e"

payload = {
    "output_type": "chat",
    "input_type": "chat",
    "input_value": "Tes koneksi PaperGuard ke Langflow. Balas dengan: LANGFLOW CONNECTED"
}

headers = {
    "x-api-key": api_key,
    "Content-Type": "application/json"
}

response = requests.post(
    url,
    json=payload,
    headers=headers
)

print("STATUS:", response.status_code)
print("RESPONSE:")
print(response.text)