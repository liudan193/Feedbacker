import os
import argparse
import json
from tqdm import tqdm
import re
import random

import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from utils import utils


def get_input_data(dataset, prompts, models):
    input_data = []
    for i, obj in tqdm(enumerate(dataset)):
        if obj["meta_data"]["domain"] not in prompts.keys():
            continue
        try:
            obj["input_ques"] = [{"role": "user", "content":
                prompts[obj["meta_data"]["domain"]].format(query=obj['prompt'])}]

            # Select model
            model_config = random.choice(models)
            obj["quality_check_model"] = model_config["query_model"]
            obj["query_model"] = model_config["query_model"]
            obj["query_base_url"] = model_config["query_base_url"]
            obj["query_api_key"] = model_config["query_api_key"]

            input_data.append(obj)
        except Exception as e:
            print("Input Error", e)
    return input_data


def parse_label_string(label_str):
    """Parse the original label string and extract JSON data"""
    try:
        # Match all {...} structures
        json_matches = re.findall(r'\{.*?\}', label_str, re.DOTALL)
        if json_matches:
            # Take the last matched {...} structure
            json_str = json_matches[-1]
            # Replace single quotes with double quotes (to handle potential format issues)
            json_str = json_str.replace("'", '"')
            # Convert null to None
            data = json.loads(json_str)
            return data
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

    # Parameters
    generation_params = {}
    output_path = "outputs/"
    os.makedirs(output_path, exist_ok=True)
    sample_num = 1

    # Models
    # models = [{"query_model": "QwQ-32B", "query_base_url": "http://localhost:8006/", "query_api_key": "any"},
    #           {"query_model": "DeepSeek-R1", "query_base_url": "http://localhost:8006/", "query_api_key": "any"},
    #           {"query_model": "o3-mini", "query_base_url": "http://localhost:8006/", "query_api_key": "any"}]
    models = [{"query_model": "doubao-lite-1.5-32k", "query_base_url": 'http://localhost:8006/', "query_api_key": "any"}]

    prompts = {
        "writing": utils.read_prompt("./prompts/Quality-Writing.md"),
        "roleplay": utils.read_prompt("./prompts/Quality-Roleplay.md"),
        "knowledge": utils.read_prompt("./prompts/Quality-Knowledge.md"),
        "coding": utils.read_prompt("./prompts/Quality-Coding.md"),
        "mathematics": utils.read_prompt("./prompts/Quality-Mathematics.md"),
        "reasoning": utils.read_prompt("./prompts/Quality-Reasoning.md"),
    }

    # Read source file
    queries_data = utils.read_jsonl_file(os.path.join(output_path, "generated_queries.jsonl"))

    # Save path
    save_path = os.path.join(output_path, "generated_queries_with_quality.jsonl")

    # ===============================================================================================

    # Get input
    input_data = get_input_data(queries_data, prompts, models)

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
                question_quality = parse_label_string(responses[0])
                obj["meta_data"]["question_quality"] = question_quality.get("question_quality", [])
                del obj["input_ques"]
                del obj["query_model"]
                del obj["query_base_url"]
                del obj["query_api_key"]
                if not question_quality:
                    continue
                f.write(json.dumps(obj, ensure_ascii=False) + '\n')
                f.flush()
