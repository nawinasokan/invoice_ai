
# import google.generativeai as genai

# import PIL.Image



# token="AIzaSyCA0SAXGYDxFrS25lrkx2gk8YTV9V3_qRk"
# genai.configure(api_key=token)
# # model = genai.GenerativeModel("gemini-1.5-flash-8b")
# model = genai.GenerativeModel("gemini-2.0-flash-thinking-exp-1219")

# organ = PIL.Image.open("2.jpeg")
# response = model.generate_content(["Get the Company name, GSTIN, Address, Invoice No, Invoice Date, Supplier State Code, Buyer State, Buyer GST, Taxable Value, Rate, CGST, SGST, IGST, Discount and total amount(Ouput Formate Should be in JSON)", organ])
# print(response.text)




from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
from io import BytesIO
import fitz  # PyMuPDF


genai.configure(api_key="AIzaSyCA0SAXGYDxFrS25lrkx2gk8YTV9V3_qRk")
model = genai.GenerativeModel("gemini-2.0-flash-thinking-exp-1219")


ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.pdf', '.jfif']

def is_allowed_file(filename: str) -> bool:
    return any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)


@app.post("/upload-invoice")
async def upload_invoice(image: UploadFile = File(...)):
    filename = image.filename
    if not is_allowed_file(filename):
        raise HTTPException(    
            status_code=400,
            detail="Invalid file type. Allowed formats are: .jpg, .jpeg, .png, .pdf, .jfif"
        )

    try:

        image_bytes = await image.read()
        pil_image = None
        
        if filename.lower().endswith('.pdf'):
            pdf_document = fitz.open(stream=image_bytes, filetype="pdf")
            first_page = pdf_document[0]  
            pix = first_page.get_pixmap()  
            pil_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        else:

            pil_image = Image.open(BytesIO(image_bytes))

        query = "Get the Company name, GSTIN, Address, Invoice No, Invoice Date, Supplier State Code, Buyer State, Buyer GST, Taxable Value, Rate, CGST, SGST, IGST, Discount and Total Amount"
        response = model.generate_content([query, pil_image])

        extracted_data = {
            "Company_Name": None,
            "GSTIN": None,
            "Address": None,
            "Invoice_No": None,
            "Invoice_Date": None,
            "Supplier_State_Code": None,
            "Buyer_State": None,
            "Buyer_GST": None,
            "Taxable_Value": None,
            "Rate": None,
            "CGST": None,
            "SGST": None,
            "IGST": None,
            "Discount": None,
            "Total_Amount": None
        }

        for line in response.text.split("\n"):
            for key in extracted_data.keys():
                if key.replace("_", " ") in line:
                    value = line.split(":")[-1].strip()
                    value = value.replace('"', '').replace(',', '').replace("**", "").strip()
                    if key == "Address":
                        value = value.replace("\\n", ", ") 
                    extracted_data[key] = value

        return JSONResponse(content={"extracted_data": [extracted_data]})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
________________________________________________



from fastapi import FastAPI, File, UploadFile, HTTPException
from typing import List
from io import BytesIO
import os
import google.generativeai as genai
import pandas as pd
import requests
from PIL import Image
from fastapi.responses import JSONResponse

# Initialize the GenAI model (replace the API key and model with actual values)
genai.configure(api_key="AIzaSyCA0SAXGYDxFrS25lrkx2gk8YTV9V3_qRk")
model = genai.GenerativeModel("gemini-2.0-flash-thinking-exp-1219")


ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.pdf', '.jfif', '.csv', '.xlsx', '.xls']

# Check if the file has an allowed extension
def is_allowed_file(filename: str) -> bool:
    return any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)

@app.post("/upload-file")
async def upload_file(file: UploadFile = File(...)):
    filename = file.filename
    
    # Validate the file extension
    if not is_allowed_file(filename):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Allowed formats are: .jpg, .jpeg, .png, .pdf, .jfif, .csv, .xlsx, .xls"
        )

    # If the file is an image (handle invoice data extraction)
    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.jfif')):
        return await process_image(file)

    # If the file is a spreadsheet (CSV, XLSX, or XLS)
    elif filename.lower().endswith(('.csv', '.xlsx', '.xls')):
        return await process_spreadsheet(file)

    raise HTTPException(status_code=400, detail="Unsupported file format.")


