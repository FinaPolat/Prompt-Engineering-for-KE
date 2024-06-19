import json
import os
import argparse

def read_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def main():
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--input_dir', type=str, default='3_evaluation_module/evaluation_reference_to_Wikidata/14_Jun_24_evaluation_Llama/extracted_relations_and_entities', help='Directory to read extraction files')

    args = parser.parse_args()
    
    if not os.path.exists(args.input_dir):
        print(f"'{args.input_dir}' does not exist. Please check the folder name and try again.")
    
    all_stats = []
    for file in os.listdir(args.input_dir):
        print(file)
        data = read_json_file(os.path.join(args.input_dir, file))
        linked = 0
        not_linked = 0
        for i in data:
            if i[1] == "no-wikiID":
                not_linked += 1
            else:
                linked += 1

        if file.startswith("entities"):
            entity_stats = {"file": file, 
                            "all entities": len(data),  # "all entities": "linked entities" + "not linked entities
                            "linked entities": linked, 
                            "not linked entities": not_linked}
            all_stats.append(entity_stats)
            
        if file.startswith("relations"):
            relation_stats = {"file": file, 
                              "all relations": len(data),  # "all relations": "linked relations" + "not linked relations
                              "linked relations": linked, 
                              "not linked relations": not_linked}
            all_stats.append(relation_stats)

    sorted_by_file = sorted(all_stats, key=lambda x: x['file'])

    with open(f'{args.input_dir}/stats.json', "w", encoding="utf-8") as f:
        json.dump(sorted_by_file, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()