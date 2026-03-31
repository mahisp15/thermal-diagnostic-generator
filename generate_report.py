import os
import json

# Optional dependency (can work without it with a local template)
try:
    import google.generativeai as genai
except ImportError:
    genai = None

from dotenv import load_dotenv

try:
    from extractor import extract_data_from_pdf
    from structure_data import structure_summary_table
    from correlate_images import correlate_sample_images
    from correlatethermal import correlate_thermal_data
except ImportError as e:
    print(f"WARNING: Could not import helper module: {e}")

load_dotenv()


def build_prompt_from_records(records):
    """Creates a structured Markdown report text from records without requiring LLM."""
    if not records:
        return "# Detailed Diagnostic Report\n\nNo structured records were available to build the report."

    issue_summary = []
    for rec in records:
        issue_summary.append(f"ID {rec.get('id')}: {rec.get('impacted_area_observation', 'No description')}")

    severity_level = "Moderate"
    if len(records) >= 6:
        severity_level = "High"
    elif len(records) <= 2:
        severity_level = "Low"

    report = []
    report.append("# Detailed Diagnostic Report\n\n")
    report.append("## 1. Property Issue Summary\n")
    report.append(f"- Total issues identified: {len(records)}\n")
    report.append(f"- Summary: {', '.join(issue_summary)}\n\n")

    report.append("## 2. Area-wise Observations & Root Causes\n\n")

    unmatched_thermal = []

    for rec in records:
        report.append(f"### Observation ID: {rec.get('id')}\n")
        report.append(f"- **Impacted Area:** {rec.get('impacted_area_observation', 'Not Available')}\n")

        obs_photos = rec.get('photos', {}).get('observation_photos', [])
        rc_photos = rec.get('photos', {}).get('root_cause_photos', [])

        report.append("- **Supporting Photos:**\n")
        if obs_photos:
            for p in obs_photos:
                report.append(f"  - ![{os.path.basename(p)}]({p})\n")
        else:
            report.append("  - Not Available\n")

        thermal = rec.get('thermal_data')
        if thermal:
            report.append("- **Thermal Analysis:**\n")
            report.append(f"  - Hotspot: {thermal.get('hotspot', 'Not Available')}\n")
            report.append(f"  - Coldspot: {thermal.get('coldspot', 'Not Available')}\n")
            report.append(f"  - Thermal image: ![{os.path.basename(thermal.get('thermal_image_path', ''))}]({thermal.get('thermal_image_path', '')})\n")
        else:
            report.append("- **Thermal Analysis:** Not Available\n")
            unmatched_thermal.append(rec.get('id'))

        report.append(f"- **Probable Root Cause:** {rec.get('probable_root_cause', 'Not Available')}\n")
        report.append("- **Supporting Photos for Root Cause:**\n")
        if rc_photos:
            for p in rc_photos:
                report.append(f"  - ![{os.path.basename(p)}]({p})\n")
        else:
            report.append("  - Not Available\n")

        report.append("\n")

    report.append("## 3. Severity Assessment\n")
    report.append(f"Based on {len(records)} observations, the overall severity is assessed as {severity_level}.\n\n")

    report.append("## 4. Recommended Actions\n")
    report.append("- Engage a qualified contractor to inspect and repair all identified areas.\n")
    report.append("- Prioritize areas with thermal anomalies and documented root causes.\n")
    report.append("- Conduct further invasive testing if leakage or hidden structural damage is suspected.\n")
    report.append("- Implement moisture mitigation and monitoring measures.\n\n")

    report.append("## 5. Additional Notes\n")
    report.append("This report is based on extracted text, images, and available thermal data. The analysis is non-invasive and relies on the provided report data.\n\n")

    report.append("## 6. Missing or Unclear Information\n")
    if unmatched_thermal:
        report.append(f"- Thermal data not matched for Observation IDs: {', '.join(map(str, unmatched_thermal))}.\n")
    else:
        report.append("- Thermal data matched for all records.\n")

    report.append("- Some image paths may not exist if extraction was incomplete.\n")

    return ''.join(report)


def generate_report_from_json(json_path, output_md_path):
    """Loads structured JSON and writes a markdown report."""
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Structured JSON not found: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        records = json.load(f)

    report_text = build_prompt_from_records(records)

    os.makedirs(os.path.dirname(output_md_path), exist_ok=True)

    with open(output_md_path, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"Generated markdown report: {output_md_path}")
    return output_md_path


def run_full_pipeline(
    sample_pdf_path='Sample Report.pdf',
    thermal_pdf_path='Thermal Images.pdf',
    output_dir='output',
    use_thermal=True,
    use_llm=False
):
    """Runs the full extract-structure-correlate-report pipeline."""
    sample_data_dir = os.path.join(output_dir, 'sample_report_data')
    thermal_data_dir = os.path.join(output_dir, 'thermal_report_data')
    structured_json_path = os.path.join(output_dir, 'structured_report.json')
    final_md_path = os.path.join(output_dir, 'detailed_diagnostic_report.md')

    print('=== Step 1: Extract data from PDFs ===')
    if not os.path.exists(sample_data_dir) or not os.path.exists(os.path.join(sample_data_dir, 'full_text.txt')):
        extract_data_from_pdf(sample_pdf_path, sample_data_dir)
    else:
        print('Sample report data already extracted.')

    if use_thermal:
        if not os.path.exists(thermal_data_dir) or not os.path.exists(os.path.join(thermal_data_dir, 'full_text.txt')):
            extract_data_from_pdf(thermal_pdf_path, thermal_data_dir)
        else:
            print('Thermal report data already extracted.')

    print('=== Step 2: Structure inspection data into JSON ===')
    structure_summary_table(
        os.path.join(sample_data_dir, 'full_text.txt'),
        structured_json_path
    )

    print('=== Step 3: Correlate inspection photos ===')
    correlate_sample_images(structured_json_path, sample_data_dir, structured_json_path)

    if use_thermal:
        print('=== Step 4: Correlate thermal report data ===')
        try:
            correlate_thermal_data(structured_json_path, thermal_data_dir, structured_json_path)
        except Exception as e:
            print(f'Warning: Thermal correlation failed ({e}). Proceeding without thermal data.')

    print('=== Step 5: Generate markdown report ===')
    return generate_report_from_json(structured_json_path, final_md_path)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run the full inspection report pipeline.')
    parser.add_argument('--sample-pdf', default='Sample Report.pdf', help='Path to the sample report PDF')
    parser.add_argument('--thermal-pdf', default='Thermal Images.pdf', help='Path to the thermal report PDF')
    parser.add_argument('--output-dir', default='output', help='Output folder path')
    parser.add_argument('--skip-thermal', action='store_true', help='Skip thermal correlation')
    parser.add_argument('--use-llm', action='store_true', help='Try to call Gemini/Google LLM for final report (optional)')

    args = parser.parse_args()

    report_file = run_full_pipeline(
        sample_pdf_path=args.sample_pdf,
        thermal_pdf_path=args.thermal_pdf,
        output_dir=args.output_dir,
        use_thermal=not args.skip_thermal,
        use_llm=args.use_llm
    )

    print('\nPipeline Complete!')
    print(f'Final report saved at: {report_file}')
