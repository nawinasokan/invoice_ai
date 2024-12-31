

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import google.generativeai as genai
import PIL.Image
from io import BytesIO
import json
import pandas as pd
import requests
from pdf2image import convert_from_bytes
import fitz
from io import BytesIO
from PIL import Image
from urllib.parse import urlparse



# token = "AIzaSyBLnWtYXmw9stMlymaxO4J_ZxhePBm-uMw"
token ="AIzaSyBW9ot7RVqj2jWgnIncwVC1V8yfXW7BSsc"
genai.configure(api_key=token)

# Load the generative model
model = genai.GenerativeModel("gemini-2.0-flash-thinking-exp-1219")

# Allowed file extensions
ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.pdf', '.jfif', '.csv', '.xlsx']

# Function to check if a file has an allowed extension
def is_allowed_file(filename: str) -> bool:
    return any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)

# Helper function to check if a URL is valid
def is_valid_url(link: str) -> bool:
    if link == "-" or not link:
        return False
    parsed_url = urlparse(link)
    if parsed_url.scheme and parsed_url.netloc:
        # Check if the URL ends with one of the allowed extensions
        return any(link.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)
    return False

@app.post("/extract-invoice")
async def extract_invoice(file: UploadFile = File(...)):
    filename = file.filename

    # Check if the file type is allowed
    if not is_allowed_file(filename):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Allowed formats are: .jpg, .jpeg, .png, .pdf, .jfif, .csv, .xlsx"
        )

    try:
        # Read the file bytes
        file_bytes = await file.read()

        # Handle CSV and Excel file formats
        if filename.lower().endswith(('.csv', '.xlsx')):
            # Parse CSV or Excel
            if filename.lower().endswith('.csv'):
                df = pd.read_csv(BytesIO(file_bytes))
            elif filename.lower().endswith('.xlsx'):
                df = pd.read_excel(BytesIO(file_bytes))
            
            # Check for 'Invoice link' column
            if "Invoice link" not in df.columns:
                raise HTTPException(status_code=400, detail="Invoice link column not found")
            
            extracted_data = []
            extracted_count = 0  # Initialize a counter for extracted links

            # Loop through each link and process
            for idx, link in enumerate(df['Invoice link'], 1):
                # Skip invalid links
                if not is_valid_url(link):
                    print(f"Skipping invalid link: {link}")
                    continue

                # Process valid links
                data = await process_invoice_link(link)
                extracted_data.append(data)
                extracted_count += 1  # Increment count for each link processed
                print(f"Extracted {idx} invoice(s) from the provided link.")  # Print the incremental count
            
            # Return the extracted data
            return JSONResponse(content={"extracted_data": extracted_data})

        # Handle PDF and image file formats
        elif filename.lower().endswith('.pdf'):
            pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
            first_page = pdf_document[0]
            pix = first_page.get_pixmap()
            pil_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            extracted_data = await process_image(pil_image)

        else:
            # For image files, use PIL to open the image
            pil_image = PIL.Image.open(BytesIO(file_bytes))
            pil_image = pil_image.convert("L")
            extracted_data = await process_image(pil_image)

        return JSONResponse(content={"extracted_data": extracted_data})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


import time

