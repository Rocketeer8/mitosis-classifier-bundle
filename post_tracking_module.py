import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
from PIL import Image

def detect_mitosis(group, overlap_threshold=3):  # Detect mitosis events based on distance and overlap threshold.
    frame_groups = group.groupby('FRAME')  # Group cell detections by frame number.
    last_single_cell_frame = None
    mitotic_pairs = []

    for frame, frame_group in frame_groups:
        if frame == 1:
            continue
        if len(frame_group) == 1:
            last_single_cell_frame = int(frame)
        elif len(frame_group) == 2 and last_single_cell_frame is not None:
            cell1, cell2 = frame_group.iloc[0], frame_group.iloc[1]
            avg_diameter = 2 * np.sqrt((cell1['AREA'] + cell2['AREA']) / (2 * np.pi))
            distance_threshold = 1.3 * avg_diameter  # Dynamic threshold: cells further apart than 1.3x average diameter may be division.
            distance = np.sqrt((cell1['POSITION_X'] - cell2['POSITION_X'])**2 +  # Calculate Euclidean distance between two cells.
                               (cell1['POSITION_Y'] - cell2['POSITION_Y'])**2)
            if distance > distance_threshold:
                mitotic_pairs.append((cell1['TRACK_ID'], cell2['TRACK_ID'], int(frame), distance_threshold))

    if not mitotic_pairs:
        return False

    for track_id1, track_id2, start_frame, dynamic_threshold in mitotic_pairs:
        frames_no_overlap = sum(
            (lambda frame_data: (
                np.sqrt((frame_data.iloc[0]['POSITION_X'] - frame_data.iloc[1]['POSITION_X'])**2 +
                        (frame_data.iloc[0]['POSITION_Y'] - frame_data.iloc[1]['POSITION_Y'])**2) > dynamic_threshold
            ) if len(frame_data) == 2 else False)
            (group[group['FRAME'] == f])
            for f in range(start_frame, start_frame + overlap_threshold + 1)
        )
        if frames_no_overlap >= overlap_threshold:
            return True
    return False

def classify_cells(data):
    results = []
    grouped = data.groupby('TRACK_ID')
    cell_count_threshold = 5
    frame_occurrence_threshold = 5

    for track_id, group in grouped:
        group = group.sort_values(by='FRAME')
        max_r, min_r = group['CIRCULARITY'].max(), group['CIRCULARITY'].min()
        max_a, min_a = group['AREA'].max(), group['AREA'].min()
        area_change = max_a - min_a
        splits = group['NUMBER_SPLITS'].max()

        sustained_elongation = (group['ELLIPSE_ASPECTRATIO'].dropna() > 2.0).sum() >= 3
        sustained_rounding = (group['CIRCULARITY'] > 0.85).sum() >= 3
        significant_area_change = max_a > 1.5 * min_a
        frames_exceeding_threshold = (group.groupby('FRAME').size() > cell_count_threshold).sum()  # Group cell detections by frame number.

        if frames_exceeding_threshold >= frame_occurrence_threshold:
            classification = 'NaN'
        elif splits > 0:
            mitosis_detected = detect_mitosis(group)
            if mitosis_detected and sustained_rounding and significant_area_change:
                classification = 'Y'
            elif splits > 0 and sustained_rounding and max_a > 2 * min_a:
                classification = 'T2F'
            else:
                classification = 'N'
        elif sustained_rounding and (significant_area_change or sustained_elongation):
            classification = 'T1F'
        else:
            classification = 'N'

        results.append({
            'TRACK_ID': track_id,
            'Classification': classification,
            'Max Roundness': max_r,
            'Min Roundness': min_r,
            'Max Area': max_a,
            'Min Area': min_a,
            'Area Change': area_change,
            'Sustained Rounding': sustained_rounding,
            'Significant Area Change': significant_area_change,
            'Sustained Elongation': sustained_elongation,
        })

    return pd.DataFrame(results)

def extract_last_number(filename):
    # Find all digit groups, then return the last one
    numbers = re.findall(r'\d+', filename)
    return int(numbers[-1]) if numbers else float('inf')

