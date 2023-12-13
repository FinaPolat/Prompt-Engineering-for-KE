Testing Prompt Engineering Methods for Knowledge Extraction from Text


1. Download data and preprocess it according to project requirements: 
    convert_REDFM.py

    Ps. the resulting files already in the folder: "data"

2. Prompt templates can be found in the folder: "prompt templates"

    Ps. template_creator.py can facilitate the creation of prompt templates

3. Compile prompts using:
    i. retrieval_augmented_prompt_compiler.py
    ii. no_retrieval_prompt_compiler.py

4. Run inference:
    run_inference.py

    Ps. generated content can be found in the folder: "generated_output_by_GPT4"

5. Process the generated content:
    post_processing.py

    Ps. post-proccessed outputs can be found in the folder: "post_processed"

6. Evaluation script: 
    general_evaluation_final.py

    Ps. all evaluation files can be found in the folder: "evaluation_reference_to_Wikidata/21_Nov_23_evaluation"
