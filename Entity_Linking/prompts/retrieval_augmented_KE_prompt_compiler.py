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
            line["triples"] = json.dumps(line["triples"]).replace('{', '{{').replace('}', '}}')
            line["wiki_triples"] = json.dumps(line["wiki_triples"]).replace('{', '{{').replace('}', '}}')
            #print(line)
            data.append(line) 
    return data
    

def get_fixed_prompt_components(path_to_prompt_components):
    """Read from an external file: json file
    """	
    with open(path_to_prompt_components, 'r', encoding='utf-8') as f:
        prompt_dict = json.load(f)
        
    return prompt_dict
        
  
def main():  
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--input_file', type=str, default='Entity_Linking/data/test.jsonl', help='Input file')
    parser.add_argument('--task', type=str, default='EL', help='Task name')
    parser.add_argument('--demonstration_file', type=str, default='Entity_Linking/data/for_task_demonstrations.jsonl', help='File to select task demonstrations')
    parser.add_argument('--prompt_template', type=str, default='Entity_Linking/prompt_templates/KE_templates/one_demonstration_with_wikiIDs_prompt.json', help='Prompt components')
    parser.add_argument('--example_selector', type=str, default='max_marginal_relevance', help='Example selector type')
    parser.add_argument('--k', type=int, default=1, help='number of example to add to the prompt')
    parser.add_argument('--output_dir', type=str, default='Entity_Linking/prompts/EL', help='Output directory to save prompts')    
    args = parser.parse_args()
    

    if not os.path.exists(args.output_dir): # Create a new directory because it does not exist
        os.makedirs(args.output_dir)
        logging.info(f'Created a new directory ({args.output_dir}) to save the data with prompts')
        
    data = read_data(args.input_file)
    total_instances = len(data) 
    task_demonstrations = read_data(args.demonstration_file)
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
    prompt_template_name = f'{args.task}_{prompt_template_name}'
    #print(prompt_template_name)
        
    input_file = args.input_file.split('/')[-1]
    input_file = input_file.split('.')[0]   
    
    prompts = []
    # Wrap the loop with tqdm to create a progress bar
    for index, instance in enumerate(tqdm(data, desc=f"Compiling prompts and writing them to outfile", total=total_instances)):
        #if index == 0:
            #print(instance.keys())  
        text = instance['text']
        #print(text)
        prompt = few_shot_template.format(text = text)
        #print(prompt)
        prompts.append(prompt)

    with open(f'{args.output_dir}/{prompt_template_name}s_{input_file}.json', 'w', encoding='utf-8', ) as just_prompts:
        json.dump(prompts, just_prompts, indent=4, ensure_ascii=False)
        
    logging.info('Prompts compiled and saved successfully')
    
    
if __name__ == '__main__':
    
    main()
