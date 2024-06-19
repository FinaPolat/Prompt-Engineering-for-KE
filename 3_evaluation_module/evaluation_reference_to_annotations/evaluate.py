import json
import os
from tqdm import tqdm
import argparse
import logging


def read_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def read_jsonlines(gold_file_path):
    with open(gold_file_path, 'r', encoding="utf-8") as f:
        data = f.readlines()
        data = [json.loads(line) for line in data]
    return data


def read_triples(data):
    # Try reading from a list of lists
    if isinstance(data, list) and all(isinstance(item, list) for item in data):
        return data
    
    # Try reading from a list of dicts with keys: subject, predicate, object
    if isinstance(data, list) and all(isinstance(item, dict) and all(key in item for key in ['subject', 'predicate', 'object']) for item in data):
        lists_data = [[item['subject'], item['predicate'], item['object']] for item in data]
        return lists_data
    
        # Try reading from a list of dicts with keys: Subject, Predicate, Object
    if isinstance(data, list) and all(isinstance(item, dict) and all(key in item for key in ['Subject', 'Predicate', 'Object']) for item in data):
        lists_data = [[item['Subject'], item['Predicate'], item['Object']] for item in data]
        return lists_data
    
        # Try reading from a list of dicts with keys: subject, relation, object
    if isinstance(data, list) and all(isinstance(item, dict) and all(key in item for key in ['subject', 'relation', 'object']) for item in data):
        lists_data = [[item['subject'], item['relation'], item['object']] for item in data]
        return lists_data
    
    # Try reading from a dict with key "Triples" and value as a list of dicts
    if isinstance(data, dict) and 'Triples' in data and isinstance(data['Triples'], list) and all(isinstance(item, dict) and all(key in item for key in ['subject', 'predicate', 'object']) for item in data['Triples']):
        lists_data = [[item['subject'], item['predicate'], item['object']] for item in data['Triples']]
        return lists_data
    
        # Try reading from a dict with key "Triples" and value as a list of dicts
    if isinstance(data, dict) and 'triples' in data and isinstance(data['triples'], list) and all(isinstance(item, dict) and all(key in item for key in ['subject', 'predicate', 'object']) for item in data['triples']):
        lists_data = [[item['subject'], item['predicate'], item['object']] for item in data['triples']]
        return lists_data
    
    if isinstance(data, dict) and 'knowledge_triples' in data and isinstance(data['knowledge_triples'], list) and all(isinstance(item, dict) and all(key in item for key in ['subject', 'predicate', 'object']) for item in data['knowledge_triples']):
        lists_data = [[item['subject'], item['predicate'], item['object']] for item in data['knowledge_triples']]
        return lists_data
    
    # If none of the above conditions match
    #print("Invalid data structure format.")
    return None  # Return None for invalid data structures

def evaluate():
    
    logging.basicConfig(level=logging.INFO)
    logging.info('Start Logging')
    
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--input_dir', type=str, default='2_inference_module/postprocessed_outputs/post_processed_Llama', help='Directory to read extraction files')
    parser.add_argument('--gold_file', type=str, default='1_data_module/1_data_preprocessing/RED-fm/test.jsonl', help='File to get the text from which the extractions were made')
    parser.add_argument('--out_dir', type=str, default='3_evaluation_module/evaluation_reference_to_annotations/Llama_evaluation_results', help='Directory to save evaluation results')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_dir):
        print(f"'{args.input_dir}' does not exist. Please check the folder name and try again.")
        
    if not os.path.exists(args.out_dir):
        os.makedirs(args.out_dir)

    gold_data = read_jsonlines(args.gold_file)
    
    files = os.listdir(args.input_dir)

    for file in tqdm(files, desc='Reading extraction files', total=len(files)):
        print(file)
        input_file_path = os.path.join(args.input_dir, file)
        with open(input_file_path, "r", encoding="utf-8") as f:
            extractions = json.load(f)

        precision = []
        recall = []
        nr_of_gold_matches = 0

        for index, item in tqdm(enumerate(extractions), desc=f"Evaluating triples from: {file}", total=len(extractions)):
            gold = gold_data[index]["Triples"]
            gold_triples = []
            for triple in gold:
                lower_triple = [item.lower() for item in triple]
                gold_triples.append(lower_triple)
            
            triples =read_triples(item["postprocessed"])
            if triples == None:
                #print(f"Invalid data structure format in file: {file}")
                #print(item["postprocessed"])
                #print(type(item["postprocessed"]))
                #print("##############################################")
                #if type(item["postprocessed"]) == list:
                    #for i in item["postprocessed"]:
                        #print(i)
                        #print(type(i))
                        #print("-------------------")
                precision.append(0)
                recall.append(0)
                continue
            else:
                extracted_triples = []
                for triple in triples:
                    if len(triple) != 3:
                        continue
                    if type(triple) == None:
                        continue
                    else:
                        lower_triple = []
                        for item in triple:
                            if type(item) == str:
                                lower_triple.append(item.lower())
                        extracted_triples.append(lower_triple)

                if len(extracted_triples) == 0:
                    precision.append(0)
                    recall.append(0)
                    continue

                tp = 0
                fp = 0
                fn = 0

                for triple in extracted_triples:
                    if triple in gold_triples:
                        tp += 1
                        nr_of_gold_matches += 1
                    else:
                        fp += 1

                for triple in gold_triples:
                    if triple not in extracted_triples:
                        fn += 1

                if tp + fp == 0:
                    precision.append(0)
                else:
                    precision.append(tp / (tp + fp))

                if tp + fn == 0:
                    recall.append(0)
                else:
                    recall.append(tp / (tp + fn))

        precision = sum(precision) / len(precision)
        recall = sum(recall) / len(recall)

        if precision + recall == 0:
            f1 = 0
        else:
            f1 = 2 * (precision * recall) / (precision + recall)

        with open(os.path.join(args.out_dir, file), "w", encoding="utf-8") as f:
            json.dump({"Averaged results": {"precision": precision, "recall": recall, "f1": f1}, "Number of gold matches": nr_of_gold_matches}, f, indent=4, ensure_ascii=False)

        print(f"Precision: {precision}, Recall: {recall}, F1: {f1}")

if __name__ == "__main__":
    evaluate()