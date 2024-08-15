from datasets import load_dataset
import logging
import json
import os
import random
import argparse 
from retry import retry
import requests
import requests_cache
from tqdm import tqdm

# Enable cache and specify the cache name (it will be stored in a file with this name)
requests_cache.install_cache('wikidata_cache', backend='sqlite', expire_after=172800)  # Cache expires after 48 hours (in seconds)

logging.basicConfig(level=logging.INFO)
logging.info('Start Logging')
    

def lookup_entity_type(entity_types, type_string):
    """	 Looks up the entity type from the entity_types.json object
        returns the entity type as a string
    """
    
    for key, value in entity_types.items():
        if key == type_string:
            ent_type = value
    
    return ent_type


def lookup_relations(relations, search_value, search_key='Relation'):
    """     Looks up the relation from the relations.json object
            returns the relation as a string
    """
    
    for relation in relations:
        if relation['Predicate number'] == search_value:
            return relation[search_key]

# Get an answer from Wikidata API
@retry(tries=3, delay=2, max_delay=25)       
def get_wikidata_label_and_description(wikidata_id):
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbgetentities",
        "format": "json",
        "ids": wikidata_id,
        "languages": "en",
        "props": "labels|descriptions"
    }

    response = requests.get(url, params=params)
    data = response.json()

    if "entities" in data and wikidata_id in data["entities"]:
        entity = data["entities"][wikidata_id]
        label = entity["labels"].get("en", {}).get("value", "No label available")
        description = entity["descriptions"].get("en", {}).get("value", "No description available")
        return {"id": wikidata_id, "label": label, "description": description}
    else:
        return None
        

def convert_data(data):
    converted_data = []
    for i in tqdm(data, desc="Converting data", total=len(data)):
        input_text = i["text"]
        #print(input_text)
        triples = i["relations"]
        new_triples = []
        wiki_triples = []
        entities = dict()
        properties = dict()
        for t in triples:
            #print(t)
            nt = {"subject": t['subject']['surfaceform'],
                   "subject_type": lookup_entity_type(entity_types, t['subject']['type']),
                   "predicate": lookup_relations(relations_json, t['predicate'], search_key="Relation"),
                   "object": t['object']['surfaceform'],
                   "object_type": lookup_entity_type(entity_types, t['object']['type'])
                   }
            wt = {"subject": t['subject']['surfaceform'],
                   "subject_type": lookup_entity_type(entity_types, t['subject']['type']),
                   "subject_wikiID": t['subject']['uri'],
                   "predicate": lookup_relations(relations_json, t['predicate'], search_key="Relation"),
                   "predicate_wikiID": lookup_relations(relations_json, t['predicate'], search_key="Wikidata ID"),
                   "object": t['object']['surfaceform'],
                   "object_type": lookup_entity_type(entity_types, t['object']['type']),
                   "object_wikiID": t['object']['uri']
                   }
            ent1 = get_wikidata_label_and_description(t['subject']['uri'])
            if ent1 is not None:
                entities[t['subject']['uri']] = ent1
            
            prop  = get_wikidata_label_and_description(lookup_relations(relations_json, t['predicate'], search_key="Wikidata ID"))
            if prop is not None:
                properties[lookup_relations(relations_json, t['predicate'], search_key="Wikidata ID")] = prop

            ent2 = get_wikidata_label_and_description(t['object']['uri'])
            if ent2 is not None:
                entities[t['object']['uri']] = ent2

            new_triples.append(nt)
            wiki_triples.append(wt)

        converted_data.append({"text": input_text,
                            "triples": new_triples,
                            "wiki_triples": wiki_triples,
                            "entities": entities,
                            "properties": properties})
    
    return converted_data

        
if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--output_dir', type=str, default='Entity_Linking/data', help='Output directory')
    parser.add_argument('--entity_types', type=str, default='Entity_Linking/data/entity_types.json', help='Entity types json file')
    parser.add_argument('--relations', type=str, default='Entity_Linking/data/relations.json', help='Relations json file')
    args = parser.parse_args()
    
    logging.info('Downloading RED-FM dataset from HuggingFace Datasets')
    
    redfm = load_dataset('Babelscape/REDFM', 'en')

    logging.info(f''' RED-FM dataset downloaded successfully.
             Number of training examples: {len(redfm['train'])}, 
             Number of test examples: {len(redfm['test'])}, 
             Number of validation instances: {len(redfm['validation'])}''')
    
    with open(args.entity_types, "r", encoding="utf-8") as entity_types_file:
        entity_types = json.load(entity_types_file)
    
    with open(args.relations, "r", encoding="utf-8") as relations_file:
        relations_json = json.load(relations_file)
        
    isExist = os.path.exists(args.output_dir)
    if not isExist: # Create a new directory because it does not exist
        os.makedirs(args.output_dir)
        logging.info('Created a new directory to save the converted RED-FM dataset')
    
    for key in redfm.keys():
        data = redfm[key]
        converted_data = convert_data(data)
        with open(f'{args.output_dir}/{key}.jsonl', 'w', encoding="utf-8") as f:
            for line in converted_data:
                #print(line)
                f.write(json.dumps(line, ensure_ascii=False) + '\n')
            logging.info(f'{key} data converted and saved to {args.output_dir}/{key}.jsonl')
    
    logging.info('Finished converting RED-FM dataset')