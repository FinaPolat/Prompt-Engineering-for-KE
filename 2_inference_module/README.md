# Inference Module
==============================

This module contains scripts for running inference using the OpenAI API and local Ollama models through LangChain.

Overview
--------
The data does not require further processing at this stage. The script reads prompts from the `1_data_module/2_creating_prompts/data_with_prompts` directory.

API Keys
--------
OpenAI inference requires an API key in the project `.env` file. Ollama inference runs locally and does not require an API key; ensure the Ollama application is running and the selected model is installed (for example, `ollama pull qwen3.5:4b`).

Running Inference
-----------------
- Run inference with a local Ollama model:

`uv run python 2_inference_module/run_inference_LangChain_HF.py --input_folder "1_data_module/2_creating_prompts/data_with_prompts" --model_name "qwen3.5:4b" --out_dir "2_inference_module/output_generated_by_models/generated_by_Llama"`


- Run inference with OpenAI models:

`python 2_inference_module/run_inference_OpenAI.py`


Extracted triples are stored in `2_inference_module/output_generated_by_models`.

Post-processing
---------------
Extracted triples come in various formats such as lists, dictionaries, enumerated lists, enumerated strings with separators, JSON strings, and other complex structures.

To handle these different formats, the parsing script works as follows:

Scenario 1: Assume the generated text is a structured format.

Action: Attempt to load it directly. It can be:

  - List of lists
  - List of dicts
  - Dictionary of triples where values are lists of dicts
  - JSON string

Scenario 2: Structure is embedded in the generated text.

Action: Use REGEX to extract the structured span and then load it. It can be:

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
