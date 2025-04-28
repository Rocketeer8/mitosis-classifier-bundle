# run_pipeline.py

import os
from segmentation_module import segment_frames
from tracking_module import run_trackmate_and_visualize
from post_tracking_module import classify_cells_pipeline

# --- User Configurable Paths ---
INPUT_DIR = "input"  # Drop the original TIFF frames or movies here
SEGMENTED_DIR = "output/segmented"
TRACKING_CSV_DIR = "output/tracking_csv"
OVERLAY_DIR_TRACKMATE = "output/trackmate_overlays"
OVERLAY_DIR_MITOSIS = "output/mitosis_classification_overlays"
CLASSIFIED_CSV_PATH = "output/classification_results.csv"

# --- Ensure Output Directories Exist ---
os.makedirs(SEGMENTED_DIR, exist_ok=True)
os.makedirs(TRACKING_CSV_DIR, exist_ok=True)
os.makedirs(OVERLAY_DIR_TRACKMATE, exist_ok=True)
os.makedirs(OVERLAY_DIR_MITOSIS, exist_ok=True)

# --- Pipeline Execution ---
def main():
    print("\n=== Stage 1: Segmenting Cells with Cellpose ===")
    segment_frames(INPUT_DIR, SEGMENTED_DIR)

    print("\n=== Stage 2: Tracking Cells with TrackMate ===")
    run_trackmate_and_visualize(SEGMENTED_DIR, TRACKING_CSV_DIR, OVERLAY_DIR_TRACKMATE)

    print("\n=== Stage 3: Classifying Mitosis Outcomes ===")
    classify_cells_pipeline(TRACKING_CSV_DIR, INPUT_DIR, OVERLAY_DIR_MITOSIS, CLASSIFIED_CSV_PATH)

    print("\n✅ Pipeline complete!")
    print(f" - TrackMate overlays saved at: {OVERLAY_DIR_TRACKMATE}")
    print(f" - Mitosis classification overlays saved at: {OVERLAY_DIR_MITOSIS}")
    print(f" - Classification CSV saved at: {CLASSIFIED_CSV_PATH}")

if __name__ == "__main__":
    main()
