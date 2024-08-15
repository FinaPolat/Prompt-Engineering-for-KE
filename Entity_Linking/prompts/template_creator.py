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
    
    prefix = """Entity linking is the process of determining the true identity of an entity or a property extracted from text by linking it to the correct entry in a knowledge base. Given a piece of input text with an extracted component (entity or property) from it and a list of candidates from Wikidata, your goal is to select the candidate that most accurately represents the extracted component based on the contextual information provided in the text. 
    """
    
    example_variables = ["text", "extracted_component", "candidates", "correct_answer"]
    
    formatter = """Here is an example:
        Input text: {text}, 
        Extracted component: {extracted_component},
        Candidates: {candidates},
        Correct answer: {correct_answer}
    """
    input_variables = ["text", "extracted_component", "candidates"]
    
    suffix = """Now it is time to perform entity linking with the following inputs:
        Input text: {text}
        Extracted component: {extracted_component}
        Candidates: {candidates}
        Answer only with the candidate number (wikidata_id) that you think is the correct answer. If none of the candidates match, you can select the option 'None'. Please do not include any additional information or explanation in your answer."""
    
    prompt_dict = {'prefix': prefix, 
                   'formatter': formatter, 
                   'example variables': example_variables, 
                   'input variables': input_variables, 
                   'suffix': suffix
                   }
    #print(prompt_dict)
    return prompt_dict


def write_components_to_file(prompt_dict, path_to_file):
    """Write a prompt to an external file. 
    """
    with open(path_to_file, 'w', encoding="utf-8") as f:
        json.dump(prompt_dict, f, indent=4, ensure_ascii=False)
        
        
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output_dir', type=str, default='Entity_Linking/prompts/prompt_templates/EL_templates', help='Output directory for templates')
    parser.add_argument('--template_name', type=str, default='one_demonstration_prompt', help='Prompt template name')
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