async def process_invoice_link(link: str):
    retries = 3  # Number of retries
    retry_delay = 5  # Delay between retries (in seconds)

    for attempt in range(retries):
        try:
            # Download the image or PDF from the link
            response = requests.get(link)
            
            if response.status_code == 200:
                file_bytes = response.content
                file_ext = link.split('.')[-1].lower()

                if file_ext in ['jpg', 'jpeg', 'png', 'jfif']:
                    # Process image file
                    pil_image = PIL.Image.open(BytesIO(file_bytes))
                    pil_image = pil_image.convert("L")
                    return await process_image(pil_image)
                elif file_ext == 'pdf':
                    # Process PDF file
                    pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
                    first_page = pdf_document[0]
                    pix = first_page.get_pixmap()
                    pil_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    return await process_image(pil_image)
                else:
                    raise HTTPException(status_code=400, detail="Unsupported file format in invoice link")

            elif response.status_code == 429:
                # Handle rate limiting (Quota Exceeded)
                print(f"Quota exceeded. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise HTTPException(status_code=400, detail="Failed to fetch the file from the provided link")

        except Exception as e:
            if attempt == retries - 1:
                raise HTTPException(status_code=400, detail=f"Error processing invoice link: {str(e)}")
            else:
                # Retry for other errors
                time.sleep(retry_delay)



# Function to process the image and extract data
async def process_image(image: PIL.Image.Image):
    prompt = """
        Carefully extract the following information from the invoice image. Pay close attention to the labels, context, and relationships between fields.

        Specifically:
        - Supplier Company Name: Extract the full name of the company issuing the invoice, usually located prominently at the top of the supplier details section.
        - Supplier GSTIN: Extract the GSTIN associated with the supplier (not the buyer). This will typically be found near the supplier's name and address.
        - Address: Extract the full address of the supplier.
        - Invoice No: Extract the unique identification number of the invoice. It may be labeled as "Invoice No." or a similar variation.
        - Invoice Date: Extract the invoice issue date in the format DD/MM/YYYY.
        - Supplier State: Extract the full name of the supplier's state.
        - Supplier State Code: Extract the numeric state code associated with the supplier. Ensure it matches the supplier's state.
        - Buyer State: Extract the full name of the buyer's state.
        - Buyer GST: Extract the GSTIN associated with the buyer.
        - Taxable Value: Extract the total taxable value.
        - Rate: Extract all distinct tax rates applied to the items (e.g., 5%, 12%).
        - CGST: Extract the Central Goods and Services Tax amount.
        - SGST: Extract the State Goods and Services Tax amount.
        - IGST: Extract the Integrated Goods and Services Tax amount.
        - Discount: Extract any discount applied to the total amount.
        - Total Amount: Extract the final amount payable, including taxes and discounts.

        Return the extracted information in the following JSON format:
        ```json
        {
        "Supplier Company Name": "<supplier_company_name>",
        "Supplier GSTIN": "<supplier_gstin>",
        "Address": "<address>",
        "Invoice No": "<invoice_no>",
        "Invoice Date": "<invoice_date>",
        "Supplier State": "<supplier_state>",
        "Supplier State Code": "<supplier_state_code>",
        "Buyer State": "<buyer_state>",
        "Buyer GST": "<buyer_gst>",
        "Taxable Value": "<taxable_value>",
        "Rate": ["<rate1>", "<rate2>", ...],
        "CGST": "<cgst>",
        "SGST": "<sgst>",
        "IGST": "<igst>",
        "Discount": "<discount>",
        "Total Amount": "<total_amount>"
        }
    """

    # Get the response from the model
    response = model.generate_content([prompt, image])

    # Extract and clean the raw output
    raw_output = response.text

    # Find the JSON part of the output
    start_index = raw_output.find("{")
    end_index = raw_output.rfind("}")
    if start_index == -1 or end_index == -1:
        raise ValueError("JSON structure not found in the response.")

    # Extract and parse the JSON content
    json_content = raw_output[start_index:end_index + 1]
    parsed_data = json.loads(json_content)

    # Define a list of expected fields
    expected_fields = [
            "Supplier Company Name", "Supplier GSTIN", "Address", "Invoice No", "Invoice Date", 
            "Supplier State Code", "Buyer State", "Buyer GST", "Taxable Value", 
            "Rate", "CGST", "SGST", "IGST", "Discount", "Total Amount"
        ]

    # Replace missing fields or null values with '-'
    for field in expected_fields:
        if field not in parsed_data or parsed_data[field] is None:
            parsed_data[field] = "-"
        elif field == "Address":  # Clean up the address field if it exists
            parsed_data[field] = parsed_data[field].replace("\n", ", ")

    return parsed_data
