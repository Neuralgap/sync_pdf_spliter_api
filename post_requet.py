import requests
import base64

# The URL of the API endpoint
url = "http://127.0.0.1:7000/async_pdf_scrapper"

# Read the PDF file
with open("ARAFATH_Report.pdf", "rb") as f:
    file_contents = f.read()

# Encode the file contents in base64
file_contents_base64 = base64.b64encode(file_contents).decode('utf-8')

# The payload to send with the POST request
payload = {
    "file_contents": file_contents_base64,
    "file_name": "ARAFATH_Report.pdf",
    "pages_per_chunk": 2  # or any number of pages per chunk you want
}

# Send the POST request
response = requests.post(url, json=payload)

# Check the response
if response.status_code == 200:
    print("Success:", response.json())
else:
    print("Failed:", response.status_code, response.text)
