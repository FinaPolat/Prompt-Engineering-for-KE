from langchain_huggingface import HuggingFaceEndpoint
from getpass import getpass
import os
import json
from retry import retry
import argparse
import logging
import time
from tqdm import tqdm

HUGGINGFACEHUB_API_TOKEN = getpass()
os.environ["HUGGINGFACEHUB_API_TOKEN"] = "your_HF_API_token_here"

def read_prompts(input_file): 
    
    with open(input_file, 'r', encoding='utf-8') as prompt_file:
        prompts = json.load(prompt_file)
        
    return prompts

#repo_id = "mistralai/Mistral-7B-Instruct-v0.3"
#repo_id = "microsoft/Phi-3-mini-4k-instruct"
#repo_id = "meta-llama/Meta-Llama-3-8B-Instruct"
#repo_id = "google/gemma-1.1-7b-it"


def main():
        
    logging.basicConfig(level=logging.INFO)
    logging.info('Start Logging')
    # Record the start time
    start_time = time.time()
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--input_folder', type=str, default='data_with_prompts', help='Input directory')
    parser.add_argument('--model_name', type=str, default="meta-llama/Meta-Llama-3-8B-Instruct", help='Huggingface model name')
    parser.add_argument('--out_dir', type=str, default='generated_by_Llama', help='Output directory')

    args = parser.parse_args()
    
    if os.path.exists(args.input_folder) and os.path.isdir(args.input_folder):
       
        file_names = os.listdir(args.input_folder)
    else:
        print(f"The folder '{args.input_folder}' does not exist or is not a directory.")
        
    if not os.path.exists(args.out_dir):
        os.makedirs(args.out_dir)

    llm = HuggingFaceEndpoint(
    repo_id=args.model_name, max_new_tokens=512, temperature=0.5, huggingfacehub_api_token=os.environ["HUGGINGFACEHUB_API_TOKEN"])
    
    for file in file_names:
        prompt_file = f'{args.input_folder}/{file}'
        prompts = read_prompts(prompt_file)
        #prompts = prompts[:3]
        total_instances = len(prompts)
    
        logging.info(f'Read the input file: {prompt_file}. Number of instances: {total_instances}. Extraction started.')
    
        generated_extractions = []
    
        for i, prompt in enumerate(tqdm(prompts, desc=f"Passing inputs through {args.model_name} for inference", total=total_instances)):
            generated_text = llm.invoke(prompt)
            #print(generated_text)
            generated_extractions.append({"index": i, "prompt": prompt, "generated_text": str(generated_text)})

        outfile = prompt_file.split('/')[-1]
    
        logging.info(f'Extraction finished. Saved the results to {args.out_dir}/{outfile}')
    
        with open(f'{args.out_dir}/{outfile}', 'w', encoding='utf-8') as output_file:
            json.dump(generated_extractions, output_file, indent=4, ensure_ascii=False)
        
    end_time = time.time()
    
    # Calculate the elapsed time
    elapsed_time = (end_time - start_time) / 60
    print(f"Elapsed time: {elapsed_time:.2f} minutes")

if __name__ == '__main__':
    main()
