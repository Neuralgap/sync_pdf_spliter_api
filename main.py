from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
import time
from pydantic import BaseModel
import json
import os
import urllib
import aiohttp
from aiohttp import FormData, ClientTimeout
import asyncio
from PyPDF2 import PdfReader, PdfWriter
import io
import requests,base64


app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "https://neuralgap-1.web.app",
        "https://neuralgap-1.firebaseapp.com",
        "https://neuralgap.web.app",
        "https://neuralgap-forager-enterprise.web.app",
    ],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS", "DELETE"],
    allow_headers=["Content-Type"],
)

async def call_pdfscraper(session, file_contents, pdf_name, processTables):
    headers = {"Origin": "http://localhost:8080"}
    url = "https://us-central1-neuralgap-1.cloudfunctions.net/scraperPDFDocxTables_v3"
    # Create a FormData object
    data = FormData()
    data.add_field(
        "pdf",
        file_contents,
        filename=os.path.basename(pdf_name),
        content_type="application/pdf",
    )
    data.add_field("processTables", processTables)

    async with session.post(url, data=data, headers=headers) as resp:
        if resp.status == 200:
            response = await resp.json()
        else:
            print(f"Failed to get response: {resp.status}")
            return {}

    return response, pdf_name

async def execute_pdfscraper_async():
    file_path = "chunks"
    chunk_list = os.listdir(file_path)
    chunk_byte_list = [
        (open(f"{file_path}/{file}", "rb").read(), file) for file in chunk_list
    ]
    processTables = "True"
    response_list = []
    async with aiohttp.ClientSession() as session: #timeout=ClientTimeout(2000)
        tasks = [
            call_pdfscraper(session, file_all[0], file_all[1], processTables)
            for file_all in chunk_byte_list
        ]
        responses = await asyncio.gather(*tasks)
        for i, response in enumerate(responses):
            # print(
            #     "starting response -------------------------------> ",
            #     i,
            #     "--- file name ---> ",
            #     response[-1],
            # )
            # print(response[0])

            response_list.append(response[0])

    return response_list

def split_pdf(file_contents, file_name, pages_per_chunk):

    file_bytes = io.BytesIO(file_contents)
    reader = PdfReader(file_bytes)
    total_pages = len(reader.pages)
    print(f"Total pages in document: {total_pages}")

    # Create output directory
    output_dir = os.path.join(os.path.dirname(file_name), "chunks")
    os.makedirs(output_dir, exist_ok=True)

    # Calculate the number of chunks
    num_chunks = (total_pages + pages_per_chunk - 1) // pages_per_chunk
    print(f"Document will be split into {num_chunks} chunks.")

    # Split the document
    for i in range(num_chunks):
        writer = PdfWriter()
        start_page = i * pages_per_chunk
        end_page = min(start_page + pages_per_chunk, total_pages)

        # Add pages to the new chunk
        for page_number in range(start_page, end_page):
            writer.add_page(reader.pages[page_number])

        # Save the chunk
        output_path = os.path.join(output_dir, f"{file_name}_{i + 1}.pdf")
        with open(output_path, "wb") as output_pdf:
            writer.write(output_pdf)

        print(f"Created: {output_path}")

def collect_pdfscraper_response(scrape_response_list):
    content_list = []
    tables_dict = {}
    table_count = 1
    for response in scrape_response_list:
        content = response["corpus"]
        table_content = response["tables_raw"]

        content_list.append(content)
        for table_key in table_content.keys():
            tables_dict[str(table_count)] = table_content[table_key]
            table_count += 1

    content_str = "\n".join(content_list)

    return content_str, tables_dict

class PDFRequest(BaseModel):
    file_contents: str
    file_name: str
    pages_per_chunk: int

@app.post("/async_pdf_scrapper")
async def async_pdf_scrapper(request: PDFRequest):
    # Decode the base64 file contents
    file_contents_decoded = base64.b64decode(request.file_contents)
    # Call your split_pdf function with the decoded contents
    split_pdf(file_contents_decoded, request.file_name, request.pages_per_chunk)
    
    scrape_response_list = await execute_pdfscraper_async()

    content, table_string = collect_pdfscraper_response(scrape_response_list)

    return {"message": "PDF processed successfully","content":content,"table_string":table_string}

