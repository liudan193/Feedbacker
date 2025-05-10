import copy
import os
import json
import random
from tqdm import tqdm
import pandas as pd
import re
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from utils import utils


def find_criteria_by_idx(saved_criteria, id):
    if isinstance(saved_criteria, pd.DataFrame):
        row = saved_criteria[saved_criteria['id'] == id]
        if not row.empty:
            return row.iloc[0]['criteria_with_weights']
        return "Criteria not found."
    else:
        for i in range(len(saved_criteria)):
            if saved_criteria[i]["id"] == id:
                return saved_criteria[i]["extracted_criteria"]
    return "Criteria not found. "


def get_input_data(df_majority_vote, system_prompt, user_prompt, saved_criteria, max_number=None):
    input_data = []

    for i, row in tqdm(df_majority_vote.iterrows(), total=len(df_majority_vote)):

        criteria = find_criteria_by_idx(saved_criteria, row["id"])

        try:
            input_ques = user_prompt.format(question=row['prompt'], criteria=criteria, answer=row['response_a'])
            obj_a = row.to_dict()
            obj_a["response_eval"] = "a"
            obj_a["input_ques"] = [{"role": "system", "content": system_prompt},
                                   {"role": "user", "content": input_ques}]
            input_ques = user_prompt.format(question=row['prompt'], criteria=criteria, answer=row['response_b'])
            obj_b = row.to_dict()
            obj_b["response_eval"] = "b"
            obj_b["input_ques"] = [{"role": "system", "content": system_prompt},
                                   {"role": "user", "content": input_ques}]
            input_data.append(obj_a)
            input_data.append(obj_b)
            # print(f"The winner is: {obj_a['winner']}.")
        except Exception as e:
            print(f"Error at index {i}: {e}")

    return input_data


def get_input_eval(df_majority_vote, prompt, model, base_urls, api_key, id_key_name, use_baseline_ans, max_number=None):
    input_data = []
    for i, row in tqdm(df_majority_vote.iterrows(), total=len(df_majority_vote)):
        try:
            obj = row.to_dict()

            obj_new = copy.deepcopy(obj)
            obj_new[id_key_name] = obj_new[id_key_name] + "_a"
            if not use_baseline_ans:
                obj_new["input_ques"] = [{"role": "user", "content": prompt.format(question=obj_new['prompt'], eval_system=obj_new['criteria'], answer=obj_new['response_a'])}]
            else:
                obj_new["input_ques"] = [{"role": "user", "content": prompt.format(question=obj_new['prompt'], eval_system=obj_new['criteria'], answer=obj_new['response_b'], answer_baseline=obj['ques2ans_responses'][0]['response'])}]
            obj_new["query_model"] = model
            obj_new["query_base_url"] = random.choice(base_urls)
            obj_new["query_api_key"] = api_key
            input_data.append(obj_new)

            obj_new = copy.deepcopy(obj)
            obj_new[id_key_name] = obj_new[id_key_name] + "_b"
            if not use_baseline_ans:
                obj_new["input_ques"] = [{"role": "user", "content": prompt.format(question=obj_new['prompt'], eval_system=obj_new['criteria'], answer=obj_new['response_b'])}]
            else:
                obj_new["input_ques"] = [{"role": "user", "content": prompt.format(question=obj_new['prompt'], eval_system=obj_new['criteria'], answer=obj_new['response_b'], answer_baseline=obj['ques2ans_responses'][0]['response'])}]
            obj_new["query_model"] = model
            obj_new["query_base_url"] = random.choice(base_urls)
            obj_new["query_api_key"] = api_key
            input_data.append(obj_new)

        except Exception as e:
            print(f"Error at index {i}: {e}")

    return input_data


def get_input_data_ques2ans(df_majority_vote, prompt, max_number=None):
    input_data = []
    for i, row in tqdm(df_majority_vote.iterrows(), total=len(df_majority_vote)):
        try:
            obj = row.to_dict()
            obj["input_ques"] = [{"role": "user", "content": prompt.format(question=row['prompt'])}]
            input_data.append(obj)
        except Exception as e:
            print(f"Error at index {i}: {e}")
    return input_data


