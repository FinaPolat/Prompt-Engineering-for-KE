Evaluation Module
===============================

This documentation provides an overview of the evaluation sub-modules and instructions for running the various scripts with their respective default values.

The Evaluation module comprises two distinct sub-modules for assessing different aspects of the extraction:

Sub-module 1: Evaluation of Reference to Annotations
-----------------------------------------------------
This sub-module calculates the precision, recall, and F1-score for your model's outputs.

Repository:

`evaluation_reference_to_annotations`

Script:

  `evaluate.py`

Usage:

```
  python 3_evaluation_module/evaluation_reference_to_annotations/evaluate.py --input_dir <input_directory> --gold_file <gold_standard_file> --out_dir <output_directory>
```

Default Values:

  `--input_dir: 2_inference_module/postprocessed_outputs/post_processed_{model_name}`
  
  `--gold_file: 1_data_module/1_data_preprocessing/RED-fm/test.jsonl`
  
  `--out_dir: {model_name}_evaluation_results`


Sub-module 2: Evaluation Reference to Wikidata
----------------------------------------------
This sub-module analyzes generated triples in reference to Wikidata.

Repository:

  `3_evaluation_module/evaluation_reference_to_Wikidata`

Script:

  `wikidata_analysis.py`

Usage:

  ```
  python 3_evaluation_module/evaluation_reference_to_Wikidata/wikidata_analysis.py --input_dir <input_directory> --gold_file <gold_standard_file> --out_dir <output_directory>
```

Default Values:

  `--input_dir: 2_inference_module/postprocessed_outputs/post_processed_{model_name}`
  
  `--gold_file: 1_data_module/1_data_preprocessing/RED-fm/test.jsonl`
  
  `--out_dir: 3_evaluation_module/evaluation_reference_to_Wikidata/{evaluation_date}_evaluation_{model_name}`

----------------------------------------------
Results Storage: 

Wikidata analysis results are stored in three sub-directories:

1. extracted_relations_and_entities
2. results
3. triples

----------------------------------------------
Additional Analysis Scripts:

* Entity and Relation Linking Rates:

To calculate the entity and relation linking rates, run:

```
python 3_evaluation_module/evaluation_reference_to_Wikidata/count_linked_items.py --input_dir <input_directory>
```

* Domain and Range Annotation Check:

To verify if relations have domain and range annotations in Wikidata, run:

```
python 3_evaluation_module/evaluation_reference_to_Wikidata/get_domain_range_info.py --input_dir <input_directory>
```

Default input_dir:

`3_evaluation_module/evaluation_reference_to_Wikidata/{evaluation_date}_evaluation_{model_name}/extracted_relations_and_entities`
