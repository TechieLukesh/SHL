## How dataset.xlsx is used

`dataset.xlsx` contains:

- A labeled train set (~10 queries) used purely for validation and pipeline iteration.
- An unlabeled test set (~9 queries) used to generate final predictions.

**Process**

1. Parse the workbook with `python data/parse_dataset.py` → produces `data/train.json` and `data/test.json`.
2. Validate and iterate the recommender using `python evaluate.py` — this computes precision@5 and MRR on the labeled set.
3. Generate final submission for the test set with `python predict_test.py` → outputs `data/test_predictions.csv` and `data/test_predictions.json`.

**Important**: The SHL catalog (`shl_assessments.json`) is the source of truth for recommendations. `dataset.xlsx` is only used for validation & final submission, as required by the assessment instructions.
