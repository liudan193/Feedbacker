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


def get_input_eval(df_majority_vote, prompt, model, base_urls, api_key, id_key_name, use_baseline_ans, max_number=None):
    input_data = []
    for i, row in tqdm(df_majority_vote.iterrows(), total=len(df_majority_vote)):
        try:
            obj = row.to_dict()
            obj_new = copy.deepcopy(obj)
            obj_new["input_ques"] = [{"role": "user", "content": prompt.format(question=obj_new['prompt'], eval_system=obj_new['criteria'], answer=obj_new['ques2ans_responses'][0]['response'])}]
            obj_new["query_model"] = model
            obj_new["query_base_url"] = random.choice(base_urls)
            obj_new["query_api_key"] = api_key
            input_data.append(obj_new)
        except Exception as e:
            print(f"Error at index {i}: {e}")
    return input_data


def extract_critic_score(raw_string: str) -> str:
    # Match any content between <The Start of Evaluation Result> and <The End of Evaluation Result>
    pattern = r'<The Start of Evaluation Result>(.*?)<The End of Evaluation Result>'
    matches = re.findall(pattern, raw_string, re.DOTALL)
    if matches:
        # Return the last matched string
        if "Weighted Score: [" in matches[-1]:
            return matches[-1]
    return None


def filter_processed_data(full_data, save_path_to_test):
    # Read processed unique_id
    processed_unique_ids = set()
    if os.path.exists(save_path_to_test):
        with open(save_path_to_test, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    unique_id = data.get('id', None)
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
    # 2.1. Obtain score for baseline answer
    print("=" * 50)
    print("Generating final evaluation scores based on criteria and weights")
    use_baseline_ans = False  # Cannot be changed, must be False
    prompt_path_get_eval = "./prompts/ours/ours_final_judge.md"
    prompt = utils.read_prompt(prompt_path_get_eval)
    model_info = {
        "model_name": "QwQ-32B",
        "base_urls": ["http://localhost:8004", "http://localhost:8004"],
        "api_key": "any"
    }
    generation_params = {}
    sample_num = 1
    max_workers = int(200 * len(model_info["base_urls"]) / sample_num)
    id_key_name = "id"

    input_data_path = os.path.join(output_path, "ours_get_criteria.jsonl")
    input_data = utils.read_jsonl_file(input_data_path)
    model, base_urls, api_key = model_info["model_name"], model_info["base_urls"], model_info["api_key"]
    test_data = get_input_eval(pd.DataFrame(input_data), prompt, model, base_urls, api_key, id_key_name, use_baseline_ans)
    save_path = os.path.join(output_path, "data_for_ours_eval_baseline.jsonl")
    # Obtain LLM generated results and save them in real-time
    unprocessed_data = filter_processed_data(test_data, save_path)
    # unprocessed_data = []
    print("Remaining data to process:", len(unprocessed_data))
    if len(unprocessed_data) != 0:
        with open(save_path, 'a', encoding='utf-8') as f:
            for responses, obj in utils.process_data_async_spe_model(unprocessed_data, sample_num, generation_params, max_workers=max_workers):
                for key in ['query_model', 'query_base_url', 'query_api_key', 'input_ques']:
                    if key in obj:
                        del obj[key]
                obj['ques2ans_responses'][0]["score"] = extract_critic_score(responses[0])
                if obj['ques2ans_responses'][0]["score"]:
                    f.write(json.dumps(obj, ensure_ascii=False) + '\n')
                    f.flush()
                    os.fsync(f.fileno())

    score_data = utils.read_jsonl_file(save_path)
    print(f"Filtered data saved to {save_path}, total valid entries: {len(score_data)}")
    # ============================================================================


if __name__ == "__main__":
    main()