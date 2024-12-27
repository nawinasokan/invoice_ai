genai.configure(api_key="AIzaSyCA0SAXGYDxFrS25lrkx2gk8YTV9V3_qRk")
model = genai.GenerativeModel("gemini-2.0-flash-thinking-exp-1219")


@app.post("/upload-invoice")
async def upload_invoice(image: UploadFile = File(...)):
    if image.content_type not in ["image/jpeg", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Only JPEG images are supported.")

    try:
        # Load the image using PIL
        image_bytes = await image.read()
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
                    extracted_data[key] = line.split(":")[-1].strip()

        print(extracted_data)
        return JSONResponse(content={"extracted_data": [extracted_data]})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")