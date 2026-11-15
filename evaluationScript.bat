@echo off
cd /d "%~dp0"
uv run python 3_evaluation_module/evaluation_reference_to_annotations/evaluate.py --input_dir "2_inference_module/postprocessed_outputs/post_processed_qwen" --gold_file "1_data_module/1_data_preprocessing/RED-fm/test.jsonl" --out_dir "3_evaluation_module/evaluation_reference_to_annotations/Qwen_evaluation_results"
