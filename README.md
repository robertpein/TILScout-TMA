# TILScout-TMA

TILScout adapted to H&E-stained tissue microarray (TMA) cores.

[TILScout](https://github.com/huibozh/TILScout) (Zhang et al. 2025) classifies 150 × 150-pixel patches of H&E-stained whole slide images as TIL-positive, TIL-negative or non-tumor with a pre-trained InceptionResNetV2 model and calculates a TIL score for each image. Its script `TILscout.py` reads whole slide images with OpenSlide. This repository adapts the script to TMA cores exported as untiled `.tif` images and contains the QuPath script used to export the cores.

**Only the patch generation was changed.** The pre-trained model, the stain normalization, the prediction, the TIL score and the TIL maps are those of the original script.

Related article: Pein RJ, Illyés I, Anders FD, Kenessey I, Pesti A, Kiss A, Borka K. Deep learning-based tumor-infiltrating lymphocyte scoring on H&E-stained tissue microarrays and overall survival in ampullary carcinoma. *Virchows Archiv* (under revision).

## What was changed

Each core image is read with OpenCV and divided into non-overlapping 150 × 150-pixel patches, starting at the top-left corner; incomplete patches at the right and lower edge are skipped. In the original, OpenSlide's `DeepZoomGenerator` divides whole slide images into 150 × 150-pixel tiles at 20×. The tissue filter (mean pixel value < 230 and standard deviation > 15), the Macenko normalization (`norm_HnE(Io=240, alpha=1, beta=0.15)`) and the naming of the patch files are unchanged.

| Line(s) in the original `TILscout.py` (commit `470419a`) | Change |
|---|---|
| 10 | `import openslide` → `import cv2` |
| 13 | `from openslide.deepzoom import DeepZoomGenerator` deleted |
| 33–74 | `process_image` and `process_tile` replaced by a new `process_image` for `.tif` images |
| 79 | `"*.svs"` → `"*.tif"` |

All changes are shown line by line in [`changes_vs_original.diff`](changes_vs_original.diff).

## Requirements

- Python 3.9 (3.9.15 was used)
- The packages in [`requirements.txt`](requirements.txt). OpenSlide is not needed. NumPy must be older than 1.24, because `normalize_HnE.py` uses `np.float`.

## Setup

1. Clone this repository.
2. Copy `normalize_HnE.py` and the pre-trained model `best_InceptionResNetV2_model.h5` (228 MB, stored with Git LFS) from the [original TILScout repository](https://github.com/huibozh/TILScout) into the same folder. Both are used unchanged and are not included here.

   ```bash
   git lfs install
   git clone https://github.com/huibozh/TILScout.git
   cp TILScout/normalize_HnE.py TILScout/best_InceptionResNetV2_model.h5 .
   ```

3. Install the packages:

   ```bash
   pip install -r requirements.txt
   ```

## Input

Place one RGB `.tif` image per core in `WSI_example/`. The images should have a resolution of about 0.5 µm/pixel, so that a patch covers about 75 × 75 µm. We scanned the TMA slides at 40× (about 0.25 µm/pixel) on a Pannoramic 1000 scanner (3DHISTECH), dearrayed them in QuPath 0.6.0 and exported each core with [`export_tma_cores.groovy`](export_tma_cores.groovy) at a downsample of 2 (about 0.5 µm/pixel; 4640 × 4640 pixels per core).

Use only cores that contain tumor. As in the original script, the run stops with a division by zero if an image has neither a TIL-positive nor a TIL-negative patch.

## Run

```bash
python TILscout_TMA.py
```

## Output

| File | Content |
|---|---|
| `results/<core>_TIL_score.txt` | TIL score of the core |
| `results/<core>_TIL_map.pdf` | Patch classification map (purple, TIL-positive; red, TIL-negative; pink, non-tumor) |
| `tile_processing.log` | Log of saved and skipped patches |

The temporary patch folder `patch/` is deleted at the end of the run, as in the original.

## Credits

TILScout: Zhang H, Chen L, Li L, Liu Y, Das B, Zhai S, Tan J, Jiang Y, Turco S, Yao Y, Frishman D (2025) Prediction and analysis of tumor infiltrating lymphocytes across 28 cancers by TILScout using deep learning. *NPJ Precis Oncol* 9:76. https://doi.org/10.1038/s41698-025-00866-0

The original repository states that TILScout is freely available for non-commercial academic research. The same applies to this adaptation.