async def process_image(image: UploadFile):
    try:
        # Read the file and load it with PIL
        image_bytes = await image.read()
        pil_image = Image.open(BytesIO(image_bytes))

        # Define the query for extracting invoice data
        query = "Get the Company name, GSTIN, Address, Invoice No, Invoice Date, Supplier State Code, Buyer State, Buyer GST, Taxable Value, Rate, CGST, SGST, IGST, Discount and Total Amount"
        
        # Generate content using the model
        response = model.generate_content([query, pil_image])

        # Prepare a dictionary for extracted data
        extracted_data = {
            "Company_Name": None,
            "GSTIN": None,  
            "Address": None,
            "Invoice_No": None,
            "Invoice_Date": None,
            "Supplier_State_Code": None,
            "Buyer_State": None,
            "Buyer_GST": None,
            "Taxable_Value": None,
            "Rate": None,
            "CGST": None,
            "SGST": None,
            "IGST": None,
            "Discount": None,
            "Total_Amount": None
        }

        # Parse the response text and extract data
        for line in response.text.split("\n"):
            for key in extracted_data.keys():
                if key.replace("_", " ") in line:
                    extracted_data[key] = line.split(":")[-1].strip()

        # Return the extracted data as JSON response
        return JSONResponse(content={"extracted_data": [extracted_data]})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


async def process_spreadsheet(file: UploadFile):
    try:
        # Save the file temporarily
        temp_file_path = f"{file.filename}"
        print(f"{file.filename}")
        os.makedirs("uploads", exist_ok=True)
        print(f"{file.filename}")

        with open(temp_file_path, "wb") as f:
            f.write(await file.read())
            print(f"{file.filename}")


        # Read the spreadsheet (CSV, XLSX, or XLS) using pandas
        if file.filename.lower().endswith('.csv'):
            df = pd.read_csv(temp_file_path)
        elif file.filename.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(temp_file_path)

        # Find the 'invoice link' column in the dataframe
        if 'Invoice link' not in df.columns:
            raise HTTPException(status_code=400, detail="No 'invoice link' column found in the file.")

        invoice_links = df['Invoice link'].dropna().tolist()

        # Process each invoice link
        all_extracted_data = []
        for link in invoice_links:
            try:
                # Convert the link into an image (in real use case, you could download the file or render it from a URL)
                response = requests.get(link)
                pil_image = Image.open(BytesIO(response.content))

                # Define the query for extracting invoice data
                query = "Get the Company name, GSTIN, Address, Invoice No, Invoice Date, Supplier State Code, Buyer State, Buyer GST, Taxable Value, Rate, CGST, SGST, IGST, Discount and Total Amount"
                
                # Generate content using the model
                response = model.generate_content([query, pil_image])

                # Prepare a dictionary for extracted data
                extracted_data = {
                    "Company_Name": None,
                    "GSTIN": None,  
                    "Address": None,
                    "Invoice_No": None,
                    "Invoice_Date": None,
                    "Supplier_State_Code": None,
                    "Buyer_State": None,
                    "Buyer_GST": None,
                    "Taxable_Value": None,
                    "Rate": None,
                    "CGST": None,
                    "SGST": None,
                    "IGST": None,
                    "Discount": None,
                    "Total_Amount": None
                }

                # Parse the response text and extract data
                for line in response.text.split("\n"):
                    for key in extracted_data.keys():
                        if key.replace("_", " ") in line:
                            extracted_data[key] = line.split(":")[-1].strip()

                # Append the extracted data for this link
                all_extracted_data.append(extracted_data)

            except Exception as e:
                all_extracted_data.append({"error": f"Failed to process link {link}: {str(e)}"})

        if not all_extracted_data:
            return JSONResponse(content={"message": "No valid data extracted from the URLs."})

        return JSONResponse(content={"extracted_data": all_extracted_data})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while processing the spreadsheet: {str(e)}")





