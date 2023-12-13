import requests
import requests_cache
import json
import os
from retry import retry
from string import Template
from tqdm import tqdm
import argparse
import logging
import time 

# Enable cache and specify the cache name (it will be stored in a file with this name)
requests_cache.install_cache('wikidata_cache', backend='sqlite', expire_after=28800)  # Cache expires after 8 hours (in seconds)

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
    
        # Try reading from a list of dicts with keys: subject, predicate, object
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

# Get an answer from Wikidata API
@retry(tries=3, delay=2, max_delay=25)
def get_wiki_ID(query, query_type='entity'):
  if query_type == 'entity':
    url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={query}&language=en&format=json"
  if query_type == 'property':
    url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={query}&type=property&language=en&format=json"
  try:
    data = requests.get(url).json()
    # Return the first id (Could upgrade this in the future)
    return data['search'][0]['id']
  except:
    return 'no-wikiID'

@retry(tries=3, delay=2, max_delay=25)
def check_triple_exists(sparql_query_template, endpoint_url, triple):
    sparql_query = sparql_query_template.format(subject=triple[0], predicate=triple[1], object=triple[2])
    response = requests.get(endpoint_url, params={'query': sparql_query, 'format': 'json'})
    #print(response)
    data = response.json()
    #print(data)
    result = data['boolean']
    
    return result