def get_input_get_criteria(df_majority_vote, prompt, model, base_urls, api_key, max_number=None):
    input_data = []
    for i, row in tqdm(df_majority_vote.iterrows(), total=len(df_majority_vote)):
        try:
            input_ques = prompt.format(question=row['prompt'],
                                       answer_1=row['ques2ans_responses'][0]["response"],
                                       answer_2=row['ques2ans_responses'][1]["response"],
                                       answer_3=row['ques2ans_responses'][2]["response"])
            obj = row.to_dict()
            obj["input_ques"] = [{"role": "user", "content": input_ques}]
            obj["query_model"] = model
            obj["query_base_url"] = random.choice(base_urls)
            obj["query_api_key"] = api_key
            input_data.append(obj)
        except Exception as e:
            print(f"Error at index {i}: {e}")
    return input_data


def get_input_get_weights(df_majority_vote, system_prompt, user_prompt, max_number=None):
    input_data = []
    for i, row in tqdm(df_majority_vote.iterrows(), total=len(df_majority_vote)):
        try:
            input_ques = user_prompt.format(question=row['prompt'], metrics=row['get_criteria'],
                                            answer_1=row['ques2ans_responses'][0]["response"],
                                            answer_2=row['ques2ans_responses'][1]["response"],
                                            answer_3=row['ques2ans_responses'][2]["response"])
            obj = row.to_dict()
            obj["input_ques"] = [{"role": "system", "content": system_prompt}, {"role": "user", "content": input_ques}]
            input_data.append(obj)
        except Exception as e:
            print(f"Error at index {i}: {e}")
    return input_data


def extract_criteria(text):
    # Preprocessing: Normalize symbols
    text = text.replace('%', '').replace('_', '/')
    text = text.replace('\\\\', '/').replace('\\', '/').replace('//', '/')
    # Match lines in the format "number. description | weight"
    pattern = re.compile(
        r"^\s*(\d+)\.\s+(.+?)\s*\|\s*(.+?)\s*$",
        re.MULTILINE
    )
    # Find all matching lines
    matches = pattern.findall(text)
    if not matches:
        print("No content matching the format found, original text as follows:")
        print(text)
        return None
    # Sort matching results by number in ascending order
    matches = sorted(matches, key=lambda x: int(x[0]), reverse=False)
    # Concatenate results
    result = '\n'.join(
        [f"{number}. {description.strip()} | {weight.strip()}" for number, description, weight in matches])
    return result


def extract_score(raw_string: str) -> float:
    # Match all numbers (integer or decimal) following "Weighted Score"
    pattern = r'Weighted Score[^\d-]*(-?\d*\.?\d+)'
    matches = re.findall(pattern, raw_string)
    if matches:
        # Return the last matched number, converted to a float
        return float(matches[-1])
    return None


