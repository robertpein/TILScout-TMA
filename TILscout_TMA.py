# -*- coding: utf-8 -*-
"""
TILScout
@author: Huibo Zhang

Adapted to untiled .tif images of tissue microarray cores: only the patch
generation differs from the original TILscout.py
(https://github.com/huibozh/TILScout, commit 470419a). See README.md.
"""

"""
### patch generation
"""
import cv2
import numpy as np
import tifffile as tiff
import os
import glob
import concurrent.futures
from normalize_HnE import norm_HnE
import logging

# Define constants
IMG_WIDTH = 224
IMG_HEIGHT = 224
IMG_CHANNELS = 3
SIZE = 224  
BATCH_SIZE = 1000  
NUM_THREADS = 1

# Define results folder path
results_path = os.path.abspath("./results")
if not os.path.exists(results_path):
    os.makedirs(results_path)

# Patch size (150 x 150 pixels, as in the original)
TILE_SIZE = 150

logging.basicConfig(
    level=logging.INFO,
    filename='tile_processing.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def process_image(file_path, patch_root, tile_size=TILE_SIZE, stride=None):
    label = os.path.basename(file_path)
    print("Processing:", label)

    out_dir = os.path.join(patch_root, os.path.splitext(label)[0])
    os.makedirs(out_dir, exist_ok=True)

    img = cv2.imread(file_path, cv2.IMREAD_COLOR)
    if img is None:
        print(f"Error reading image at {file_path}")
        logging.error(f"Error reading image at {file_path}")
        return

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    H, W, _ = img_rgb.shape
    if stride is None:
        stride = tile_size

    cols = (W - tile_size) // stride + 1 if W >= tile_size else 0
    rows = (H - tile_size) // stride + 1 if H >= tile_size else 0

    if cols == 0 or rows == 0:
        print(f"Image too small for tiling ({W}x{H})")
        logging.warning(f"Image too small for tiling ({W}x{H})")
        return

    for row in range(rows):
        for col in range(cols):
            y0 = row * stride
            x0 = col * stride
            tile = img_rgb[y0:y0+tile_size, x0:x0+tile_size, :]

            if tile.shape[0] != tile_size or tile.shape[1] != tile_size:
                continue

            try:
                if tile.mean() < 230 and tile.std() > 15:
                    norm_img, _, _ = norm_HnE(tile, Io=240, alpha=1, beta=0.15)
                    tile_name = f"{col}_{row}_{label[:23]}_norm.tif"
                    tiff.imwrite(os.path.join(out_dir, tile_name), norm_img)
                    logging.info(f"Saved tile {tile_name}")
                else:
                    logging.info(f"Skipping blank tile col={col}, row={row}")
            except Exception as e:
                logging.error(f"Error processing tile {col},{row}: {str(e)}")

patch_path = os.path.abspath("./patch") #Create a temporary folder ./patch for storing patches
if not os.path.exists(patch_path):
    os.makedirs(patch_path)
directory_paths = glob.glob(os.path.join("WSI_example", "*.tif"))

with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
    futures = [executor.submit(process_image, path, patch_path) for path in directory_paths]
    concurrent.futures.wait(futures)



"""
### patch prediction and TIL score calculation
"""
import cv2
from tensorflow import keras
import pandas as pd
import gc
from concurrent.futures import ThreadPoolExecutor

SIZE = 224  
BATCH_SIZE = 1000  
NUM_THREADS = 1

# Load model
prediction_model = keras.models.load_model('best_InceptionResNetV2_model.h5')

def process_directory(directory_path):
    label = os.path.basename(directory_path)
    img_paths = glob.glob(os.path.join(directory_path, "*.tif"))
    num_images = len(img_paths)
    num_batches = np.ceil(num_images / BATCH_SIZE).astype(int)
    pred_ID, Y_proba = pd.DataFrame(), pd.DataFrame()

    for batch in range(num_batches):
        batch_img_paths = img_paths[batch * BATCH_SIZE: min((batch + 1) * BATCH_SIZE, num_images)]
        pred_images = [cv2.cvtColor(cv2.resize(cv2.imread(img_path, cv2.IMREAD_COLOR), (SIZE, SIZE)), cv2.COLOR_BGR2RGB) for img_path in batch_img_paths]
        X_pred = np.array(pred_images) / 255.0

        # Perform prediction
        y_proba = prediction_model.predict(X_pred)
        batch_pred_ID = pd.DataFrame(batch_img_paths, columns=['Patch_id'])
        batch_Y_proba = pd.DataFrame(y_proba, columns=['Positive', 'Negative', 'Other'])

        pred_ID = pd.concat([pred_ID, batch_pred_ID], ignore_index=True)
        Y_proba = pd.concat([Y_proba, batch_Y_proba], ignore_index=True)

        del pred_images, X_pred
        gc.collect()

    # Combine results
    results = pd.concat([pred_ID, Y_proba], axis=1)
    results['MaxCategory'] = results[['Positive', 'Negative', 'Other']].idxmax(axis=1)
    results['Coordinates'] = results['Patch_id'].str.extract(r'(\d+_\d+)')
    results[['X', 'Y']] = results['Coordinates'].str.split('_', expand=True).astype(int)
    
    # Calculate TIL scores
    TIL_positive = results[results["Positive"] > results[["Negative", "Other"]].max(axis=1)]
    TIL_negative = results[results["Negative"] > results[["Positive", "Other"]].max(axis=1)]
    #Other = results[results["Other"] > results[["Positive", "Negative"]].max(axis=1)]

    score = TIL_positive.shape[0] / (TIL_negative.shape[0] + TIL_positive.shape[0])
    result_text = f"{label}: TIL Score = {score:.4f}"
    print(result_text)
    with open(os.path.join(results_path, f"{label}_TIL_score.txt"), 'w') as f:
        print(label, score, file=f)
    return results

# Processing all directories
with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
    directory_paths = glob.glob(os.path.join("patch", "*"))  
    results_list = list(executor.map(process_directory, directory_paths))



"""
### TIL map generation
"""
import matplotlib.pyplot as plt

def generate_til_maps(results_list):
    for results in results_list:
        draw_til_map(results)

def draw_til_map(results):
    # Extraction of the directory name
    first_path = results['Patch_id'].iloc[0]
    label1 = os.path.basename(os.path.dirname(first_path))
    #print("Generating TIL map for:", label1)
    colors = {'Negative': 'red', 'Positive': 'purple', 'Other': 'pink'}
    max_dims = results[['X', 'Y']].max()
    plt.figure(figsize=(max_dims['X']/7.1, max_dims['Y']/7.1))  # Adjust figure size dynamically

    for category, color in colors.items():
        category_data = results[results['MaxCategory'] == category]
        plt.scatter(x=category_data.X, y=category_data.Y, s=48, color=color, marker='s')

    plt.title(f"{label1} TIL Map", fontsize=max_dims['X']/7.1)  # Title size adjusts with figure size
    plt.gca().set_aspect('equal')
    plt.xlim(0, max_dims['X'] + 5)
    plt.ylim(max_dims['Y'] + 5, 0)
    plt.xticks([])
    plt.yticks([])
    plt.savefig(f"{results_path}/{label1}_TIL_map.pdf")
    plt.close()
    print("TIL map is generated and stored in the results directory for:", label1)
generate_til_maps(results_list)

#delete temporary folder patch
import shutil
patch_path = os.path.abspath("./patch")
shutil.rmtree(patch_path)


