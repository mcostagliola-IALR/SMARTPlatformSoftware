from plantcv import plantcv as pcv
import numpy as np
import os
import cv2
import time
import pandas as pd
import re
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import filedialog, messagebox
def parse_filename(path):
    """Parses filename to extract date, time, and repetition number."""
    try:
        base = os.path.splitext(os.path.basename(path))[0]
        match = re.match(r"(\d{2}-\d{2}-\d{4})_(\d{2}-\d{2})-Rep(\d+)", base)
        if not match:
            raise ValueError("Filename format mismatch")
        date_str, time_str, rep = match.groups()
        file_date = time.strftime("%m/%d/%Y", time.strptime(date_str, "%m-%d-%Y"))
        file_time = time_str.replace("-", ":")
        return f"{file_date} {file_time}", rep
    except Exception as e:
        print(f"Filename parsing failed for '{path}': {e}")
        return "", ""

def process_image(img_path, out_dir):
    """Processes a single image: applies CLAHE, thresholds, performs morphological operations, and extracts size."""
    try:
        # Read image using OpenCV for direct use with cv2 functions
        img = cv2.imread(img_path)
        if img is None:
            raise ValueError(f"Failed to read image: {img_path}")

        # Apply CLAHE for contrast enhancement
        # Convert BGR to LAB color space
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2Lab)
        # Split the LAB image into L, A, and B channels
        l_channel, a_channel, b_channel = cv2.split(lab)

        # Apply CLAHE to the L-channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl_l_channel = clahe.apply(l_channel)

        # Merge the enhanced L-channel back with the original A and B channels
        merged_lab = cv2.merge([cl_l_channel, a_channel, b_channel])
        # Convert back to BGR
        output_enhanced = cv2.cvtColor(merged_lab, cv2.COLOR_Lab2BGR)

        # Convert to grayscale 'a' channel as in the original PlantCV code for thresholding
        # PlantCV's rgb2gray_lab('a') effectively takes the 'a' channel directly.
        # We need to ensure output_enhanced is in a format PlantCV expects or convert it.
        # Since we are using cv2, let's explicitly get the 'a' channel from the LAB converted 'output_enhanced'
        # Convert BGR to LAB again for consistency with original 'a' channel logic
        lab_for_a = cv2.cvtColor(output_enhanced, cv2.COLOR_BGR2Lab)
        lab_a_channel = lab_for_a[:, :, 1] # 'a' channel is the second channel (index 1) in LAB

        # Otsu thresholding
        # Ensure PlantCV is correctly used or replace with cv2 equivalent if direct conversion is better.
        # pcv.threshold.otsu expects a grayscale image.
        # Since lab_a_channel is already grayscale, we can pass it directly.
        binl = pcv.threshold.otsu(gray_img=lab_a_channel, object_type='dark')

                # Morphological operations
        # Step 1: Slightly stronger closing to seal gaps inside plant regions
        kernel_close = np.array([[0, 1, 1, 1, 0],
                                 [1, 1, 1, 1, 1],
                                 [1, 1, 1, 1, 1],
                                 [1, 1, 1, 1, 1],
                                 [0, 1, 1, 1, 0]], dtype=np.uint8)

        closed = pcv.closing(gray_img=binl, kernel=kernel_close)

        # Step 2: Fill internal holes up to a larger size
        # Increased from 50 -> 500 to capture small leaf gaps
        filled = pcv.fill(closed, 85)

        # Step 3: Very light opening to remove isolated noise
        kernel_open = np.array([[0, 1, 0],
                                [1, 1, 1],
                                [0, 1, 0]], dtype=np.uint8)

        clean_mask = pcv.opening(filled, kernel=kernel_open)

        size = np.count_nonzero(clean_mask)

        # Parse filename for metadata
        file_name, rep = parse_filename(img_path)

        # Save binary mask
        out_file_path = os.path.join(out_dir, os.path.basename(img_path))
        # PlantCV's print_image saves the image.
        pcv.print_image(clean_mask, out_file_path)

        return [file_name, rep, size]
    except Exception as e:
        print(f"Error processing {img_path}: {e}")
        return ["", "", 0]

def RGB2BIN(inDirectoryPath: str) -> str:
    """
    Processes RGB images in a directory, converts them to binary masks,
    and saves mask sizes to an Excel file.
    """
    start_time = time.time()

    outDirectoryPath = os.path.join(inDirectoryPath, 'processed_images')
    os.makedirs(outDirectoryPath, exist_ok=True)

    print(f'In Path: {inDirectoryPath}\nOut Path: {outDirectoryPath}')

    # Get all image files in the directory
    extensions = ('.jpg', '.png')
    image_files = [os.path.join(inDirectoryPath, f) for f in os.listdir(inDirectoryPath)
                   if f.lower().endswith(extensions) and os.path.isfile(os.path.join(inDirectoryPath, f))]

    if not image_files:
        print(f"No image files found in {inDirectoryPath} with extensions {extensions}")
        return outDirectoryPath

    print(f"Found {len(image_files)} images to process. Processing images...")

    # Use ThreadPoolExecutor for parallel processing
    # Adjust max_workers based on your CPU cores and available memory
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        # map returns results in the order the tasks were submitted
        results = list(executor.map(lambda f: process_image(f, outDirectoryPath), image_files))

    # Filter out any failed processing results (where file_name is empty)
    valid_results = [res for res in results if res[0] != ""]

    # Convert data to DataFrame
    df = pd.DataFrame(valid_results, columns=["datetime", "rep", "size"])
    excel_path = os.path.join(inDirectoryPath, "mask_sizes.xlsx")
    df.to_excel(excel_path, index=False)

    print(f"Data written to Excel: {excel_path}")
    print(f"Total processing time: {time.time() - start_time:.2f} seconds")

    return outDirectoryPath

if __name__ == "__main__":

    # Hide the main tkinter window
    root = tk.Tk()
    root.withdraw()

    # Open folder picker
    folder_path = filedialog.askdirectory(
        title="Select Image Folder to Process"
    )

    if folder_path:
        try:
            print(f"Selected folder: {folder_path}")

            output = RGB2BIN(folder_path)

            messagebox.showinfo(
                "Processing Complete",
                f"Processing finished successfully.\n\nOutput:\n{output}"
            )

        except Exception as e:
            messagebox.showerror(
                "Processing Error",
                str(e)
            )

    else:
        print("No folder selected.")