def classify_cells_pipeline(tracking_csv_dir, original_frames_dir, output_overlay_dir, output_csv_path):
    tracks_df = pd.read_csv(os.path.join(tracking_csv_dir, "tracks.csv"))
    spots_df = pd.read_csv(os.path.join(tracking_csv_dir, "spots.csv"))

    os.makedirs(output_overlay_dir, exist_ok=True)
    spots_df['ELLIPSE_ASPECTRATIO'] = pd.to_numeric(spots_df['ELLIPSE_ASPECTRATIO'], errors='coerce')
    merged_df = pd.merge(spots_df, tracks_df, on='TRACK_ID', how='left')

    classification_results = classify_cells(merged_df)  # Run classification of each track into mitosis outcome types.
    # Compute classification rates
    classification_counts = classification_results['Classification'].value_counts()  # Count how many tracks are classified into each category (N, Y, T1F, T2F, etc).
    total_tracks = classification_results.shape[0]
    classification_rates = {f"Rate {label}": f"{(count / total_tracks) * 100:.2f}%" for label, count in classification_counts.items()}

    # Save classification results
    classification_results.to_csv(output_csv_path, index=False)
    print(f"[Classification] Saved refined results to {output_csv_path}")

    # Also save classification rates to a separate file
    rates_output_path = os.path.splitext(output_csv_path)[0] + "_rates.csv"
    pd.DataFrame([classification_rates]).to_csv(rates_output_path, index=False)
    print(f"[Classification] Saved classification rates to {rates_output_path}")

    # Display breakdown
    print("[Classification] Breakdown:")
    for label, rate in classification_rates.items():
        print(f"{label}: {rate}")

    annotated_data = pd.merge(merged_df, classification_results[['TRACK_ID', 'Classification']], on='TRACK_ID', how='left')

    frame_files = sorted(  # Sort frame images based on numeric order extracted from filenames.
        [f for f in os.listdir(original_frames_dir) if f.endswith((".tif", ".tiff"))],
        key=extract_last_number
    )

    if not frame_files:
        print("[Overlay] No valid TIFF frame files found. Skipping overlay generation.")
        return
    
    print(f"The frame number is: {frame_files}")

    min_frame_data = annotated_data['FRAME'].min()
    frame_offset = min_frame_data - 1
    print(f"\n[DEBUG] Using natural sort order for files.")
    print(f"[DEBUG] Applying frame offset: {frame_offset} (data FRAME - index)")


    for idx, file_name in enumerate(frame_files):
        frame = idx + 1
        adjusted_frame = frame + frame_offset  # Offset frame index if needed to align images with tracking data.

        frame_path = os.path.join(original_frames_dir, file_name)
        frame_tracks = annotated_data[annotated_data['FRAME'] == adjusted_frame]

        if frame_tracks.empty:
            print(f"[Overlay] Skipping frame {frame}: No tracks for adjusted frame {adjusted_frame}")
            continue

        if os.path.exists(frame_path):
            original_frame = Image.open(frame_path)
            dpi = 300
            original_array = np.array(original_frame)

            plt.figure(figsize=(10, 10), dpi=dpi)
            plt.imshow(original_array, cmap='gray', interpolation='nearest')

            for _, row in frame_tracks.iterrows():
                if not pd.isna(row['TRACK_ID']) and not pd.isna(row['POSITION_X']) and not pd.isna(row['POSITION_Y']):
                    x, y = row['POSITION_X'], row['POSITION_Y']
                    plt.text(x, y, f"{int(row['TRACK_ID'])}: {row['Classification']}",  # Draw classification and track ID labels on the frame images.
                            color=(1, 1, 1, 0.6), fontsize=4,
                            bbox=dict(facecolor='black', alpha=0.2, pad=0.2))

            plt.title(f"Frame {frame} (Data Frame: {adjusted_frame})", fontsize=10)
            plt.axis('off')

            overlay_path = os.path.join(output_overlay_dir, f"{os.path.splitext(file_name)[0]}_overlay.png")
            plt.savefig(overlay_path, bbox_inches='tight', pad_inches=0, dpi=dpi)
            plt.close()
            print(f"[✓] Overlay saved for {file_name}")
        else:
            print(f"[Overlay] Frame not found: {frame_path}")
