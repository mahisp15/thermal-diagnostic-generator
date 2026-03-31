# Thermal Diagnostic Report Generator

This project automates the extraction and correlation of inspection data from sample and thermal report PDFs to generate a comprehensive diagnostic report.

## Features

- **PDF Extraction**: Extracts text and images from sample and thermal report PDFs using PyMuPDF.
- **Data Structuring**: Parses summary tables into structured JSON format.
- **Image Correlation**: Matches inspection photos to observations using heuristics.
- **Thermal Analysis**: Correlates thermal images with inspection records using ResNet50 embeddings.
- **Report Generation**: Produces a detailed Markdown report with findings, photos, and thermal data.

## Setup

1. Install dependencies:
   ```
   pip install pymupdf torch torchvision pillow
   ```

2. Place your PDFs in the root directory:
   - `Sample Report.pdf` (or specify with `--sample-pdf`)
   - `Thermal Images.pdf` (or specify with `--thermal-pdf`)

3. Run the pipeline:
   ```
   python generate_report.py
   ```

## Output

- `output/structured_report.json`: Structured inspection data.
- `output/detailed_diagnostic_report.md`: Final diagnostic report.

## Limitations

- Relies on specific PDF formats for accurate extraction.
- Thermal correlation uses heuristics due to low similarity between visible and IR images.
- Requires PyTorch for thermal matching (optional with `--skip-thermal`).

## Improvements

- Integrate LLM for enhanced report insights.
- Add more robust image matching algorithms.
- Support for batch processing and web deployment.
