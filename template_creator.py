import json
import os
import argparse 
import logging

logging.basicConfig(level=logging.INFO)
logging.info('Start Logging')


def prompt_component_creator():
    """Create a prompt template from a list of fixed prompt components. 
    prefix + formatter + example_variables + input_variables + suffix
    """
    
    prefix = """Your task is extracting knowledge triples from text. A knowledge triple consists of three elements: subject - predicate - object. 
    Subjects and objects are entities and the predicate is the relation between them. Let's use an example:"""
    
    example_variables = ["Text", "Entities", "Relations", "Entity Types", "Triples"]
    
    #formatter = "\nInput text: {Text},\nEntities to extract: {Entities}, \nRelations to predict: {Relations}, \nTriples to extract: {Triples}, \nCorresponding Wikidata version of the triples: {Wiki Triples}"
    formatter = """Text: {Text} Thought 1: I need to determine the entities. Act 1: Named entity extraction. Observation 1: {Entities} 
    Thought 2: What type of entities do I have?
    Act 2: Named entity tagging
    Observation 2: {Entity Types}
    Thought 3: What are the potential relations between these entities? 
    Act3: List the potential relations
    Observation3: {Relations}
    Thought 4: What are the triples?
    Act4: Form the triples
    Observation4: {Triples}
    Thought5: I have extracted knowledge triples from the input text. 
    Act5: Finish
    Observation5: Task is completed.
    """
    input_variables = [ "Text"]
    
    suffix = "Before answering the query, think and decide your act. Extract the knowledge triples from the following text. Text: {Text} Your answer: "
    
    prompt_dict = {'prefix': prefix, 
                   'formatter': formatter, 
                   'example variables': example_variables, 
                   'input variables': input_variables, 
                   'suffix': suffix
                   }
    
    return prompt_dict


def write_components_to_file(prompt_dict, path_to_file):
    """Write a prompt to an external file. 
    """
    with open(path_to_file, 'w', encoding="utf-8") as f:
        json.dump(prompt_dict, f, indent=4, ensure_ascii=False)
        
        
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output_dir', type=str, default='prompt_templates', help='Output directory for templates')
    parser.add_argument('--template_name', type=str, default='one_shot_ReAct_prompt', help='Prompt template name')
    args = parser.parse_args()
        
    isExist = os.path.exists(args.output_dir)

    if not isExist: # Create a new directory because it does not exist
        os.makedirs(args.output_dir)
        logging.info('Created a new directory to save the prompt templates')
        
    prompt_dict = prompt_component_creator()
    logging.info('Prompt template created')
        
    write_components_to_file(prompt_dict, f'{args.output_dir}/{args.template_name}.json')
    logging.info(f'Prompt template saved to {args.output_dir}/{args.template_name}.json')
    
    
if __name__ == '__main__':
    main()
