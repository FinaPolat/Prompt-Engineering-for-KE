import json
import random

def shuffle_and_split_jsonl(input_file, output_file1, output_file2, split_ratio=0.50):
    """
    Reads a JSONL file, randomly shuffles the entries, splits them into two pieces,
    and writes the results to two separate files.

    :param input_file: Path to the input JSONL file.
    :param output_file1: Path to the first output JSONL file.
    :param output_file2: Path to the second output JSONL file.
    :param split_ratio: Ratio to split the data (default is 0.5, meaning 50%-50% split).
    """
    # Read the JSONL file
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Parse JSON lines
    data = [json.loads(line) for line in lines]

    # Shuffle the data
    random.shuffle(data)

    # Determine the split index
    split_index = int(len(data) * split_ratio)

    # Split the data
    data1 = data[:split_index]
    print(len(data1))
    data2 = data[split_index:]
    print(len(data2))   

    # Write the first part to the first output file
    with open(output_file1, 'w', encoding='utf-8') as f:
        for item in data1:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    # Write the second part to the second output file
    with open(output_file2, 'w', encoding='utf-8') as f:
        for item in data2:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

# Example usage
input_file = 'Entity_Linking/data/validation.jsonl'
output_file1 = 'Entity_Linking/data/for_task_demonstrations.jsonl'
output_file2 = 'Entity_Linking/data/validation_after_task_demonstrations.jsonl'
shuffle_and_split_jsonl(input_file, output_file1, output_file2)
