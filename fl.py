
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

