from langchain_core.prompts import PromptTemplate
from tqdm import tqdm
import json
import os
import argparse
import logging
import requests
from tqdm import tqdm
from retry import retry
import requests_cache

# Enable cache and specify the cache name (it will be stored in a file with this name)
requests_cache.install_cache('wikidata_cache', backend='sqlite', expire_after=172800)  # Cache expires after 48 hours (in seconds)

logging.basicConfig(level=logging.INFO)
logging.info('Start Logging')


def read_data(path_to_examples):
    """Read from an external file. List of dicts.
        Dicts keys: "text", "triples", "wiki_triples"
    """	
    data = []
    with open(path_to_examples, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            line = json.loads(line)
            data.append(line) 
    return data


def get_fixed_prompt_components(path_to_prompt_components):
    """Read from an external file: json file
    """	
    with open(path_to_prompt_components, 'r', encoding='utf-8') as f:
        prompt_dict = json.load(f)
        
    return prompt_dict

@retry(tries=3, delay=2, max_delay=25)    
def wikidata_string_search(query_string, query_type="entity"):
    url = "https://www.wikidata.org/w/api.php"
    if query_type == "entity":
        params = {
            "action": "wbsearchentities",
            "format": "json",
            "language": "en",
            "uselang": "en",
            "search": query_string,  # Search term
            "limit": 10,          # Number of search results to return
            "type": "item",
            "sort": "relevance",  # Sort the results by relevance
            'props': 'info|labels|descriptions|aliases'
        }
    elif query_type == "property":
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

@retry(tries=3, delay=2, max_delay=25)    
def get_label_and_description_for_id(wikidata_id):
    """
    Get the label and description for a single Wikidata entity ID.

    :param wikidata_id: The Wikidata entity ID (e.g., 'Q42').
    :return: A dictionary containing the label and description for the entity.
    """
    base_url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbgetentities",
        "format": "json",
        "languages": "en",
        "props": "labels|descriptions",
        "ids": wikidata_id,
    }

    # Make the request to the Wikidata API
    response = requests.get(base_url, params=params)
    data = response.json()

    # Extract the entity information from the response
    entities = data.get("entities", {})
    entity_data = entities.get(wikidata_id, {})
    label = entity_data.get("labels", {}).get("en", {}).get("value", "No label available")
    description = entity_data.get("descriptions", {}).get("en", {}).get("value", "No description available")

    # Return the result as a dictionary
    result = f"{wikidata_id} ({label}): {description}"

    return result

@retry(tries=3, delay=2, max_delay=25)    
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
        candidate = get_label_and_description_for_id(result['title'])
        pages.append(candidate)
    
    return pages

  
def main():  
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--input_file', type=str, default='Entity_Linking/data/test.jsonl', help='test file to see the target triples')
    parser.add_argument('--candidate_strategy', type=str, default='page_search', help='Candidate strategy to get the candidates: string_search or page_search')
    parser.add_argument('--prompt_components', type=str, default='Entity_Linking/prompts/prompt_templates/EL_templates/no_demonstration_prompt.json', help='Prompt components')
    parser.add_argument('--output_dir', type=str, default='Entity_Linking/prompts/EL_prompts', help='Output directory to save prompts')    
    args = parser.parse_args()
    
    if not os.path.exists(args.output_dir): # Create a new directory because it does not exist
        os.makedirs(args.output_dir)
        logging.info(f'Created a new directory ({args.output_dir}) to save the data with prompts')
    
    data = read_data(args.input_file)
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

    for i in tqdm(data, total=len(data)): 
        entities = i["entities"]
        relations = i["properties"] 
        for e, v in entities.items():
            text = json.dumps(i["text"].strip())
            extracted_component = v["label"]
            if args.candidate_strategy == "string_search":
                canditates = wikidata_string_search(extracted_component, query_type="entity")
            elif args.candidate_strategy == "page_search":
                canditates = search_wikidata_pages(extracted_component)
            if canditates is None:
                no_candidates.append((e, extracted_component, "entity"))
            prompt = zero_shot_template.format(text = text, extracted_component = extracted_component, candidates = canditates)
            #print(prompt)
            prompts.append({"entity to disambiguate": extracted_component, "correct answer": e, "prompt": prompt})

        for r, v in relations.items():
            text = json.dumps(i["text"].strip())
            extracted_component = v["label"]
            canditates = wikidata_string_search(extracted_component, query_type="property")
            if canditates is None:
                no_candidates.append((r, extracted_component, "relation"))
            prompt = zero_shot_template.format(text = text, extracted_component = extracted_component, candidates = canditates)
            prompts.append({"relation to disambiguate": extracted_component, "correct answer": r, "prompt": prompt})
        
    prompt_template_name = args.prompt_components.split('/')[-1].split('.')[0]

    with open(f'{args.output_dir}/{prompt_template_name}s_{args.candidate_strategy}.json', 'w', encoding='utf-8') as just_prompts:
        json.dump(prompts, just_prompts, indent=4, ensure_ascii=False)

    with open(f'{args.output_dir}/no_candidates_found_{args.candidate_strategy}.json', 'w', encoding='utf-8') as no_cand:
        json.dump(no_candidates, no_cand, indent=4, ensure_ascii=False)
        
    logging.info('Prompts compiled and saved successfully')
    
    
if __name__ == '__main__':
    
    main()
