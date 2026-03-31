import fitz  # PyMuPDF
import os
import json

def extract_data_from_pdf(pdf_path, output_dir):
    """
    Extracts images and text from a PDF and saves them.
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    doc = fitz.open(pdf_path)
    all_text = ""
    image_info = []

    print(f"Processing {pdf_path}...")
    print(f"Found {len(doc)} pages.")

    # 1. Extract all text
    for page_num, page in enumerate(doc):
        all_text += page.get_text("text")

    text_output_path = os.path.join(output_dir, "full_text.txt")
    with open(text_output_path, "w", encoding="utf-8") as f:
        f.write(all_text)
    print(f"Full text saved to {text_output_path}")

    # 2. Extract all images
    for page_index in range(len(doc)):
        page = doc[page_index]
        image_list = page.get_images(full=True)
        
        for image_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            
            image_filename = f"page{page_index+1}_img{image_index+1}.{image_ext}"
            image_path = os.path.join(output_dir, image_filename)
            
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            
            image_info.append({
                "path": image_path,
                "page": page_index + 1
            })

    print(f"Extracted {len(image_info)} images to {output_dir}")
    doc.close()


if __name__ == "__main__":
    # Ensure you have the PDFs in the same directory or provide correct paths
    sample_report_path = "c:\\AI GENERALIST TASK\\Sample Report.pdf"
    thermal_report_path = "c:\\AI GENERALIST TASK\\Thermal Images.pdf"

    extract_data_from_pdf(sample_report_path, "output/sample_report_data")
    extract_data_from_pdf(thermal_report_path, "output/thermal_report_data")
