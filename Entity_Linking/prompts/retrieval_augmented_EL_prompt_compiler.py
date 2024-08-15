# prompt formatter - read from an external file
# example_variables - read from an external file
# prompt template - langChain
# few-shot prompt template - langChain
# prefix + suffix - read from an external file
# examples - read from an external file
# example selector - langChain
# input variables - read from an external file
# outfile - write to an external file

from langchain_community.embeddings import HuggingFaceInstructEmbeddings
from langchain_core.example_selectors import MaxMarginalRelevanceExampleSelector, SemanticSimilarityExampleSelector
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate
from langchain_community.vectorstores import Chroma
import json
import random
import os
import argparse
import logging
from tqdm import tqdm
from retry import retry
import requests
import requests_cache

# Enable cache and specify the cache name (it will be stored in a file with this name)
requests_cache.install_cache('wikidata_cache', backend='sqlite', expire_after=172800)  # Cache expires after 48 hours (in seconds)

logging.basicConfig(level=logging.INFO)
logging.info('Start Logging')


def read_data(path_to_data):
    """Read from an external file. List of dicts.
        Dicts keys: "text", "entities", "properties"
    """	
    data = []
    with open(path_to_data, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            line = json.loads(line)
            data.append(line) 
    return data

def read_examples(path_to_examples):
    """Read from an external file. List of dicts.
        Dicts keys: "text", "entities", "properties"
    """	
    data = []
    with open(path_to_examples, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            line = json.loads(line)
            del line["index"]
            line["text"] = json.dumps(line["text"].strip())
            line["extracted_component"] = json.dumps(line["extracted_component"].strip())
            line["candidates"] = json.dumps(line["candidates"])
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
    
    parser.add_argument('--input_file', type=str, default='Entity_Linking/data/test.jsonl', help='Input file')
    parser.add_argument('--task', type=str, default='EL', help='Task name')
    parser.add_argument('--candidate_strategy', type=str, default='page_search', help='Candidate strategy to get the candidates: string_search or page_search')
    parser.add_argument('--demonstration_file', type=str, default='Entity_Linking/data/for_task_demonstrations_EL_string_search.jsonl', help='File to select task demonstrations')
    parser.add_argument('--prompt_template', type=str, default='Entity_Linking/prompts/prompt_templates/EL_templates/one_demonstration_prompt.json', help='Prompt components')
    parser.add_argument('--example_selector', type=str, default='max_marginal_relevance', help='Example selector type')
    parser.add_argument('--k', type=int, default=1, help='number of example to add to the prompt')
    parser.add_argument('--output_dir', type=str, default='Entity_Linking/prompts/EL_prompts', help='Output directory to save prompts')    
    args = parser.parse_args()
    

    if not os.path.exists(args.output_dir): # Create a new directory because it does not exist
        os.makedirs(args.output_dir)
        logging.info(f'Created a new directory ({args.output_dir}) to save the data with prompts')
        
    data = read_data(args.input_file)
    #data = random.sample(data, 10)
    total_instances = len(data) 
    task_demonstrations = read_examples(args.demonstration_file)
    #print(task_demonstrations[0].keys())
    #print(task_demonstrations[0])
    #print(type(task_demonstrations[0]['triples']))
    
    embeddings = HuggingFaceInstructEmbeddings(query_instruction="Represent the query for retrieval: ")
    k = args.k
    
    if args.example_selector == 'semantic_similarity':
        example_selector = SemanticSimilarityExampleSelector.from_examples(
            task_demonstrations,
            embeddings,
            Chroma,
            k
            )
        
    if args.example_selector == 'max_marginal_relevance':
        example_selector = MaxMarginalRelevanceExampleSelector.from_examples(
            task_demonstrations,
            embeddings,
            Chroma,
            k
            )
        
    prompt_dict = get_fixed_prompt_components(args.prompt_template)
    #print(prompt_dict)
    
    prefix = prompt_dict['prefix']
    example_variables = prompt_dict['example variables']
    #print(example_variables)
    formatter = prompt_dict['formatter']
    input_variables = prompt_dict['input variables']
    #print(input_variables)
    suffix = prompt_dict['suffix']
    
    prompt_template = PromptTemplate(
                input_variables=example_variables,  
                template=formatter,
                )
    
    few_shot_template = FewShotPromptTemplate(
        example_selector= example_selector, 
        example_prompt=prompt_template,
        prefix=prefix,
        suffix=suffix,
        input_variables=input_variables,
        example_separator="\n"
        )
    
    
    prompt_template_name = args.prompt_template.split('/')[-1]
    prompt_template_name = prompt_template_name.split('.')[0]
    prompt_template_name = f'{prompt_template_name}'
    #print(prompt_template_name)
    
    prompts = []
    # Wrap the loop with tqdm to create a progress bar
    for index, instance in enumerate(tqdm(data, desc=f"Compiling prompts and writing them to outfile", total=total_instances)):
        text = json.dumps(instance["text"].strip())
        #print(text)
        entities = instance["entities"]
        relations = instance["properties"] 
        for e, v in entities.items():
            extracted_component = v["label"]
            #print(extracted_component)
            if args.candidate_strategy == "string_search":
                candidates = wikidata_string_search(extracted_component, query_type="entity")
            elif args.candidate_strategy == "page_search":
                candidates = search_wikidata_pages(extracted_component)

            candidates = json.dumps(candidates)
            #print(candidates)
            prompt = few_shot_template.format(text = text, extracted_component=extracted_component, candidates=candidates)
            #print(prompt)
            prompts.append({"index": index, "entity to disambiguate": extracted_component, "correct answer": e, "prompt": prompt})

        for r, v in relations.items():
            extracted_component = v["label"]
            candidates = wikidata_string_search(extracted_component, query_type="property")
            candidates = wikidata_string_search(extracted_component, query_type="property")
            candidates = json.dumps(candidates)
            prompt = few_shot_template.format(text = text, extracted_component=extracted_component, candidates=candidates)
            #print(prompt)
            prompts.append({"index": index, "entity to disambiguate": extracted_component, "correct answer": r, "prompt": prompt})        
    
    with open(os.path.join(args.output_dir, f'{prompt_template_name}_{args.candidate_strategy}.json'), 'w', encoding='utf-8') as f:  
        json.dump(prompts, f, ensure_ascii=False, indent=4)

    logging.info('Prompts compiled and saved successfully')
    
    
if __name__ == '__main__':
    
    main()
