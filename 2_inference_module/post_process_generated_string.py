import json
import os
import re
import ast
import argparse
import logging
from tqdm import tqdm



def read_extraction_file(file_path):
    # Read the extraction file
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        print(len(data))
    return data

def load_structure(text):
    """	treat the text as a data structure such as list, dict or JSON string, try to load the structure. If it fails, return Try REGEX."""

    try:
        extraction = json.loads(text)
    except:
        extraction = "Structure may be in the text. Try REGEX."

    if extraction == "Structure may be in the text. Try REGEX.":   
        try:
            extraction = ast.literal_eval(text)
            if "triples" in extraction:
                extraction = extraction["triples"]
            elif "triple" in extraction:
                extraction = extraction["triple"]
            extraction = json.loads(extraction)
        except:
            extraction = "Structure may be in the text. Try REGEX."

    return extraction

def extract_series_of_lists(text):
    pattern = r"\['(.*?)', '(.*?)', '(.*?)'\]"
    matches = re.findall(pattern, text)
    extraction = [list(match) for match in matches]
    if extraction == []:
        extraction = "No series of lists found in the text."
    return extraction

def extract_list_of_lists(text):
    try:
        pattern = re.compile(r"(\[\[.*?\]\])", re.DOTALL)
        triples_part = pattern.search(text).group(1)
        # Regex to extract each triple
        triple_pattern = re.compile(r"\['(.*?)',\s*'(.*?)',\s*'(.*?)'\]")
        # Find all triples
        triples = triple_pattern.findall(triples_part)
        # Convert to list of lists
        extraction = [list(triple) for triple in triples]
    except:
        extraction = "No list of lists found in the text."

    return extraction
    
def extract_list_of_dicts(text):
    # Define regex to extract the list of dictionaries
    pattern = re.compile(r"\[\s*\{.*?\}\s*\]", re.DOTALL)
    # Extract the list of dictionaries
    match = pattern.search(text)
    if match:
        list_of_dicts_string = match.group(0)
        # Parse the text into a list of lists
        try:
            extraction = ast.literal_eval(list_of_dicts_string)
        except:
            extraction = "List of dictionaries not found in the text."
    else:
        extraction = "List of dictionaries not found in the text."

    return extraction
    
def extract_json_string(text):
    # Define the regex pattern to match the JSON string
    pattern = r"```(?:json)?\n([\s\S]*?)\n```"
    match = re.findall(pattern, text)
    try:
        extraction = json.loads(match[-1])  
    except:
        extraction = "JSON string not found in the text."
    
    return extraction

def extract_list_of_tuples(text):
    try:
        # Regular expression to match the tuples
        pattern = r'\("([^"]+)", "([^"]+)", "([^"]+)"\)'
        # Find all matches
        matches = re.findall(pattern, text)
        #Convert to list of lists
        extraction = [list(match) for match in matches]
        if extraction == []:
            extraction = "No list of tuples found in the text." 
    except:
        extraction = "No list of tuples found in the text."
    return extraction


def extract_enumerated_lists(text):
    try:
        items = re.findall(r'\d+\.\s+\[(.*?)\]', text)
        # Splitting each item into its components
        extraction = [item.replace("'","").split(', ') for item in items]
        if extraction == []:
            extraction = "No enumerated list found in the text."
    except:
        extraction = "No enumerated list found in the text."
    
    return extraction

def extract_enumerated_dicts(text):
    try:
        items = re.findall(r'\d+\.\s+({.*?})', text)
        try:
            extraction = [json.loads(item) for item in items]
        except:
            extraction = []
        if extraction == []:
            extraction = "No enumerated dicts found in the text."
    except:
        extraction = "No enumerated dicts found in the text."
        
    return extraction

def extract_enumerated_list_of_tuples(text):
    items = re.findall(r'\d+\.\s+\[(.*?)\]', text)
    extraction = [ast.literal_eval(item) for item in items]
    if extraction == []:
        extraction = "No enumerated list of tuples found in the text."
    return extraction

def extract_enumerated_tuples(text):
    pattern = re.compile(r"\(\s*(.*?)\s*,\s*(.*?)\s*,\s*(.*?)\s*\)")
    # Find all matches
    matches = pattern.findall(text)
    extraction = [list(match) for match in matches]
    if extraction == []:
        extraction = "No enumerated tuples found in the text."
    return extraction

def extract_dash_separeted_tuples(text):
    try:
        items = re.findall(r'\d+\.\s+(.*?)\n', text)
        extraction = [item.replace('\"', '').split(' - ') for item in items]
        if extraction == []:
            extraction = "No enumerated tuples seperated by - found in the text."
    except: 
        extraction = "No enumerated tuples seperated by - found in the text."
    return extraction

