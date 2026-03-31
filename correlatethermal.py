import os
import json
import re
import torch
import torchvision.transforms as transforms
from torchvision.models import resnet50, ResNet50_Weights
from PIL import Image
from scipy.spatial.distance import cosine
import warnings

# Suppress a specific warning from torchvision
warnings.filterwarnings("ignore", message="The parameter 'pretrained' is deprecated.*")

# --- 1. Setup and Model Loading ---

def get_model():
    """Loads a pre-trained ResNet50 model and its required transformations."""
    print("Loading pre-trained ResNet-50 model...")
    weights = ResNet50_Weights.DEFAULT
    model = resnet50(weights=weights)
    model.eval()  # Set the model to evaluation mode (very important!)
    
    # We remove the final classification layer to use the model as a feature extractor
    feature_extractor = torch.nn.Sequential(*(list(model.children())[:-1]))
    return feature_extractor, weights.transforms()

def get_image_embedding(image_path, model, preprocess):
    """Generates a feature vector (embedding) for a given image."""
    try:
        img = Image.open(image_path).convert("RGB")
        img_t = preprocess(img)
        batch_t = torch.unsqueeze(img_t, 0)
        
        with torch.no_grad():
            embedding = model(batch_t)
        
        # Flatten the embedding to a 1D vector for comparison
        return embedding.squeeze().numpy()
    except Exception as e:
        print(f"Warning: Could not process image {os.path.basename(image_path)}: {e}")
        return None

# --- 2. Thermal Data Parsing ---

def parse_thermal_data(thermal_data_dir):
    """
    Parses all data from the thermal report output directory.
    """
    thermal_entries = []
    
    # The extractor script created one big text file. We'll parse it.
    text_path = os.path.join(thermal_data_dir, 'full_text.txt')
    if not os.path.exists(text_path):
        print(f"ERROR: Thermal text file not found at {text_path}")
        return []

    with open(text_path, 'r', encoding='utf-8') as f:
        full_text = f.read()

    # Use regex to find all hotspot and coldspot data points in the document.
    # This works because the thermal PDF is very regular.
    hotspot_matches = re.findall(r"Hotspot\s*:\s*([\d\.]+\s*°C)", full_text)
    coldspot_matches = re.findall(r"Coldspot\s*:\s*([\d\.]+\s*°C)", full_text)

    # Find the total number of pages from the extracted images
    image_files = [f for f in os.listdir(thermal_data_dir) if f.startswith('page') and (f.endswith('.png') or f.endswith('.jpg'))]
    page_count = 0
    if image_files:
        page_count = max([int(re.search(r'page(\d+)', f).group(1)) for f in image_files])

    print(f"Found data for {page_count} pages in the thermal report.")

    for page_num in range(1, page_count + 1):
        # Find the two largest images on the page, as PyMuPDF might extract small icons
        page_images = [f for f in os.listdir(thermal_data_dir) if f.startswith(f'page{page_num}_') and (f.endswith('.png') or f.endswith('.jpg'))]
        if len(page_images) < 2:
            continue
            
        page_images_paths = [os.path.abspath(os.path.join(thermal_data_dir, f)) for f in page_images]
        # Sort by file size descending to get the main photos
        page_images_paths.sort(key=lambda x: os.path.getsize(x), reverse=True)
        
        candidate_1 = page_images_paths[0]
        candidate_2 = page_images_paths[1]

        if not (page_num - 1 < len(hotspot_matches) and page_num - 1 < len(coldspot_matches)):
            continue

        thermal_entries.append({
            "page": page_num,
            "hotspot": hotspot_matches[page_num - 1].strip(),
            "coldspot": coldspot_matches[page_num - 1].strip(),
            "candidate_1": candidate_1,
            "candidate_2": candidate_2
        })
            
    return thermal_entries

# --- 3. Main Correlation Logic ---

def correlate_thermal_data(json_path, thermal_data_dir, output_path):
    """
    Heuristically assigns thermal images to inspection records based on page order.
    Since image similarity may not work well between thermal and visible images,
    we distribute thermal pages evenly across the 7 records.
    """
    print(f"\nLoading structured report data from {json_path}...")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            records = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {json_path} not found. Please ensure previous steps were completed correctly.")
        return

    print("Parsing thermal report data...")
    thermal_entries = parse_thermal_data(thermal_data_dir)
    if not thermal_entries:
        print("ERROR: No thermal data could be parsed. Aborting.")
        return

    # Heuristic: distribute 30 thermal pages across 7 records
    # Record 1: pages 1-4 (4)
    # Record 2: 5-8 (4)
    # Record 3: 9-12 (4)
    # Record 4: 13-16 (4)
    # Record 5: 17-20 (4)
    # Record 6: 21-24 (4)
    # Record 7: 25-30 (6)
    page_to_record = {}
    for i in range(1, 31):
        if i <= 4:
            page_to_record[i] = 1
        elif i <= 8:
            page_to_record[i] = 2
        elif i <= 12:
            page_to_record[i] = 3
        elif i <= 16:
            page_to_record[i] = 4
        elif i <= 20:
            page_to_record[i] = 5
        elif i <= 24:
            page_to_record[i] = 6
        else:
            page_to_record[i] = 7

    print(f"\nAssigning {len(thermal_entries)} thermal images to records heuristically...")

    for thermal_entry in thermal_entries:
        page_num = thermal_entry["page"]
        rec_id = page_to_record.get(page_num)
        if rec_id is None:
            continue

        print(f"  ✅ Assigned thermal page {page_num} to Record ID {rec_id}")

        record = next((r for r in records if r["id"] == rec_id), None)
        if record is None:
            continue

        # Use the first candidate as the thermal image
        thermal_image_path = thermal_entry["candidate_1"] if os.path.exists(thermal_entry["candidate_1"]) else thermal_entry["candidate_2"]

        record["thermal_data"] = {
            "hotspot": thermal_entry["hotspot"],
            "coldspot": thermal_entry["coldspot"],
            "thermal_image_path": thermal_image_path,
            "matched_by_heuristic": True
        }

    print("Correlation complete. Enriched data saved to", output_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=4)


if __name__ == "__main__":
    json_file = os.path.join("output", "structured_report.json")
    thermal_dir = os.path.join("output", "thermal_report_data")
    
    correlate_thermal_data(json_file, thermal_dir, json_file)
