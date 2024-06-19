# Inference Module
==============================

This module contains scripts for running inference using the OpenAI API and LangChain Huggingface API.

Overview
--------
The data does not require further processing at this stage. The script reads prompts from the `1_data_module/2_creating_prompts/data_with_prompts` directory.

API Keys
--------
Both OpenAI and LangChain Huggingface API calls require API keys. Ensure that you replace placeholder values with your own API keys.

Running Inference
-----------------
- Run inference with Huggingface LLMs:

`python 2_inference_module/run_inference_LangChain_HF.py`


- Run inference with OpenAI models:

`python 2_inference_module/run_inference_OpenAI.py`


Extracted triples are stored in `2_inference_module/output_generated_by_models`.

Post-processing
---------------
Extracted triples come in various formats such as lists, dictionaries, enumerated lists, enumerated strings with separators, JSON strings, and other complex structures.

Parsing Script
--------------
To handle these different formats, use the parsing script as follows:

Scenario 1: Assume the generated text is a structured format
- Action: Attempt to load it directly. It can be:
- List of lists
- List of dicts
- Dictionary of triples where values are lists of dicts
- JSON string

Scenario 2: Structure is embedded in the generated text
- Action: Use REGEX to extract the structured span and then load it. It can be:
- List of lists
- List of dicts
- Dictionary of triples where values are lists of dicts
- JSON string
- Enumerated items
- Lists
- Dicts
- Other formats

Post-processing Script
----------------------
To process the generated text, run:

`python 2_inference_module/post_process_generated_string.py`


Post-processed output can be found in `2_inference_module/postprocessed_outputs`. This will be the input for the evaluation module.