def filter_processed_data(full_data, save_path_to_test, id_key_name):
    # Read processed unique_id
    processed_unique_ids = set()
    if os.path.exists(save_path_to_test):
        with open(save_path_to_test, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    unique_id = data.get(id_key_name, None)
                    if unique_id is not None:
                        processed_unique_ids.add(unique_id)
                except json.JSONDecodeError:
                    print(f"Warning: JSON decode error in line: {line}")
    # Filter processed data items
    unprocessed_data = [obj for obj in full_data if obj.get('id', None) not in processed_unique_ids]
    return unprocessed_data


def main():

    output_path = "outputs/"
    os.makedirs(output_path, exist_ok=True)

    # ============================================================================
    # 1.1. Generate answers based on the question, used for pre-comparison
    # Since it has already been generated, just retrieve it
    # Configuration
    prompt_path_ques2ans = "./prompts/ours/ours_ques2ans.md"
    prompt = utils.read_prompt(prompt_path_ques2ans)
    ques2ans_models = [{"model_name": "gpt-4o", "base_url": "http://localhost:8004", "api_key": "any"},
                       {"model_name": "deepseek-v3", "base_url": "http://localhost:8004", "api_key": "any"},
                       {"model_name": "doubao-pro-1.5-32k", "base_url": "http://localhost:8004", "api_key": "any"}]
    input_data_path = "./data/evaluation_dataset_v0.1.jsonl"
    input_data = utils.read_jsonl_file(input_data_path)
    ques2ans_data_1 = utils.read_jsonl_file(os.path.join(output_path, f"generation/{ques2ans_models[0]['model_name']}.jsonl"))
    ques2ans_data_2 = utils.read_jsonl_file(os.path.join(output_path, f"generation/{ques2ans_models[1]['model_name']}.jsonl"))
    ques2ans_data_3 = utils.read_jsonl_file(os.path.join(output_path, f"generation/{ques2ans_models[2]['model_name']}.jsonl"))
    new_data = []
    for obj in input_data:
        for temp_obj in ques2ans_data_1:
            if obj["id"] == temp_obj["id"]:
                obj1 = temp_obj
                break
        for temp_obj in ques2ans_data_2:
            if obj["id"] == temp_obj["id"]:
                obj2 = temp_obj
                break
        for temp_obj in ques2ans_data_3:
            if obj["id"] == temp_obj["id"]:
                obj3 = temp_obj
                break
        obj["ques2ans_responses"] = [
            {"ques2ans_res_id": 1, "model_name": ques2ans_models[0]["model_name"], "response": obj1["responses"][0]},
            {"ques2ans_res_id": 2, "model_name": ques2ans_models[1]["model_name"], "response": obj2["responses"][0]},
            {"ques2ans_res_id": 3, "model_name": ques2ans_models[2]["model_name"], "response": obj3["responses"][0]},
        ]
        new_data.append(obj)
    save_path = os.path.join(output_path, "ours_ques2ans_3.jsonl")  # Save directory
    utils.write_jsonl_file(new_data, save_path)
    # ============================================================================

    # ============================================================================
    # 1.2. Generate criteria and weights based on answers
    print("=" * 50)
    print("Generating criteria and weights")
    # Configuration
    prompt_path_get_criteria = "./prompts/ours/ours_get_criteria.md"
    prompt = utils.read_prompt(prompt_path_get_criteria)
    model_info = {
        "model_name": "QwQ-32B",
        "base_urls": ["http://localhost:8004", "http://localhost:8004"],
        "api_key": "any"
    }
    generation_params = {}
    sample_num = 1
    max_workers = int(200 * len(model_info["base_urls"]) / sample_num)
    id_key_name = "id"

    input_data_path = "./outputs/ours_ques2ans_3.jsonl"
    input_data = utils.read_jsonl_file(input_data_path)
    model, base_urls, api_key = model_info["model_name"], model_info["base_urls"], model_info["api_key"]
    test_data = get_input_get_criteria(pd.DataFrame(input_data), prompt, model, base_urls, api_key)
    save_path = os.path.join(output_path, "ours_get_criteria.jsonl")  # Save directory

    # Obtain LLM generated results and save them in real-time
    unprocessed_data = filter_processed_data(test_data, save_path, id_key_name)
    print("Remaining data to process:", len(unprocessed_data))
    if len(unprocessed_data) != 0:
        with open(save_path, 'a', encoding='utf-8') as f:
            for responses, obj in utils.process_data_async_spe_model(unprocessed_data, sample_num, generation_params, max_workers=max_workers):
                for key in ['query_model', 'query_base_url', 'query_api_key', 'input_ques']:
                    if key in obj:
                        del obj[key]
                obj["criteria"] = extract_criteria(responses[0])
                if obj["criteria"]:
                    f.write(json.dumps(obj, ensure_ascii=False) + '\n')
                    f.flush()
                    os.fsync(f.fileno())

    criteria_data = utils.read_jsonl_file(save_path)
    print(f"Filtered data saved to {save_path}, total valid entries: {len(criteria_data)}")
    # ============================================================================


if __name__ == "__main__":
    main()