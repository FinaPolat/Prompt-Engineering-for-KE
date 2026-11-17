@echo off
cd /d "%~dp0"
uv run python 2_inference_module/post_process_generated_string.py --input_folder "2_inference_module/output_generated_by_models/generated_by_qwen" --out_dir "2_inference_module/postprocessed_outputs/post_processed_qwen"