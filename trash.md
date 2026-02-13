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