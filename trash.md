prepare_extractor_data.py

- find_zone_code_spans() - does it make sense to use EXCLUDED_WORDS list?

what's the input to the extractor model in the test phase? - entire zoning ordinance text or filtered zoning ordinance text? provided as chunks or as whole?


modify the dashboard to clearly show the ground truth labels (BIO-tagged labels that might not be in the zoneomics csv but identified by regex) in addition to the actual codes (zoneomics) and the predicted labels for a city, to assess the performance of the extractor











extractor model - it's job is to identify zoning code candidates (strings that seem like codes) from input text







we have ordinance files (docx) & zoning codes (csv) for each city
convert docx files to md

(assuming we have aligned the zoneomics and municode files - to use common cities)
prepare the data for training the extractor model
- for each city
    - load the zoning codes from zoneomics csv
    - for each code
        - extract the places where that code appears in the city's ordinance md
        - create context windows (-500 chars, +500 chars) around the identified code location
        - identify zoning code-looking strings using regex - REMOVE!!!!!
        - create BIO tagged labels for the context chunk, add city & state as metadata
















change prepare_data_extractor
- only tag BIO to the codes that are present in zoneomics csv; do not use regex
















------------------------------------------

for validator data creation, do this (remove hard negatives) -

so why not do it like this?
instead of using hard negatives,
split the cities into train_extractor, train_validator, test.
train the extractor on train_extractor cities.
train the validator on train_validator cities where positive examples come from zoneomics and negative examples come from false positives on the train_extractor set by extractor model.
and then test the performance on test?

------------------------------------------

Yes, that's a solid alternative approach, and it aligns closely with best practices for cascaded ML pipelines (like extractor → validator) where you want the downstream model to learn from realistic upstream errors on unseen data. It could potentially improve the validator's generalization by providing more diverse, extractor-specific negatives during training without the risks of bias or leakage. However, the current script's design isn't doing it this way for a few practical and principled reasons—it's a trade-off between simplicity, data efficiency, and evaluation integrity. I'll break it down step-by-step, comparing your proposal to the script's implementation, and explain why the script opts for hard negatives in the validator's train set instead.
1. Understanding Your Proposed Approach

Splits: Divide cities into three disjoint sets:
train_extractor: Used to train the extractor model (e.g., 60-70% of cities).
train_validator: Held-out from extractor training; used to train the validator with positives (CSV-grounded zone codes from those cities' ordinances) + negatives (extractor FPs run on those cities' texts).
test: Fully held-out for final evaluation of the full pipeline (extractor predictions → validator filtering).

Training Flow:
Train extractor on train_extractor.
Run the trained extractor on train_validator cities to generate FPs (as negatives) + use CSVs for positives → train validator.
No hard negatives needed, as extractor FPs provide realistic negatives.

Evaluation: Run extractor on test cities, then validator on its outputs; measure end-to-end metrics (e.g., precision/recall for valid zone codes).
Key Benefit: Validator trains directly on the types of errors the extractor makes on unseen data (train_validator acts as a "proxy" for test), making training more aligned with deployment.

This is essentially a form of "staged holdout" or internal cross-validation, ensuring the validator sees authentic, generalized FPs during training.