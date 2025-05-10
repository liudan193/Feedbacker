import os
import argparse
import json
from tqdm import tqdm
import re
import random
import numpy as np
import string

import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from utils import utils


def get_input_data(dataset, domain, prompt, models):
    input_data = []
    charset = string.ascii_letters + string.digits
    used_ids = set()
    for i, row in tqdm(enumerate(dataset)):
        try:
            model_config = random.choice(models)
            while True:
                new_id = ''.join(random.choices(charset, k=64))
                if new_id not in used_ids:
                    used_ids.add(new_id)
                    break
            obj = {
                "id": new_id,
                "prompt": "",
                "query_gene_model": model_config["query_model"],
                "meta_data": {
                    "domain": domain,
                    "type_tags": [],
                    "question_quality": []
                },
                "source": {
                    "type_source": {
                        "id": row[0]["id"],
                    },
                    "detail_source": [
                        {"id": row[1]["id"]},
                        {"id": row[2]["id"]},
                        {"id": row[3]["id"]}
                    ]
                },
                "input_ques": [{"role": "user", "content": prompt.format(
                    domain=domain, reference_query=row[0]["prompt"], type_tags=row[0]["meta_data"]["type_tags"],
                    query1=row[1]["prompt"], query2=row[2]["prompt"], query3=row[3]["prompt"])}],  # Temporary
                "query_model": model_config["query_model"],  # Temporary
                "query_base_url": model_config["query_base_url"],  # Temporary
                "query_api_key": model_config["query_api_key"],  # Temporary
            }
            input_data.append(obj)
        except Exception as e:
            print(e)
    return input_data


def parse_label_string(label_str):
    """Parse the original label string and extract JSON data"""
    try:
        if "I cannot generate a question based on the provided base questions" in label_str:
            raise ValueError("I cannot generate a question based on the provided base questions")

        # Match all {...} structures
        pattern = r"<new_query>(.*?)(?:</new_query>|<\\new_query>|</\new_query>)"
        json_matches = re.findall(pattern, label_str, re.DOTALL)
        if json_matches:
            # Take the last matched {...} structure
            json_str = json_matches[-1]
            return json_str
        else:
            raise ValueError("No valid JSON structure found")
    except (AttributeError, json.JSONDecodeError, ValueError) as e:
        print(f"Parsing failed: {e}\nOriginal string: {label_str}")
        return {}


if __name__ == "__main__":
    # Input parameters
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', type=str, default="roleplay", help='domain name')
    args = parser.parse_args()

    # Set fixed global random seed (this needs to be modified)
    np.random.seed(42)
    random.seed(42)

    # Parameters
    generation_params = {}
    output_path = "outputs/"
    os.makedirs(output_path, exist_ok=True)
    sample_num = 1

    models = [{"query_model": "gpt-4.1", "query_base_url": 'http://localhost:8006/', "query_api_key": "any"},
              {"query_model": "deepseek-v3", "query_base_url": 'http://localhost:8006/', "query_api_key": "any"},
              {"query_model": "qwen-max", "query_base_url": 'http://localhost:8006/', "query_api_key": "any"}, ]

    # Prompt
    prompt = utils.read_prompt("prompts/get_new_query.md")

    # Read source file
    seed_data = utils.read_jsonl_file(os.path.join("dataset", "seed_data.jsonl"))
    seed_data = [x for x in seed_data if x["meta_data"]["domain"] == args.domain]

    # Save path
    save_path = os.path.join(output_path, "generated_queries.jsonl")

    # Data count
    DATA_NUM = 5

    # ===============================================================================================

    # Get input
    sampled_data = [random.sample(seed_data, 4) for i in range(DATA_NUM)]
    input_data = get_input_data(sampled_data, args.domain, prompt, models)

    # Get output
    # Read processed unique_id
    processed_unique_ids = set()
    if os.path.exists(save_path):
        with open(save_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    unique_id = data.get('id', None)
                    if unique_id is not None:
                        processed_unique_ids.add(unique_id)
                except json.JSONDecodeError:
                    print(f"Warning: JSON decode error in line: {line}")

    # Filter processed data items && get LLM-generated results and save in real-time
    unprocessed_data = [obj for obj in input_data if obj.get('id', None) not in processed_unique_ids]
    print("Remaining unprocessed data volume:", len(unprocessed_data))
    if len(unprocessed_data) != 0:
        with open(save_path, 'a', encoding='utf-8') as f:
            for responses, obj in utils.process_data_async_spe_model(unprocessed_data, sample_num, generation_params):
                prompt = parse_label_string(responses[0])
                prompt = prompt.strip()
                obj["prompt"] = prompt
                del obj["input_ques"]
                del obj["query_model"]
                del obj["query_base_url"]
                del obj["query_api_key"]
                if not prompt:
                    continue
                f.write(json.dumps(obj, ensure_ascii=False) + '\n')
                f.flush()
