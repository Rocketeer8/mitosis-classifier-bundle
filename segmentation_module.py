import os
import re
import numpy as np
from tifffile import imread, imwrite
from cellpose import models
import random
from typing import List

# Initialize Cellpose model globally (GPU optional)
model = models.CellposeModel(model_type='livecell_cp3', gpu=True)

def ensure_directory_exists(directory: str) -> None:
    os.makedirs(directory, exist_ok=True)

def normalize_to_16bit(image: np.ndarray) -> np.ndarray:
    min_val, max_val = np.min(image), np.max(image)
    if max_val > min_val:
        return ((image - min_val) / (max_val - min_val) * 65535).astype(np.uint16)
    return np.zeros_like(image, dtype=np.uint16)

def natural_sort_key(s):
    """Sort strings by natural order (e.g., 1, 2, 10 instead of 1, 10, 2)"""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def extract_frames(tiff_path: str, output_dir: str) -> List[str]:
    ensure_directory_exists(output_dir)
    frames = imread(tiff_path)
    frame_paths = []

    for idx, frame in enumerate(frames):
        frame_number = idx + 1
        output_path = os.path.join(output_dir, f"frame_{frame_number}.tif")
        imwrite(output_path, normalize_to_16bit(frame))
        frame_paths.append(output_path)
        print(f"[Segmentation] Saved frame: {output_path}")

    return frame_paths

def apply_unique_colors(masks: np.ndarray) -> np.ndarray:
    color_mask = np.zeros((*masks.shape, 3), dtype=np.uint8)
    for label in np.unique(masks[masks > 0]):
        color_mask[masks == label] = [random.randint(50, 255) for _ in range(3)]
    return color_mask

def convert_rgb_to_16bit_grayscale(rgb_image: np.ndarray) -> np.ndarray:
    grayscale = np.dot(rgb_image[..., :3], [0.299, 0.587, 0.114])
    return normalize_to_16bit(grayscale)

def segment_frame(frame_path: str, output_dir: str) -> None:
    img = imread(frame_path)
    masks, _, _ = model.eval(img)

    color_mask = apply_unique_colors(masks)
    grayscale_mask = convert_rgb_to_16bit_grayscale(color_mask)

    # Extract frame number from filename
    match = re.search(r'frame_(\d+)', os.path.basename(frame_path))
    frame_number = match.group(1) if match else 'unknown'

    output_path = os.path.join(output_dir, f"frame_{frame_number}_mask.tif")
    imwrite(output_path, grayscale_mask)
    print(f"[Segmentation] Saved grayscale mask: {output_path}")

def segment_frames(input_path_or_dir: str, output_dir: str) -> None:
    ensure_directory_exists(output_dir)

    if input_path_or_dir.lower().endswith((".tif", ".tiff")):
        frame_paths = extract_frames(input_path_or_dir, output_dir)
    else:
        frame_paths = sorted(
            [os.path.join(input_path_or_dir, f)
             for f in os.listdir(input_path_or_dir)
             if f.endswith((".tif", ".tiff"))],
            key=natural_sort_key
        )

    for frame_path in frame_paths:
        segment_frame(frame_path, output_dir)
