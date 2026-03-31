import json
import os

def correlate_sample_images(json_path, image_dir, output_path):
    """
    Correlates images from the Sample Report to the structured JSON data
    using a heuristic based on the report's known structure. It updates the JSON file in place.
    """
    # 1. Load the structured data
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            records = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {json_path} not found. Please run structure_data.py first.")
        return

    print(f"Loaded {len(records)} records from {json_path}")

    # 2. Define the heuristic map.
    # This map links the "Impacted Area" ID to the images that were extracted.
    # It's based on a manual review of Sample Report.pdf (pages 3-6).
    # The image filenames (e.g., 'page3_img1.png') match what extractor.py created.
    image_map = {
        # Impacted Area 1
        1: {
            "observation_images": ["page3_img1.png"] + [f"page3_img{i}.jpeg" for i in range(2, 8)],    # Photos 1-7
            "root_cause_images": [f"page3_img{i}.jpeg" for i in range(8, 12)]   # Photos 8-11
        },
        # Impacted Area 2
        2: {
            "observation_images": [f"page3_img{i}.jpeg" for i in range(12, 15)],  # Photos 12-14
            "root_cause_images": [f"page4_img{i}.jpeg" for i in range(1, 6)]     # Photos 15-19
        },
        # Impacted Area 3
        3: {
            "observation_images": [f"page4_img{i}.jpeg" for i in range(6, 12)],   # Photos 20-25
            "root_cause_images": [f"page4_img{i}.jpeg" for i in range(12, 17)]  # Photos 26-30
        },
        # Impacted Area 4
        4: {
            "observation_images": [f"page4_img{i}.jpeg" for i in range(17, 19)],  # Photos 31-32
            "root_cause_images": [f"page5_img{i}.jpeg" for i in range(1, 6)]     # Photos 33-37
        },
        # Impacted Area 5
        5: {
            "observation_images": [f"page5_img{i}.jpeg" for i in range(6, 10)],   # Photos 38-41
            "root_cause_images": [f"page5_img{i}.jpeg" for i in range(10, 17)]  # Photos 42-48
        },
        # Impacted Area 6
        6: {
            "observation_images": [f"page6_img{i}.jpeg" for i in range(1, 5)],     # Photos 49-52
            "root_cause_images": [f"page6_img{i}.jpeg" for i in range(5, 10)]    # Photos 53-57
        },
        # Impacted Area 7
        7: {
            "observation_images": [f"page6_img{i}.jpeg" for i in range(11, 12)],  # Photo 58
            "root_cause_images": [f"page6_img{i}.jpeg" for i in range(12, 18)]  # Photos 59-64
        }
    }

    # 3. Apply the map to the records
    for record in records:
        record_id = record['id']
        if record_id in image_map:
            mapping = image_map[record_id]
            
            # Create absolute paths for the image files
            obs_paths = [os.path.abspath(os.path.join(image_dir, fname)) for fname in mapping["observation_images"]]
            rc_paths = [os.path.abspath(os.path.join(image_dir, fname)) for fname in mapping["root_cause_images"]]

            # Only add paths for files that actually exist
            record["photos"]["observation_photos"] = [p for p in obs_paths if os.path.exists(p)]
            record["photos"]["root_cause_photos"] = [p for p in rc_paths if os.path.exists(p)]
            
            if len(record["photos"]["observation_photos"]) != len(obs_paths):
                print(f"Warning: Missing some observation photos for record {record_id}")
            if len(record["photos"]["root_cause_photos"]) != len(rc_paths):
                 print(f"Warning: Missing some root cause photos for record {record_id}")

    # 4. Save the updated data back to the same file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=4)

    print(f"\nSuccessfully correlated inspection images based on heuristics.")
    print(f"Updated data saved to: {output_path}")


if __name__ == "__main__":
    json_file = os.path.join("output", "structured_report.json")
    sample_report_image_dir = os.path.join("output", "sample_report_data")
    
    # This will overwrite the existing json file with the new image data
    correlate_sample_images(json_file, sample_report_image_dir, json_file)
