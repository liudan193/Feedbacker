import os
import argparse
import json
from tqdm import tqdm
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from utils import utils


def parse_args():
    parser = argparse.ArgumentParser(description="Script for text generation task.")
    parser.add_argument('--model', type=str, default='gpt-4o', help='Model name to use')
    parser.add_argument('--base_url', type=str, default='http://localhost:8404', help='Base URL for the model API')
    parser.add_argument('--api_key', type=str, default='any', help='API key for authentication')
    parser.add_argument('--max_workers', type=int, default=32, help='Maximum number of parallel workers')
    args = parser.parse_args()
    return args


def get_input_data(full_dataset):
    input_data = []
    for i, obj in tqdm(enumerate(full_dataset)):
        try:
            obj["input_ques"] = [{"role": "user", "content": obj['prompt']}]
            input_data.append(obj)
        except Exception as e:
            print(e)
    return input_data


if __name__ == "__main__":
    # Parameters
    args = parse_args()

    generation_params = {}
    output_path = "outputs/"
    sample_num = 1
    max_workers = args.max_workers
    model = args.model
    base_url = args.base_url
    api_key = args.api_key

    os.makedirs(output_path, exist_ok=True)

    # ============================================================================
    # Process input file: Add the prompt to be input into the model to the input file
    input_file_path = os.path.join("data", "evaluation_dataset_v0.1.jsonl")
    test_data = utils.read_jsonl_file(input_file_path)
    test_data = get_input_data(test_data)
    print(len(test_data))

    # ============================================================================
    # Obtain the final results based on the prompt above
    arena_data_with_label_save_path = os.path.join(output_path, f"generation/{model}.jsonl")
    # Read processed unique_id
    processed_unique_ids = set()
    if os.path.exists(arena_data_with_label_save_path):
        with open(arena_data_with_label_save_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    unique_id = data.get('id', None)
                    if unique_id is not None:
                        processed_unique_ids.add(unique_id)
                except json.JSONDecodeError:
                    print(f"Warning: JSON decode error in line: {line}")
    # Filter processed data items
    unprocessed_data = [obj for obj in test_data if obj.get('id', None) not in processed_unique_ids]
    print("Remaining data to process:", len(unprocessed_data))

    if len(unprocessed_data) != 0:
        # Obtain LLM generated results and save them in real-time
        with open(arena_data_with_label_save_path, 'a', encoding='utf-8') as f:
            for responses, obj in utils.process_data_async(unprocessed_data, model, sample_num, base_url, api_key, generation_params, max_workers):
                obj["responses"] = responses
                f.write(json.dumps(obj, ensure_ascii=False) + '\n')
                f.flush()
                os.fsync(f.fileno())

    # Process previously failed parsing
    arena_data_with_label = utils.read_jsonl_file(arena_data_with_label_save_path)
    print("Current length:", len(arena_data_with_label))
    # ============================================================================