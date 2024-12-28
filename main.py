from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import google.generativeai as genai
import PIL.Image
from io import BytesIO
import json

app = FastAPI()

# Configure API key for Google Generative AI
token = "AIzaSyCA0SAXGYDxFrS25lrkx2gk8YTV9V3_qRk"
genai.configure(api_key=token)

model = genai.GenerativeModel("gemini-2.0-flash-thinking-exp-1219")

@app.post("/extract-invoice")
async def extract_invoice(file: UploadFile = File(...)):
    try:
        # Read and preprocess the image file
        image_bytes = await file.read()
        image = PIL.Image.open(BytesIO(image_bytes))
        image = image.convert("L")

        # Define the prompt
        prompt = """
        Extract the following fields from the invoice image and output it in valid JSON format:
        {
            "Company Name": "<company_name>",
            "GSTIN": "<gstin>",
            "Address": "<address>",
            "Invoice No": "<invoice_no>",
            "Invoice Date": "<invoice_date>",
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

        if "Address" in parsed_data:
            parsed_data["Address"] = parsed_data["Address"].replace("\n", ", ")

        return JSONResponse(content={"extracted_data": parsed_data})

    except ValueError as ve:
        return JSONResponse(status_code=400, content={"error": str(ve), "raw_output": raw_output})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# Run the app with uvicorn: uvicorn filename:app --reload
