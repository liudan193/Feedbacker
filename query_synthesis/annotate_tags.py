import os
import argparse
import json
from tqdm import tqdm
import time
from tenacity import retry, stop_after_attempt, wait_random_exponential
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from datasets import Dataset, load_dataset
import re
from collections import Counter
import random
import numpy as np
import string
import allowed_tags

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
            obj["tags_check_model"] = model_config["query_model"]
            obj["query_model"] = model_config["query_model"]
            obj["query_base_url"] = model_config["query_base_url"]
            obj["query_api_key"] = model_config["query_api_key"]

            input_data.append(obj)
        except Exception as e:
            print(e)
    return input_data


def parse_label_string(label_str):
    """Parse the original label string and extract JSON data"""
    try:
        pattern = r'\{([^{}]*)\}(?!.*\{[^{}]*\})'
        # pattern = r'<tags>(.*?)(?:</tags>|<\\tags>|</\tags>|</tags":>)'
        # label_str = label_str.replace("\n", ' ')
        json_matches = re.findall(pattern, label_str, re.DOTALL|re.S)
        # json_matches = re.findall(pattern, label_str)
        if json_matches:
            json_str = json_matches[-1]
            json_str = f"{{{json_str}}}"
            json_str = json_str.replace("'", '"')
            json_str = json_str.replace("\n", ' ')
            json_str = json.loads(json_str)
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
        "writing": utils.read_prompt("./prompts/label_type_writing.md"),
        "roleplay": utils.read_prompt("./prompts/label_type_roleplay.md"),
        "knowledge": utils.read_prompt("./prompts/label_type_knowledge.md"),
        "coding": utils.read_prompt("./prompts/label_type_coding.md"),
        "mathematics": utils.read_prompt("./prompts/label_type_mathematics.md"),
        "reasoning": utils.read_prompt("./prompts/label_type_reasoning.md"),
    }

    # Read source file
    queries_data = utils.read_jsonl_file(os.path.join(output_path, "generated_queries.jsonl"))

    # Save path
    save_path = os.path.join(output_path, "generated_queries_with_tags.jsonl")

    # ===============================================================================================

    def filter_type_tags(type_tags, allowed_tags):
        filtered_tags = {}
        for key, value_list in type_tags.items():
            # Check if the key is in allowed_tags
            if key in allowed_tags:
                # Filter value_list, keeping only the values included in allowed_tags
                filtered_values = [tag for tag in value_list if tag in allowed_tags]
                if filtered_values:  # If the filtered value list is not empty, keep the key and its value
                    filtered_tags[key] = filtered_values
            else:
                # Skip if the key is not in allowed_tags
                continue
        return filtered_tags

    allowed_tags = allowed_tags.get_allowed_tags()

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
                type_tags = parse_label_string(responses[0])
                if not type_tags:
                    continue

                type_tags = filter_type_tags(type_tags, allowed_tags)
                obj["meta_data"]["type_tags"] = type_tags
                del obj["input_ques"]
                del obj["query_model"]
                del obj["query_base_url"]
                del obj["query_api_key"]

                f.write(json.dumps(obj, ensure_ascii=False) + '\n')
                f.flush()
