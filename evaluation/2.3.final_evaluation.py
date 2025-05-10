import subprocess
import os
import argparse
import json
import random
import sys
from tqdm import tqdm
import re
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from utils import utils


# Enable during debugging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)


def get_input_eval(aux_data, generation_data, prompt, model, base_urls, api_key, id_key_name):
    input_data = []
    for i, obj in enumerate(tqdm(aux_data, total=len(aux_data))):
        try:
            obj_gene = None
            for temp_obj in generation_data:
                if temp_obj[id_key_name] == obj[id_key_name]:
                    obj_gene = temp_obj
                    break
            if obj_gene is None:
                continue  # Skip this obj if not found
            obj["input_ques"] = [{"role": "user", "content": prompt.format(
                question=obj['prompt'], eval_system=obj['criteria'], answer=obj_gene["responses"][0],
                answer_baseline=obj['ques2ans_responses'][0]['response'],
                critic_baseline=obj['ques2ans_responses'][0]['score'])}]
            obj["query_model"] = model
            obj["query_base_url"] = random.choice(base_urls)
            obj["query_api_key"] = api_key
            obj["responses"] = obj_gene["responses"]
            input_data.append(obj)
        except Exception as e:
            print(f"Error at index {i}: {e}")
    return input_data


def extract_score(raw_string: str) -> float:
    # Match all numbers (integer or decimal) following "Weighted Score"
    pattern = r'Weighted Score[^\d-]*(-?\d*\.?\d+)'
    matches = re.findall(pattern, raw_string)
    if matches:
        # Return the last matched number, converted to a float
        # return float(matches[-1])
        return min(float(matches[-1]), 300)
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


def parse_args():
    parser = argparse.ArgumentParser(description="Script for evaluation task.")
    parser.add_argument('--model', type=str, default='gpt-4o', help='Model name to use')
    args = parser.parse_args()
    return args


def main():
    # ============================================================================
    # 2.1 Parameter configuration
    # Output root directory
    output_path = "outputs/"
    os.makedirs(output_path, exist_ok=True)
    # Path to the file to be evaluated
    args = parse_args()
    generation_data_path = os.path.join(output_path, f"generation/{args.model}.jsonl")
    id_key_name = "id"
    # Input configuration path, mainly for obtaining prompt, baseline, and baseline evaluation
    aux_data_path = os.path.join(output_path, "data_for_ours_eval_baseline.jsonl")
    # Prompt used for evaluation
    prompt_path_get_eval = "./prompts/ours/ours_baseline_final_judge.md"
    prompt = utils.read_prompt(prompt_path_get_eval)
    # Evaluation model parameters
    model_info = {
        "model_name": "QwQ-32B",
        "base_urls": ["http://localhost:8004", "http://localhost:8004"],
        "api_key": "any"
    }
    generation_params = {}
    sample_num = 1
    max_workers = int(200 * len(model_info["base_urls"]) / sample_num)
    model, base_urls, api_key = model_info["model_name"], model_info["base_urls"], model_info["api_key"]
    # Save directory
    save_path = os.path.join(output_path, f"evaluation/{args.model}.jsonl")

    # ============================================================================
    # 2.2. Obtain score
    print("=" * 50)
    print("Generating final evaluation scores based on criteria and weights; model is:", args.model)
    generation_data = utils.read_jsonl_file(generation_data_path)
    aux_data = utils.read_jsonl_file(aux_data_path)
    test_data = get_input_eval(aux_data, generation_data, prompt, model, base_urls, api_key, id_key_name)
    print(len(test_data))

    # Obtain LLM generated results and save them in real-time
    unprocessed_data = filter_processed_data(test_data, save_path)
    print("Remaining data to process:", len(unprocessed_data))

    if len(unprocessed_data) != 0:
        with open(save_path, 'a', encoding='utf-8') as f:
            for responses, obj in utils.process_data_async_spe_model(unprocessed_data, sample_num, generation_params, max_workers=max_workers):
                for key in ['query_model', 'query_base_url', 'query_api_key', 'input_ques']:
                    if key in obj:
                        del obj[key]
                obj["score"] = extract_score(responses[0])
                if obj["score"] != None:
                    f.write(json.dumps(obj, ensure_ascii=False) + '\n')
                    f.flush()
                    os.fsync(f.fileno())

    # Process previously failed parsing
    score_data = utils.read_jsonl_file(save_path)
    print("Current length:", len(score_data))
    if len(test_data) != len(score_data):
        subprocess.run(['python', '2.3.final_evaluation.py', '--model', args.model])
    else:
        print("Finished")


if __name__ == "__main__":
    main()