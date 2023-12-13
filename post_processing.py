import json
import os
import re
import argparse
import logging
from tqdm import tqdm


def read_extraction_file(file_path):
    # Read the extraction file
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        print(len(data))
    return data


def extract_last_list_of_lists(input_string):
    # Define a regular expression pattern to match individual nested lists
    input_string = input_string.replace("\n", '').replace('\"', '').replace("\\", '').replace("'", '').strip()
    
    pattern = r"\[\[(.*?)\]\]"

    
    # Find all occurrences of the pattern in the input string
    nested_lists = re.findall(pattern, input_string)
    
    if nested_lists == []:
        return "No triples found."
    else:
        return nested_lists
    
def extract_zero_shot_CoT(input_string):
    # for zero-shot CoT prompts
    pattern = r"\(([^,]+),\s*([^,]+),\s*([^)]+)\)"
    matches = re.findall(pattern, input_string)
    triples = [(match[0].strip(), match[1].strip(), match[2].strip()) for match in matches]
    if triples == []:
        return "No triples found."
    else:
        return triples

    
def get_extracted_triples(extracted_string):
    
    canditates = extract_last_list_of_lists(extracted_string)
    
    processed_canditates = []
    for c in canditates:
        c = c.replace("[", '').replace("'", '').replace("\n", '').strip()
        c = c.split('], ')
        new_c = []
        for t in c:
            t = t.split(', ')
            t = [item.lower().strip() for item in t]
            new_c.append(t)
        
        processed_canditates.append(new_c)
    
    return processed_canditates[-1]

def extract_json_object_from_string(input_string):
    # for zero-shot ReAct prompts
    pattern = r'```json\n(.*?)```'
    json_match = re.search(pattern, input_string, re.DOTALL)
    
    if json_match:
        # Extracted JSON string
        json_string = json_match.group(1)
        # Load JSON object from the string
        json_object = json.loads(json_string)
        # Print the extracted JSON object
        return json_object
    else:
        return "No JSON object found in the input string."
    
def extract_and_load_json(input_string):
    try:
        # Find the JSON substring within the input string
        start_index = input_string.find('{')
        end_index = input_string.rfind('}') + 1
        json_string = input_string[start_index:end_index]

        # Load the JSON substring
        json_string = eval(json_string)
        json_data = json.loads(json_string)
        return json_data
    except (ValueError, json.JSONDecodeError):
        # If loading as JSON fails, return None
        return None

    
    
def main():
    
    logging.basicConfig(level=logging.INFO)
    logging.info('Start Logging')
    
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--input_folder', type=str, default='generated_output_by_GPT4', help='Input directory')
    parser.add_argument('--out_dir', type=str, default='post_processed_2', help='Output directory')
    
    args = parser.parse_args()
    
    if os.path.exists(args.input_folder) and os.path.isdir(args.input_folder):
        file_names = os.listdir(args.input_folder)
    else:
        print(f"The folder '{args.input_folder}' does not exist or is not a directory.")
        
    if not os.path.exists(args.out_dir):
        os.makedirs(args.out_dir)
    
    
    for file in tqdm(file_names):
        print(file + '----------------')
        post_processed_data = []
        logging.info(f'Read the input file: {file}. Postprocessing started.')
        filepath = os.path.join(args.input_folder, file)
        outfile = f'post_processed_{file}'
        data = read_extraction_file(filepath)
        for i, d in enumerate(data):
            #print(i)
            input_string = d['extraction']
            if file == "zero_shot_CoT_prompts_test.json":
                input_string = input_string.lower().strip()
                triples = extract_zero_shot_CoT(input_string)
                #print(triples)
                
            elif file == "zero_shot_ReAct_prompts_test.json":
                input_string = input_string.lower().strip()
                try:
                    triples = extract_json_object_from_string(input_string)
                    if triples == "No JSON object found in the input string.":
                        try:
                            input_string = eval(input_string)
                            triples = json.loads(json.dumps(input_string))
                        except:
                            triples = extract_and_load_json(input_string)
                            
                except:
                    triples = get_extracted_triples(input_string)
 
            else:
                input_string = input_string.lower().strip()
                #print(f'######## {input_string}')
                try:
                    input_string = eval(input_string)
                    triples = json.loads(json.dumps(input_string))
                except:
                    triples = get_extracted_triples(input_string)
                    
            #print(type(triples))
            #print(triples)
            #print('**************')
            d['postprocessed'] = triples
            post_processed_data.append(d)
            
        with open(os.path.join(args.out_dir, outfile), 'w', encoding='utf-8') as f:
            json.dump(post_processed_data, f, indent=4, ensure_ascii=False) 
            logging.info(f'Postprocessed output is written to {outfile}.')
    
if __name__ == '__main__':
    main()