@retry(tries=3, delay=2, max_delay=5)
def execute_sparql_query(query):
    endpoint_url = "https://query.wikidata.org/sparql"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    params = {
        'query': query,
        'format': 'json'
    }

    try:
        response = requests.get(endpoint_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.HTTPError as errh:
        print("HTTP Error:", errh)
    except requests.exceptions.ConnectionError as errc:
        print("Error Connecting:", errc)
    except requests.exceptions.Timeout as errt:
        print("Timeout Error:", errt)
    except requests.exceptions.RequestException as err:
        print("Something went wrong:", err)
        
def get_bindings_from_sparql_query(query, query_type='instanceOf'):
    
    response = execute_sparql_query(query)
    bindings = response['results']['bindings']
    zero_hop_dict = {}
    one_hop_dict = {}
    two_hop_dict = {}
    three_hop_dict = {}
    
    if query_type == 'instanceOf' or query_type == 'subclassOf':
        hop1 = 'superClass'
        hop2 = 'superSuperClass'
        hop3 = 'superSuperSuperClass'

        for i in bindings:
            #print(i)
            if query_type in i:
                query_type_uri = i[query_type]['value'].split('/')[-1]
                query_type_label = i[f'{query_type}Label']['value']
                zero_hop_dict[query_type_label] = query_type_uri

            if hop1 in i:
                hop1_uri = i[hop1]['value'].split('/')[-1]
                hop1_label = i[f'{hop1}Label']['value']
                one_hop_dict[hop1_label] = hop1_uri
            
            if hop2 in i:
                hop2_uri = i[hop2]['value'].split('/')[-1]
                hop2_label = i[f'{hop2}Label']['value']
                two_hop_dict[hop2_label] = hop2_uri
                
            if hop3 in i:
                hop3_uri = i[hop3]['value'].split('/')[-1]
                hop3_label = i[f'{hop3}Label']['value']
                three_hop_dict[hop3_label] = hop3_uri
                
        results_dict = {'zero_hop': zero_hop_dict, 'one_hop': one_hop_dict, 'two_hop': two_hop_dict, 'three_hop': three_hop_dict}
            
    if query_type == 'domain' or query_type == 'range':
        for i in bindings:
            #print(i)
            if query_type in i:
                query_type_uri = i[query_type]['value'].split('/')[-1]
                query_type_label = i[f'{query_type}Label']['value']
                zero_hop_dict[query_type_label] = query_type_uri
        results_dict = zero_hop_dict
        
    return results_dict
    
def find_matching_classes(entity_dict, relation_dict):
    match_exists = False
    matching_level = None
    matched_wikiID = None
    matched_label = None
    
    for hop, classes in entity_dict.items():
        for label, wiki_id in classes.items():
            if wiki_id in relation_dict.values():
                match_exists = True
                matching_level = hop
                matched_wikiID = wiki_id
                matched_label = label
                break
        if match_exists:
            break
    
    return match_exists, matching_level, matched_wikiID, matched_label


def convert_match_level_to_integer(matching_level):
    if matching_level == 'zero_hop':
        matching_level = 0
    if matching_level == 'one_hop':
        matching_level = 1
    if matching_level == 'two_hop':
        matching_level = 2
    if matching_level == 'three_hop':
        matching_level = 3
    return matching_level

def merge_dicts(dict1, dict2):
    merged = dict1.copy()
    for key, value in dict2.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged
    

def evaluate():
    
    logging.basicConfig(level=logging.INFO)
    logging.info('Start Logging')
    
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--input_dir', type=str, default='post_processed_2', help='Directory to read extraction files')
    parser.add_argument('--gold_file', type=str, default='data/RED-fm/test.jsonl', help='File to read gold triples')
    parser.add_argument('--out_dir', type=str, default='evaluation_reference_to_Wikidata/21_Nov_23_evaluation', help='Directory to save evaluation results')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_dir):
        print(f"'{args.input_dir}' does not exist. Please check the folder name and try again.")
        
    if not os.path.exists(args.out_dir):
        os.makedirs(args.out_dir)

    complicated_relations= ['are ', 'can be ', 'at ', 'author ', 'became ', 'become ', 'becomes ', 'began ', 'can be ', 'can ', 'had ', 'had a ', 'has an ', 'has a ', 'has an ', 'has been ', 'in ', 'is ', 'is a ', 'is an ', 'main ', 'most ', 'must ', 'must be ', 'was ', 'was a ', 'was an ', 'will ', 'will be ']
    #print(len(complicated_relations))

    endpoint_url = "https://query.wikidata.org/sparql"

    statement_check_template = """
                    PREFIX wd: <http://www.wikidata.org/entity/>
                    PREFIX p: <http://www.wikidata.org/prop/>
                    PREFIX ps: <http://www.wikidata.org/prop/statement/>

                    ASK WHERE {{
                            wd:{subject} p:{predicate} ?statement.
                            ?statement ps:{predicate} wd:{object}.
                    }}
                """ 
    instanceOf_check = Template("""
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        PREFIX bd: <http://www.bigdata.com/rdf#>
        PREFIX wikibase: <http://wikiba.se/ontology#>

        SELECT ?instanceOf ?instanceOfLabel ?superClass ?superClassLabel ?superSuperClass ?superSuperClassLabel ?superSuperSuperClass ?superSuperSuperClassLabel
                    
        WHERE { wd:$item wdt:P31 ?instanceOf.
                ?instanceOf wdt:P279 ?superClass.
                ?superClass wdt:P279 ?superSuperClass.
                ?superSuperClass wdt:P279 ?superSuperSuperClass.
                SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
                }
        """)


    subclassOf_check = Template("""
            PREFIX wd: <http://www.wikidata.org/entity/>
            PREFIX wdt: <http://www.wikidata.org/prop/direct/>
            PREFIX bd: <http://www.bigdata.com/rdf#>
            PREFIX wikibase: <http://wikiba.se/ontology#>

            SELECT ?subclassOf ?subclassOfLabel ?superClass ?superClassLabel ?superSuperClass ?superSuperClassLabel ?superSuperSuperClass ?superSuperSuperClassLabel
                    
            WHERE {
                    wd:$item wdt:P279 ?subclassOf.
                    ?subclassOf wdt:P279 ?superClass.
                    ?superClass wdt:P279 ?superSuperClass.
                    ?superSuperClass wdt:P279 ?superSuperSuperClass.
                    SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
                }
        """)

    domain_check = Template("""
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX p: <http://www.wikidata.org/prop/>
        PREFIX ps: <http://www.wikidata.org/prop/statement/>

        SELECT ?domain ?domainLabel 
        WHERE {
        wd:$item p:P2302 [ps:P2302 wd:Q21503250; pq:P2308 ?domain].
        
        SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
        }
        """)

    range_check = Template("""
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX p: <http://www.wikidata.org/prop/>
        PREFIX ps: <http://www.wikidata.org/prop/statement/>

        SELECT ?range ?rangeLabel 
        WHERE {

        wd:$item  p:P2302 [ps:P2302 wd:Q21510865; pq:P2308 ?range].
        
        SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
        }
        """)

    ##########################################################################################################################
    gold_data = read_jsonlines(args.gold_file)
    
    files = os.listdir(args.input_dir)

    for file in tqdm(files, desc='Reading extraction files', total=len(files)):
        print(file)
        start_time = time.time()
        input_file_path = os.path.join(args.input_dir, file)
        with open(input_file_path, "r", encoding="utf-8") as f:
            extractions = json.load(f)
        
        extraction_reading_problems = []
        all_triples = []
        malformed_triples = []
        all_relations = set()
        all_entities = set()
        
        triples_with_all_components_in_wikidata = 0
        triple_dict = {}
        
        has_domain_range = 0
        domain_range_matches = 0
        zero_hop_matches = 0
        one_hop_matches = 0
        two_hop_matches = 0
        three_hop_matches = 0
        
        statement_matches = 0
        both_statement_and_domain_range_matches = 0
        
        has_domain_range_no_subject_no_object = 0
        
        has_domain_range_only_subject_has_wikiId = 0
        has_domain_range_only_subject_has_wikiId_and_match = 0
        
        has_domain_range_only_object_has_wikiId = 0
        has_domain_range_only_object_has_wikiId_and_match = 0

        for index, item in tqdm(enumerate(extractions), desc=f"Evaluating triples from: {file}", total=len(extractions)):
            input_text = gold_data[index]['Text']
            triples =read_triples(item["postprocessed"])
            
            if triples == None:
                extraction_reading_problems.append((item["postprocessed"], file))
                continue
            
            for triple in triples:
                all_triples.append(triple)
                if len(triple) != 3:
                    malformed_triples.append(triple)
                    continue
                if type(triple) == None:
                    malformed_triples.append('None')
                    continue
                
                triple_as_key = f'{triple[0]} && {triple[1]} && {triple[2]}'
                #print(triple_as_key)
                triple_dict[triple_as_key] = {"Extracted from": input_text, 
                                            "String triple": triple}
                
                subject = get_wiki_ID(triple[0], query_type='entity')
                object = get_wiki_ID(triple[2], query_type='entity')
                predicate = get_wiki_ID(triple[1], query_type='property')
                
                all_relations.add((str(triple[1]), predicate))
                all_entities.add((str(triple[0]), subject))
                all_entities.add((str(triple[2]), object))
                
                if predicate == 'no-wikiID':
                        try: 
                            for i in complicated_relations:
                                if triple[1].startswith(i):
                                    predicate = triple[1].split(i)[-1]
                                    predicate = get_wiki_ID(predicate, query_type='property')

                        except:
                            predicate = 'no-wikiID'

                wiki_triple = [subject, predicate, object]
                #print(wiki_triple)
                triple_dict[triple_as_key]["Wiki triple"] = wiki_triple
                
                if predicate == 'no-wikiID':
                    triple_dict[triple_as_key]["All components in Wikidata"] = False
                    triple_dict[triple_as_key]["has Domain"] = False
                    triple_dict[triple_as_key]["has Range"] = False
                    continue
                else:
                    domain_query = domain_check.substitute(item=predicate)
                    #print(domain_query)
                    domain_results = get_bindings_from_sparql_query(domain_query, query_type='domain')
                    #print(f"domain res: {domain_results}")
                        
                    if domain_results == {}:
                        triple_dict[triple_as_key]["has Domain"] = False
                    else:
                        triple_dict[triple_as_key]["has Domain"] = True
                        triple_dict[triple_as_key]["Domain"] = domain_results
                        
                    range_query = range_check.substitute(item=predicate)
                    #print(range_query)
                    range_results = get_bindings_from_sparql_query(range_query, query_type='range')
                    #print(f"range res: {range_results}")
                        
                    if range_results == {}:
                        triple_dict[triple_as_key]["has Range"] = False
                    else:
                        triple_dict[triple_as_key]["has Range"] = True
                        triple_dict[triple_as_key]["Range"] = range_results 
                        
                    if triple_dict[triple_as_key]["has Domain"] == True and triple_dict[triple_as_key]["has Range"] == True:
                        triple_dict[triple_as_key]["Predicate has Domain & Range"] = True
                        has_domain_range += 1
                    else:
                        triple_dict[triple_as_key]["Predicate has Domain & Range"] = False

                if subject != 'no-wikiID':
                    ins_of_query = instanceOf_check.substitute(item=subject)
                    insOf_results = get_bindings_from_sparql_query(ins_of_query, query_type='instanceOf')
                    triple_dict[triple_as_key]["Subject instanceOf"] = insOf_results
                    
                    subclass_of_query = subclassOf_check.substitute(item=subject)
                    subclass_of_results = get_bindings_from_sparql_query(subclass_of_query, query_type='subclassOf')
                    triple_dict[triple_as_key]["Subject subclassOf"] = subclass_of_results
                    
                    subject_types = merge_dicts(insOf_results, subclass_of_results)
                    domain_match, domain_matching_level, matched_domain_wikiId, matched_domain_label = find_matching_classes(subject_types, domain_results)
                    domain_matching_level = convert_match_level_to_integer(domain_matching_level)
                    
                    if domain_match == True:
                        triple_dict[triple_as_key]["Domain match"] = True
                        triple_dict[triple_as_key]["Domain matching level"] = domain_matching_level
                        triple_dict[triple_as_key]["Domain matched label"] = matched_domain_label
                        triple_dict[triple_as_key]["Domain matched wikiID"] = matched_domain_wikiId
                    else:
                        triple_dict[triple_as_key]["Domain match"] = False
                        
                    if triple_dict[triple_as_key]["Predicate has Domain & Range"] == True and object == 'no-wikiID':
                        has_domain_range_only_subject_has_wikiId += 1
                        triple_dict[triple_as_key]["Object not found in Wikidata"] = True
                        if triple_dict[triple_as_key]["Domain match"] == True:
                            has_domain_range_only_subject_has_wikiId_and_match += 1
                        
                if object != 'no-wikiID':
                    insOf_query2 = instanceOf_check.substitute(item=object)
                    insOf_results2 = get_bindings_from_sparql_query(insOf_query2, query_type='instanceOf')
                    triple_dict[triple_as_key]["Object instanceOf"] = insOf_results2
                    
                    subclass_of_query2 = subclassOf_check.substitute(item=object)
                    subclass_of_results2 = get_bindings_from_sparql_query(subclass_of_query2, query_type='subclassOf')
                    triple_dict[triple_as_key]["Object subclassOf"] = subclass_of_results2
                    
                    object_types = merge_dicts(insOf_results2, subclass_of_results2)
                    range_match, range_matching_level, matched_range_wikiID, matched_range_label = find_matching_classes(object_types, range_results)
                    range_matching_level = convert_match_level_to_integer(range_matching_level)
                    
                    if range_match == True:
                        triple_dict[triple_as_key]["Range match"] = True
                        triple_dict[triple_as_key]["Range matching level"] = range_matching_level
                        triple_dict[triple_as_key]["Range matched label"] = matched_range_label
                        triple_dict[triple_as_key]["Range matched wikiID"] = matched_range_wikiID
                    else:
                        triple_dict[triple_as_key]["Range match"] = False  
                        
                    if triple_dict[triple_as_key]["Predicate has Domain & Range"] == True and subject == 'no-wikiID':
                        has_domain_range_only_object_has_wikiId += 1
                        triple_dict[triple_as_key]["Subject not found in Wikidata"] = True
                        if triple_dict[triple_as_key]["Range match"] == True:
                            has_domain_range_only_object_has_wikiId_and_match += 1
                        
                if triple_dict[triple_as_key]["Predicate has Domain & Range"] == True and subject == 'no-wikiID' and object == 'no-wikiID':
                    has_domain_range_no_subject_no_object += 1
                    triple_dict[triple_as_key]["Both subject and object not found in Wikidata"] = True
                    
                if 'no-wikiID' not in wiki_triple:
                    triples_with_all_components_in_wikidata += 1
                    triple_dict[triple_as_key]["All components in Wikidata"] = True
                    statement_check = check_triple_exists(statement_check_template, endpoint_url, wiki_triple)

                    if statement_check == True:
                        statement_matches += 1
                        triple_dict[triple_as_key]["Triple statement in Wikidata"] = True  
                    else: 
                        triple_dict[triple_as_key]["Triple statement in Wikidata"] = False
                            
                    if triple_dict[triple_as_key]["Predicate has Domain & Range"]==True and triple_dict[triple_as_key]["Domain match"] == True and triple_dict[triple_as_key]["Range match"] == True:
                        domain_range_matches += 1
                        triple_dict[triple_as_key]["Domain&Range Match"] = True
                        triple_level_match = max(domain_matching_level, range_matching_level)
                        triple_dict[triple_as_key]["Triple matching level"] = triple_level_match
                        if triple_level_match == 0:
                            zero_hop_matches += 1
                        if triple_level_match == 1:
                            one_hop_matches += 1
                        if triple_level_match == 2:
                            two_hop_matches += 1
                        if triple_level_match == 3:
                            three_hop_matches += 1  
                    else:
                        triple_dict[triple_as_key]["Domain&Range Match"] = False
                        
                    if triple_dict[triple_as_key]["Domain&Range Match"] == True and statement_check == True:
                        triple_dict[triple_as_key]["Both Statement and Domain&Range Match"] = True
                        both_statement_and_domain_range_matches += 1 
                else:
                    triple_dict[triple_as_key]["All components in Wikidata"] = False
                    
                #for k, v in triple_dict[triple_as_key].items():
                    #print(k)
                    #print(v)
                    #print()
        
        print(f'Number of triples: {len(all_triples)} from {file}')
        print(f'Number of malformed triples: {len(malformed_triples)} from {file}')  
        print(f'Number of triples all components in Wikidata: {triples_with_all_components_in_wikidata} from {file}')
        print(f'Number of statements in Wikidata: {statement_matches} from {file}')
        print(f'Number of triples with matching domain&range: {domain_range_matches} from {file}')
        print(f'Number of triples with both statement and domain&range in Wikidata: {both_statement_and_domain_range_matches} from {file}')
        
        end_time = time.time()
        elapsed_time = (end_time - start_time) / 60
        logging.info(f"Evaluation time: {elapsed_time:.2f} minutes")
        
        results_dict = { "Evaluated file": file,
                        "Evaluation time": f"{elapsed_time:.2f} minutes",
                        'Number of extracted triples': len(all_triples), 
                        'Number of malformed triples': len(malformed_triples), 
                        'Number of triples has domain&range in Wikidata': has_domain_range,
                        'Number of triples with matching domain&range in Wikidata': domain_range_matches,
                        'Number of triples with zero hop match': zero_hop_matches,
                        'Number of triples with one hop match': one_hop_matches,
                        'Number of triples with two hop match': two_hop_matches,
                        'Number of triples with three hop match': three_hop_matches,
                        'Number of triples has domain&range in Wikidata and only subject has wikiID (obj=no-wikiID)': has_domain_range_only_subject_has_wikiId,
                        'Number of triples has domain&range in Wikidata and only subject has wikiID (obj=no-wikiID) and the domain matches': has_domain_range_only_subject_has_wikiId_and_match,
                        'Number of triples has domain&range in Wikidata and only object has wikiID (sbj=no-wikiID)': has_domain_range_only_object_has_wikiId,	
                        'Number of triples has domain&range in Wikidata and only object has wikiID (sbj=no-wikiID) and range matches': has_domain_range_only_object_has_wikiId_and_match,
                        'Number of triples has domain&range but subject and object both NOT found in Wikidata': has_domain_range_no_subject_no_object,

                        'Number of triples with all components in Wikidata': triples_with_all_components_in_wikidata,
                        'Number of triples with matching statement in Wikidata': statement_matches,
                        'Number of triples with both statement and domain&range in Wikidata': both_statement_and_domain_range_matches,
                        }
        
        triples_folder = os.path.join(args.out_dir, 'triples')
        if not os.path.exists(triples_folder):
            os.makedirs(triples_folder)
        
        outfile = os.path.join(triples_folder, f'triples_checked_from{file.replace("post_processed_", "_")}')
        with open (outfile, 'w', encoding='utf-8') as f:
            json.dump(triple_dict, f, indent=4, ensure_ascii=False)
            
        results_folder = os.path.join(args.out_dir, 'results')
        
        if not os.path.exists(results_folder):
            os.makedirs(results_folder)
            
        results_file = os.path.join(results_folder, f'results_from{file.replace("post_processed_", "_")}')
        with open (results_file, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, indent=4, ensure_ascii=False)
            
        relations_entities_folder = os.path.join(args.out_dir, 'extracted_relations_and_entities')
        if not os.path.exists(relations_entities_folder):
            os.makedirs(relations_entities_folder)
            
        relations_file = os.path.join(relations_entities_folder, f'relations_from{file.replace("post_processed_", "_")}')
        with open (relations_file, 'w', encoding='utf-8') as f:
            json.dump(list(all_relations), f, indent=4, ensure_ascii=False)
            
        entities_file = os.path.join(relations_entities_folder, f'entities_from{file.replace("post_processed_", "_")}')
        with open (entities_file, 'w', encoding='utf-8') as f:
            json.dump(list(all_entities), f, indent=4, ensure_ascii=False)
    
    logging.info(f"Evaluation of {file} finished. Results saved to {args.out_dir}/results_{file}")
    
if __name__ == "__main__":
    evaluate()
        