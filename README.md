# AnaVerse 2.0 – Hackathon Submission

A practical, notebook-first machine learning solution for **anomaly detection** on tabular sensor data.

This repository contains the final competition notebook used to:
- clean and validate the data,
- engineer robust row-level and extreme-value features,
- train an ensemble of gradient boosting models,
- optimize thresholds for better F1 score,
- and generate submission files.

## What's inside

- `final-submission-anaverse-2-0.ipynb` — end-to-end pipeline from data loading to final submission export.

## Approach (short version)

1. **Data preparation**: basic cleaning + safe transformations.
2. **Leakage and distribution checks**: train/test diagnostics before modeling.
3. **Feature engineering**:
   - extreme-value indicator flags,
   - row-wise statistical features.
4. **Modeling**: blended ensemble of **LightGBM**, **CatBoost**, and **XGBoost**.
5. **F1-focused thresholding**: probability cutoffs tuned for class imbalance.

## How to run

1. Open the notebook in **Kaggle** or a local Jupyter environment.
2. Make sure input files are available (the current notebook expects Kaggle-style paths).
3. Run cells top-to-bottom.
4. Retrieve the generated submission CSV(s).

## Dependencies

The notebook uses common Python ML libraries, including:
- `numpy`, `pandas`, `scikit-learn`
- `lightgbm`, `catboost`, `xgboost`
- `matplotlib`, `scipy`

> Some dependencies are installed directly inside notebook cells (`pip install ...`).

## Notes

- This repo currently stores the final submission notebook as the main artifact.
- If helpful, we can later add:
  - a reproducible `requirements.txt`,
  - a cleaner script-based pipeline,
  - and a short experiment/results summary.

---
