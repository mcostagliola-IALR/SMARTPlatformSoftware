import numpy as np
import cv2 as cv
import customtkinter as ctk
import os
from natsort import natsorted
import re
import datetime

def TRACKMOTION(img_folder: str, delete_bin_files: bool = False, max_features: int = 60):
    """
    Track motion in a sequence of images and save the motion features to CSV files.
    Periodically detects new features to add to existing tracked points, helping
    capture motion from new leaves appearing later in the sequence.
    Also shows motion vectors as arrows.

    Parameters:
        img_folder (str): Path to folder containing images or 'processed_images' subfolder.
        delete_bin_files (bool): Not used here.
        max_features (int): Maximum number of features to track. Default is 200.

    Returns:
        tuple: (output_dir, overall_datetimes_agg)
    """
    output_dir = None
    overall_datetimes_agg = []

    is_processed_images_folder = os.path.basename(img_folder) == 'processed_images'

    if is_processed_images_folder:
        parent_dir = os.path.dirname(img_folder)
        num_ext = 1
        existing_motion_dirs = []
        try:
            for item in os.listdir(parent_dir):
                if os.path.isdir(os.path.join(parent_dir, item)):
                    match = re.match(r'motion_features_(\d+)', item)
                    if match:
                        existing_motion_dirs.append(int(match.group(1)))
        except Exception as e:
            print(f"ERROR listing directory {parent_dir}: {e}")

        if existing_motion_dirs:
            num_ext = max(existing_motion_dirs) + 1
        output_dir = os.path.join(parent_dir, f'motion_features_{num_ext}')
        os.makedirs(output_dir, exist_ok=True)
    else:
        output_dir = os.path.join(img_folder, 'motion_features')
        os.makedirs(output_dir, exist_ok=True)
        img_folder = os.path.join(img_folder, 'processed_images')

    if not os.path.isdir(img_folder):
        raise FileNotFoundError(f"Image folder not found: {img_folder}")

    img_lst = [
        os.path.normpath(os.path.join(img_folder, f))
        for f in os.listdir(img_folder)
        if os.path.isfile(os.path.join(img_folder, f)) and f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ]
    img_lst = natsorted(img_lst)

    if len(img_lst) < 2:
        raise ValueError(f"Need at least two images in {img_folder}. Found {len(img_lst)}")

    # Optical flow params and colors
    feature_params = dict(maxCorners=min(140, max_features), qualityLevel=0.0007, 
                         minDistance=7, blockSize=4)
    lk_params = dict(winSize=(15, 15), maxLevel=2,
                     criteria=(cv.TERM_CRITERIA_EPS | cv.TERM_CRITERIA_COUNT, 10, 0.03))
    color = np.random.randint(0, 255, (500, 3))

    # Read first frame grayscale
    old_frame = cv.imread(img_lst[0], cv.IMREAD_GRAYSCALE)
    if old_frame is None:
        raise IOError(f"Could not read first image: {img_lst[0]}")

    old_gray = old_frame if len(old_frame.shape) < 3 else cv.cvtColor(old_frame, cv.COLOR_BGR2GRAY)

    def extract_datetime(filename):
        try:
            match = re.search(r'(\d{2}-\d{2}-\d{4})_(\d{2}-\d{2}-\d{2})', filename)
            if match:
                dt_obj = datetime.datetime.strptime(f"{match.group(1)}_{match.group(2)}", "%m-%d-%Y_%H-%M-%S")
                return dt_obj.strftime("%m/%d/%Y %H:%M:%S")
            else:
                base = filename.split("-Rep")[0]
                date_part, time_part = base.split("_")
                dt_obj = datetime.datetime.strptime(date_part, "%m-%d-%Y")
                return dt_obj.strftime("%m/%d/%Y") + " " + time_part.replace("-", ":")
        except Exception:
            return filename

    overall_datetimes_agg.append(extract_datetime(os.path.basename(img_lst[0])))

    p0 = cv.goodFeaturesToTrack(old_gray, mask=None, **feature_params)
    if p0 is None:
        p0 = np.empty((0, 1, 2), dtype=np.float32)
        feature_ids = []
        print(f"WARNING: No features detected in first image.")
    else:
        feature_ids = list(range(len(p0)))

    mask = np.zeros_like(cv.cvtColor(old_frame, cv.COLOR_GRAY2BGR) if len(old_frame.shape) < 3 else old_frame)

    fade_trails = True
    fade_alpha = 0.1

    frames = []
    max_feature_id = max(feature_ids) if feature_ids else -1

    feature_refresh_interval = 300

    for frame_idx, img_path in enumerate(img_lst[1:], start=1):
        frame = cv.imread(img_path, cv.IMREAD_GRAYSCALE)
        if frame is None:
            print(f"WARNING: Cannot read image {img_path}. Skipping.")
            overall_datetimes_agg.append(extract_datetime(os.path.basename(img_path)))
            continue

        frame_display = cv.cvtColor(frame, cv.COLOR_GRAY2BGR) if len(frame.shape) < 3 else frame
        frame_gray = frame

        if p0 is not None and len(p0) > 0:
            p1, st, err = cv.calcOpticalFlowPyrLK(old_gray, frame_gray, p0, None, **lk_params)
            if p1 is not None:
                st = st.flatten()
                good_new = p1[st == 1]
                good_old = p0[st == 1]
                good_ids = [fid for fid, alive in zip(feature_ids, st) if alive == 1]

                filename = os.path.basename(img_path)
                file_datetime_str = extract_datetime(filename)
                rep = ""
                rep_match = re.search(r'-Rep(\d+)', filename)
                if rep_match:
                    rep = rep_match.group(1)

                for new_pt, old_pt, fid in zip(good_new, good_old, good_ids):
                    a, b = new_pt.ravel()
                    c, d = old_pt.ravel()
                    with open(os.path.join(output_dir, f"feature_{fid}.csv"), "a") as f:
                        f.write(f"{a},{b},{file_datetime_str},{rep}\n")

                    # Draw line trails (your existing style)
                    mask = cv.line(mask, (int(a), int(b)), (int(c), int(d)), color[fid % len(color)].tolist(), 2)
                    # Draw circles on points
                    frame_display = cv.circle(frame_display, (int(a), int(b)), 5, color[fid % len(color)].tolist(), -1)

                    # **Draw arrowed vector for motion**
                    # Adjust thickness and tip length for visibility
                    cv.arrowedLine(frame_display, (int(c), int(d)), (int(a), int(b)), color[fid % len(color)].tolist(), 2, tipLength=0.3)

                p0 = good_new.reshape(-1, 1, 2)
                feature_ids = good_ids
            else:
                p0 = np.empty((0,1,2), dtype=np.float32)
                feature_ids = []
                print(f"No features tracked in {img_path}.")
        else:
            print(f"No features to track in {img_path}.")
            p0 = np.empty((0,1,2), dtype=np.float32)
            feature_ids = []

        if frame_idx % feature_refresh_interval == 0:
            current_feature_count = len(p0) if p0 is not None else 0
            
            # Only detect new features if under the limit
            if current_feature_count < max_features:
                remaining_slots = max_features - current_feature_count
                feature_params['maxCorners'] = remaining_slots
                
                new_feats = cv.goodFeaturesToTrack(frame_gray, mask=None, **feature_params)
                if new_feats is not None and len(new_feats) > 0:
                    existing_pts = p0.reshape(-1, 2) if len(p0) > 0 else np.empty((0, 2))
                    new_pts = new_feats.reshape(-1, 2)

                    min_dist = feature_params['minDistance']
                    filtered_new_pts = []
                    for pt in new_pts:
                        if len(existing_pts) == 0 or np.min(np.linalg.norm(existing_pts - pt, axis=1)) > min_dist:
                            filtered_new_pts.append(pt)
                            
                    if filtered_new_pts:
                        filtered_new_pts = np.array(filtered_new_pts).reshape(-1, 1, 2)
                        new_feature_ids = list(range(max_feature_id + 1, 
                                                   max_feature_id + 1 + len(filtered_new_pts)))
                        max_feature_id += len(filtered_new_pts)

                        if len(p0) == 0:
                            p0 = filtered_new_pts
                            feature_ids = new_feature_ids
                        else:
                            p0 = np.concatenate((p0, filtered_new_pts), axis=0)
                            feature_ids.extend(new_feature_ids)

                        print(f"Added {len(filtered_new_pts)} new features at frame {frame_idx}. "
                              f"Total features: {len(p0)}/{max_features}")
            else:
                print(f"Feature limit reached ({max_features}). Skipping feature detection.")

        overall_datetimes_agg.append(extract_datetime(os.path.basename(img_path)))

        if fade_trails:
            mask = cv.addWeighted(mask, 1 - fade_alpha, np.zeros_like(mask), 0, 0)

        img_display = cv.add(frame_display, mask)
        frames.append(img_display.copy())

        cv.imshow('frame', img_display)
        k = cv.waitKey(1) & 0xff
        if k == 27:
            break

        old_gray = frame_gray.copy()

    cv.destroyAllWindows()

    output_video_path = os.path.join(output_dir, 'PlantMotionFade.mp4')
    if frames:
        height, width, layers = frames[0].shape
        fourcc = cv.VideoWriter_fourcc(*'mp4v')
        video = cv.VideoWriter(output_video_path, fourcc, 24, (width, height))
        for frame in frames:
            video.write(frame)
        video.release()
        print(f"Motion video saved to: {output_video_path}")
    else:
        print("No frames captured, video not created.")

    summary_path = os.path.join(output_dir, "tracking_summary.txt")
    with open(summary_path, "w") as f:
        f.write(f"TRACKMOTION Summary\n")
        f.write(f"Frames processed: {len(img_lst)}\n")
        f.write(f"Unique feature IDs tracked: {max_feature_id + 1 if max_feature_id >= 0 else 0}\n")
        f.write(f"Datetimes collected: {len(overall_datetimes_agg)}\n")

    print(f"TRACKMOTION completed. Output directory: {output_dir}")
    print(f"Number of datetimes collected: {len(overall_datetimes_agg)}")

    overall_datetimes_agg = natsorted(list(set(overall_datetimes_agg)))

    return os.path.normpath(output_dir), overall_datetimes_agg

if __name__ == "__main__":
    pass