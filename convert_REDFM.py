from datasets import load_dataset
import logging
import json
import os
import random
import argparse 

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


def convert_data(data):
    
    """  Converts the RED-FM dataset into a format that can be used by the	prompt generator """
    
    converted_data = []
    for instance in data:
    
        given_text = instance['text']
    
        extracted_entities = []
        types = []
        entity_wiki_ids = []    

        entities = instance['entities']
        
        for entity in entities:
            #print(entity)

            ent_string = entity['surfaceform']
            #print(entity['type'])
            ent_wiki_id = entity['uri']
            ent_type = lookup_entity_type(entity_types, entity['type'])
            if ent_string not in extracted_entities:
                extracted_entities.append(ent_string)
                #print(ent_string)   
                if ent_string == '':
                    continue
                if ent_string[0].isupper():
                    continue
                else:
                    ent_string = ent_string.capitalize() 
                types.append(f'{ent_string} is a/an {ent_type.lower()}.')
                entity_wiki_ids.append(f'{ent_string} has a Wikidata ID of {ent_wiki_id}.')
    
        relations = []
        relations_wiki_ids = []
        string_triples = []
        wiki_triples = []
    
        triples = instance['relations']
        for triple in triples:
            predicate = lookup_relations(relations_json, triple['predicate'], search_key="Relation")
            #print(predicate)
            if predicate not in relations:
                relations.append(predicate)
                predicate_wiki_id = lookup_relations(relations_json, triple['predicate'], search_key="Wikidata ID")
                if predicate[0].isupper():
                    continue
                else:
                    predicate = predicate.capitalize()
                relations_wiki_ids.append(f'{predicate} has the Wikidata ID of {predicate_wiki_id}.')
            
            predicate_wiki_id = lookup_relations(relations_json, triple['predicate'], search_key="Wikidata ID")
            #print(predicate_wiki_id)

            string_triple = (triple['subject']['surfaceform'], predicate, triple['object']['surfaceform'])
            #print(string_triple) 
            if string_triple not in string_triples:
                string_triples.append(string_triple)
            wiki_triple = (triple['subject']['uri'], predicate_wiki_id, triple['object']['uri'])
            #print(wiki_triple)
            if wiki_triple not in wiki_triples:
                wiki_triples.append(wiki_triple)
        #print(string_triples)
        
        num_triples = 2
        made_up_triples = []
        for _ in range(num_triples):
            entity1 = random.choice(extracted_entities)
            relation = random.choice(relations)
            entity2 = random.choice(extracted_entities)
            triple = (entity1, relation, entity2)
            if triple not in string_triples:
                made_up_triples.append(triple)
            
            
        mixed_triples = string_triples + made_up_triples    
        random.shuffle(mixed_triples)
        
        difference_triples = list(filter(lambda x: x not in string_triple, made_up_triples))
        
        
        explanations = []
        
        for i in difference_triples:
            
            if i != []:
                explanation= f'The relation - {i[1]} - does not hold between {i[0]} and {i[2]}.'
                if explanation not in explanations:
                    explanations.append(explanation)
        
        instance_dict = {'Text': given_text,
                     'Entities': extracted_entities,
                     'Entity Types': types,
                     'Entity wiki ids': entity_wiki_ids, 
                     'Relations': relations,
                     'Relation wiki ids': relations_wiki_ids, 
                     'Triples': string_triples,
                     'Wiki Triples': wiki_triples,
                     'Mixed Triples': mixed_triples,
                     'Corrupted Triples': difference_triples,
                     'Explanations': explanations,
                     }

        #print(instance_dict)
        converted_data.append(instance_dict)
    

    return converted_data



if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--output_dir', type=str, default='data/RED-fm', help='Output directory')
    parser.add_argument('--entity_types', type=str, default='data/entity_types.json', help='Entity types json file')
    parser.add_argument('--relations', type=str, default='data/relations.json', help='Relations json file')
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