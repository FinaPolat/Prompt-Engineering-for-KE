from langchain_core.prompts import PromptTemplate
from tqdm import tqdm
import json
import os
import argparse
import logging
import requests
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logging.info('Start Logging')

def read_json(file):
    with open(file, 'r', encoding='utf-8') as f:
        return json.load(f)


def read_data(path_to_examples):
    """Read from an external file. List of dicts.
        Dicts keys: "text", "triples", "wiki_triples"
    """	
    data = []
    with open(path_to_examples, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            line = json.loads(line)
            line["text"] = json.dumps(line["text"].strip())
            line["triples"] = json.dumps(line["triples"])
            line["wiki_triples"] = json.dumps(line["wiki_triples"])
            data.append(line) 
    return data


def get_fixed_prompt_components(path_to_prompt_components):
    """Read from an external file: json file
    """	
    with open(path_to_prompt_components, 'r', encoding='utf-8') as f:
        prompt_dict = json.load(f)
        
    return prompt_dict

def get_wikidata_candidates(query_string, quert_type="entity"):
    url = "https://www.wikidata.org/w/api.php"
    if quert_type == "entity":
        params = {
            "action": "query",
            "list": "search",
            "srsearch": "paradox",  # Search term
            "srlimit": 10,          # Number of search results to return
            "format": "json"
        }

    elif quert_type == "property":
        params = {
            "action": "wbsearchentities",
            "format": "json",
            "language": "en",
            "uselang": "en",
            "search": query_string,
            "limit": 10,  # Increase the limit to get more results
            "type": "property",
            "sort": "relevance",  # Sort the results by relevance
            'props': 'info|labels|descriptions|aliases'
        }

    response = requests.get(url, params=params)
    data = response.json()

    if "search" in data and len(data["search"]) > 0:
        results = []
        for result in data["search"]:
            wikidata_id = result["id"]
            label = result["label"]
            description = result.get("description", "No description available")
            results.append(f"{wikidata_id} ({label}): {description}")

        return results
    else:
        return None

def search_wikidata_pages(search_term, limit=10):
    """
    Search for pages on Wikidata based on the given search term using the MediaWiki API.

    :param search_term: The term to search for.
    :param limit: The maximum number of search results to return.
    :param language: The language code for the search results.
    :return: A list of dictionaries containing page titles, IDs, and snippets.
    """
    # Define the API endpoint
    url = "https://www.wikidata.org/w/api.php"
    
    # Define the parameters for the search
    params = {
        "action": "query",
        "list": "search",
        "srsearch": search_term,  # Search term
        "srlimit": limit,         # Number of search results to return
        "format": "json",
        "srprop": "snippet"       # To include a snippet of the page
    }
    
    # Make the request
    response = requests.get(url, params=params)
    
    # Parse the JSON response
    data = response.json()
    
    # Extract and return the search results
    pages = []
    for result in data.get('query', {}).get('search', []):
        pages.append({
            'WikiID': result['title'],
            'Page_id': result['pageid'],
            'Description': result['snippet']
        })
    
    return pages


  
def main():  
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--extraction_file', type=str, default='Entity_Linking/generated_output_by_GPT4mini_KE/KE_no_demonstration_prompts_test.json', help='Extraction filewhich stores the LLM generation')
    parser.add_argument('--test_file', type=str, default='Entity_Linking/data/test.jsonl', help='test file to see the target triples')
    parser.add_argument('--prompt_components', type=str, default='Entity_Linking/prompt_templates/EL_templates/no_demonstration_prompt.json', help='Prompt components')
    parser.add_argument('--output_dir', type=str, default='Entity_Linking/prompts/EL', help='Output directory to save prompts')    
    args = parser.parse_args()
    
    if not os.path.exists(args.output_dir): # Create a new directory because it does not exist
        os.makedirs(args.output_dir)
        logging.info(f'Created a new directory ({args.output_dir}) to save the data with prompts')
    
    extraction = read_json(args.extraction_file)
    gold = read_data(args.test_file)


    prompt_dict = get_fixed_prompt_components(args.prompt_components)
    formatter = prompt_dict['formatter']
    #print(formatter)
    input_variables = prompt_dict['input variables']
    #print(input_variables)
    zero_shot_template = PromptTemplate(
                    input_variables=input_variables,  
                    template=formatter,
                    )

    prompts = []
    no_candidates = []

    for i, (e, r) in tqdm(enumerate(zip(extraction, gold)), total=len(extraction)):
        extracted_entities = []
        extracted_relations = []
        #print(e["extraction"])
        extracted_triples = e["extraction"].strip().replace("\n", "").replace("```json", "").replace("```", "")
        extracted_triples = json.loads(extracted_triples)
        
        for triple in extracted_triples:
            extracted_entities.append(triple["subject"])
            extracted_entities.append(triple["object"])
            extracted_relations.append(triple["predicate"])
        
        extracted_entities = list(set(extracted_entities))
        extracted_relations = list(set(extracted_relations))

        for entitiy in extracted_entities:
            text = r["text"]
            extracted_component = entitiy
            canditates = get_wikidata_candidates(entitiy)
            if canditates is None:
                no_candidates.append((entitiy, "entity"))
            prompt = zero_shot_template.format(text = text, extracted_component = extracted_component, candidates = canditates)
            #print(prompt)
            prompts.append({"index": i, "entity to disambiguate": extracted_component, "prompt": prompt})

        for relation in extracted_relations:
            text = r["text"]
            extracted_component = relation
            canditates = get_wikidata_candidates(relation, quert_type="property")
            if canditates is None:
                no_candidates.append((relation, "relation"))
            prompt = zero_shot_template.format(text = text, extracted_component = extracted_component, candidates = canditates)
            prompts.append({"index": i, "relation to disambiguate": extracted_component, "prompt": prompt})
        
    input_file = args.extraction_file.replace("KE_", "EL_").split('/')[-1].split('.')[0]
    prompt_template_name = args.prompt_components.split('/')[-1].split('.')[0]

    with open(f'{args.output_dir}/{prompt_template_name}s_{input_file}.json', 'w', encoding='utf-8') as just_prompts:
        json.dump(prompts, just_prompts, indent=4, ensure_ascii=False)

    with open(f'{args.output_dir}/no_candidates_found_{input_file}.json', 'w', encoding='utf-8') as no_cand:
        json.dump(no_candidates, no_cand, indent=4, ensure_ascii=False)
        
    logging.info('Prompts compiled and saved successfully')
    
    
if __name__ == '__main__':
    
    main()