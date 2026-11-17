# ML Training and Runtime Verification

Audit date: 2026-11-17

## Artifact/runtime verification

- The supplied pair dataset exists at `data/student_job_pairs_rebuilt.csv` (437,541,455 bytes). A streaming scan found 799,020 rows and 79,902 distinct students.
- Its supplied target is `suitability_label_synthetic`: 735,306 rows labelled 0 and 63,714 labelled 1. The target-generation formula is absent from the project, so it cannot be verified as a real hiring or placement outcome.
- The saved classifiers are `decision_tree.pkl`, `best_random_forest.pkl`, `svm.pkl`, `knn.pkl`, and `naive_bayes.pkl`. They implement alternative algorithms for the same binary synthetic target: Decision Tree, Random Forest, SVM, KNN, and Gaussian Naive Bayes.
- The Flask model registry loaded all five estimators, training medians, scaler, and the exact 20-field feature configuration with `ready=true` and no load errors. Integration tests invoked each estimator independently.
- Saved training metadata describes a 20,000-row maximum sample, a student-grouped 80/20 holdout (15,994 train / 4,006 test in this artifact), and training-only grouped cross-validation. All artifact prediction-parity flags in the saved configuration are true. This audit did not rerun training or reproduce the held-out scores.
- Inference uses `train_medians.pkl` to replace missing numeric values, followed by `standard_scaler.pkl`. Category inputs use the configured one-hot fields and baseline categories CSE, Business Analyst, and Hybrid. Runtime array construction follows the configured feature order. `median_imputer.pkl` is an additional artifact not loaded by current `ModelRegistry` code.

## Recorded metrics and interpretation

| Classifier | Accuracy | Suitable precision | Suitable recall | Suitable F1 |
|---|---:|---:|---:|---:|
| Decision Tree | 64.63% | 17.53% | 92.50% | 29.47% |
| Random Forest | 71.17% | 18.15% | 74.38% | 29.18% |
| SVM (selected) | 66.23% | 18.14% | 91.88% | 30.29% |
| KNN | 91.19% | 33.98% | 10.94% | 16.55% |
| Gaussian Naive Bayes | 81.43% | 15.13% | 28.75% | 19.83% |

The labels are imbalanced and synthetic. The SVM's 18.14% suitable-class precision and the other model-specific figures measure agreement with that supplied label only. They are not calibrated placement probabilities, verified employment outcomes, or hiring recommendations.

## Training source and limits

`notebooks/final colab.ipynb` and its exported `notebooks/final colab.py` are Colab-generated. The Python export imports `google.colab` and reads `/content/student_job_pairs_rebuilt.csv`; it is not a verified standalone local command. The actual project CSV is in `data/`. No models were retrained or overwritten during this audit, as requested.

The model/data/export workflow can be inspected in the notebook and Python export. It defines Decision Tree, tuned Random Forest, RBF SVM, 5-neighbor KNN, and GaussianNB, uses grouped student splits, median imputation plus scaling, and exports the selected artifacts. Since the target recipe is missing, target leakage/construct validity cannot be fully established even though target proxies are excluded from the configured model features.

## New student inference path

Student CRUD only validates and persists profile values; registration does not retrain or automatically run inference. Match Workspace loads the selected student and job, includes their database record IDs and current submitted fields, then calls `/api/analyze` with `request_prediction=true` and the selected algorithm. Flask rebuilds all 20 features, applies saved medians/scaler and the selected pickle, returns the actual model output, and persists the output with the input snapshot in `analyses`. The React workspace renders that response. A two-student integration test verified that record IDs, skills, CGPA values, predictions, and histories remained separated, including retrieval after a fresh Flask process.