def extract_enumerated_dash_separated_strings(text):
    try:
        pattern = re.compile(r"\d+\.\s*([^\n]+)")
        matches = pattern.findall(text)
        matches = matches[-1].split(".")
        extraction = []
        for i in matches:
            if " - " in i:
                extraction.append(i.split(" - "))
    except:
        extraction = "No enumerated items separated by - found in the text."
    
    if extraction == []:
        extraction = "No enumerated items separated by - found in the text."
    
    return extraction

def extract_enumerated_dict_strings(text):
    #text = text.replace('\n', '')
    try:
        pattern = r'Subject: (.*?), Predicate: (.*?), Object: (.*?)\n'
        matches = re.findall(pattern, text)
        triples = []
        for match in matches:
            triple = {'subject': match[0], 'predicate': match[1], 'object': match[2]}
            triples.append(triple)
        if triples == []:
            triples = "No enumerated dict strings found in the text."
    except:
        triples = "No enumerated dict strings found in the text."
    return triples

def extract_enumerated_dict_strings2(text):
    try:
        # Regular expression pattern to match Subject, Predicate, and Object
        pattern = r'Subject: (.*?)\n\nPredicate: (.*?)\n\nObject: (.*?)\n\n'
        # Find all matches
        matches = re.findall(pattern, text, re.DOTALL)
        # Convert matches to a list of dictionaries
        triples = []
        for match in matches:
            triple = {
                "Subject": match[0].strip(),
                "Predicate": match[1].strip(),
                "Object": match[2].strip()
                }
        triples.append(triple)
        if triples == []:
            triples = "No enumerated dict strings found in the text."

    except:
        triples = "No enumerated dict strings found in the text."

    return triples

        
    
    

    
def main():
    
    logging.basicConfig(level=logging.INFO)
    logging.info('Start Logging')
    
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--input_folder', type=str, default='generated_by_Mistral', help='Input directory')
    parser.add_argument('--out_dir', type=str, default='post_processed_Mistral', help='Output directory')
    
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
            print(i)
            text =  d["generated_text"].strip() #d["extraction"].strip() #
            extraction = load_structure(text)
            print(extraction)

            if extraction == "Structure may be in the text. Try REGEX.":
                extraction = extract_enumerated_dict_strings(text)
                print(extraction)
            if extraction == "No enumerated dict strings found in the text.":
                extraction = extract_enumerated_dict_strings2(text)
                print(extraction)
            if extraction == "No enumerated dict strings found in the text.":
                extraction = extract_series_of_lists(text)
                print(extraction)
            if extraction == "No series of lists found in the text.":
                extraction = extract_list_of_lists(text)
                print(extraction)
            if extraction == "No list of lists found in the text.":
                extraction = extract_list_of_dicts(text)
                print(extraction)
            if extraction == "List of dictionaries not found in the text.":
                extraction = extract_json_string(text)
                print(extraction)
            if extraction == "JSON string not found in the text.":
                extraction = extract_list_of_tuples(text)
                print(extraction)
            if extraction == "No list of tuples found in the text.":
                extraction = extract_enumerated_lists(text)
                print(extraction)
            if extraction == "No enumerated list found in the text.":
                extraction = extract_enumerated_dash_separated_strings(text)
                print(extraction)
            if extraction == "No enumerated items separated by - found in the text.":
                extraction = extract_enumerated_dicts(text)
                print(extraction)
            if extraction == "No enumerated dicts found in the text.":
                extraction = extract_enumerated_list_of_tuples(text)
                print(extraction)
            if extraction == "No enumerated list of tuples found in the text.":
                extraction = extract_enumerated_tuples(text)
                print(extraction)
            if extraction == "No enumerated tuples found in the text.":
                extraction = extract_dash_separeted_tuples(text)
                print(extraction)
            if extraction == "No enumerated tuples seperated by - found in the text.":
                extraction = "No structure found in the text."
                print(extraction)
            
            if type(extraction) == list:
                new_extraction = []
                for item in extraction:
                    if type(item) == set:
                        item = list(item)
                        new_extraction.append(item) 
                        extraction = new_extraction

            if extraction == "No structure found in the text.":
                extraction = []
                print(extraction)
            
            d['postprocessed'] = extraction
            post_processed_data.append(d)
            #print(d['postprocessed'])
            
        with open(os.path.join(args.out_dir, outfile), 'w', encoding='utf-8') as f:
            json.dump(post_processed_data, f, indent=4, ensure_ascii=False) 
            logging.info(f'Postprocessed output is written to {outfile}.')
    
if __name__ == '__main__':
    main()