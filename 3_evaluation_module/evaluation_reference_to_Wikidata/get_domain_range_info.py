import json
import os
import argparse
from string import Template
from retry import retry
import requests_cache
import requests


def read_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

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


def main():
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--input_dir', type=str, default='3_evaluation_module/evaluation_reference_to_Wikidata/14_Jun_24_evaluation_Llama/extracted_relations_and_entities', help='Directory to read extraction files')

    args = parser.parse_args()
    
    if not os.path.exists(args.input_dir):
        print(f"'{args.input_dir}' does not exist. Please check the folder name and try again.")

    endpoint_url = "https://query.wikidata.org/sparql"

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
    all_stats = []
    for file in os.listdir(args.input_dir):
        if file.startswith("relations"):
            print(file)
            has_domain = 0
            has_range = 0
            has_domain_and_range = 0
            data = read_json_file(os.path.join(args.input_dir, file))
            for i in data:
                relation = i[1]
                if relation == "no-wikiID":
                    continue
                else: 
                    domain_query = domain_check.substitute(item=relation)
                    domain_results = get_bindings_from_sparql_query(domain_query, query_type='domain')
                    if domain_results == {}:
                        #print(f"{relation} has no domain information")
                        domain_info = False
                    else:
                        #print(f"{relation} domain: {domain_results}")
                        domain_info = True
                        has_domain += 1
                    
                    range_query = range_check.substitute(item=relation)
                    range_results = get_bindings_from_sparql_query(range_query, query_type='range')
                    if range_results == {}:
                        #print(f"{relation} has no range information")
                        range_info = False
                    else:
                        #print(f"{relation} range: {range_results}")
                        range_info = True
                        has_range += 1
                    if domain_info and range_info:
                        has_domain_and_range += 1
            all_stats.append({"file": file, 
                              "relations with domain": has_domain, 
                              "relations with range": has_range, 
                              "relations with domain and range": has_domain_and_range})
            
    sorted_by_file = sorted(all_stats, key=lambda x: x['file'])

    with open(f'{args.input_dir}/domain_range_stats.json', "w", encoding="utf-8") as f:
        json.dump(sorted_by_file, f, indent=4, ensure_ascii=False)

 
if __name__ == "__main__":
    main()
