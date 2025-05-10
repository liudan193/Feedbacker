from pathlib import Path
from typing import Union
import os
import json
from tqdm import tqdm
from tenacity import retry, stop_after_attempt, wait_random_exponential
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI


def read_prompt(input_path: Union[str, Path]) -> str:
    """
    Read file content, preferably in Markdown (md) and text (txt) formats.
    Directly return the file content.

    :param input_path: File path
    :return: File content string
    """
    # Check if the file exists
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")
    # Read file content
    with open(input_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return content


def read_jsonl_file(file_path: Union[str, Path], max_sample_size: int = None) -> list:
    data = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line_count, line in enumerate(file):
            if max_sample_size is not None and line_count >= max_sample_size:
                break
            try:
                data.append(json.loads(line.strip()))
            except Exception as e:
                print(f"Skipping invalid JSON line: {line.strip()}. {e}")
    return data


def write_jsonl_file(data: list, file_path: Union[str, Path]) -> list:
    with open(file_path, "w", encoding="utf-8") as file:
        for item in data:
            json_line = json.dumps(item, ensure_ascii=False)
            file.write(json_line + "\n")
    print(f"JSONL file has been saved to {file_path}")


# Use @retry decorator to define a retry mechanism for API call failures. The retry strategy is random exponential backoff, with a maximum of 99999 attempts
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(99999))
def completion_with_backoff_openai_api(client, model, messages, stream=False, **kwargs):
    completions = client.chat.completions.create(model=model, messages=messages, stream=stream, **kwargs)
    return completions


def api_query(messages, model_name, sample_num, base_url, api_key, generation_params):
    client = OpenAI(base_url=base_url, api_key=api_key)
    responses = []
    for _ in range(sample_num):
        # ========= debug =========
        # try:
        #     response = client.chat.completions.create(model=model_name, messages=messages, stream=False)
        #     print(response)
        # except Exception as e:
        #     print(e)
        # =========================
        response = completion_with_backoff_openai_api(client=client, model=model_name, messages=messages, stream=False,
                                                      **generation_params)
        content = response.choices[0].message.content
        responses.append(content)
    return responses


def process_data_async(test_data, model, sample_num, base_url, api_key, generation_params, max_workers=32):
    print(f"process_data started with max workers of {max_workers}")
    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for obj in test_data:
            future = executor.submit(api_query, obj["input_ques"], model, sample_num, base_url, api_key,
                                     generation_params)
            futures.append((future, obj))
        future_to_obj = {future: obj for future, obj in futures}
        for future in tqdm(as_completed(future_to_obj.keys()), total=len(test_data)):  # Process results in completion order
            obj = future_to_obj[future]
            try:
                responses = future.result()
                yield responses, obj
            except Exception as e:
                print(f"Error processing item: {e}")
                continue


def process_data_async_spe_model(test_data, sample_num, generation_params, max_workers=32):
    # Compared to process_data_async, this function allows specifying the model, facilitating simultaneous generation with multiple models
    # test_data[i]["query_model"] as the model
    # test_data[i]["query_base_url"] as the URL
    # test_data[i]["query_api_key"] as the API key
    print(f"process_data started with max workers of {max_workers}")
    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for obj in test_data:
            future = executor.submit(api_query, obj["input_ques"], obj["query_model"], sample_num,
                                     obj["query_base_url"], obj["query_api_key"], generation_params)
            futures.append((future, obj))
        future_to_obj = {future: obj for future, obj in futures}
        for future in tqdm(as_completed(future_to_obj.keys()), total=len(test_data)):  # Process results in completion order
            obj = future_to_obj[future]
            try:
                responses = future.result()
                yield responses, obj
            except Exception as e:
                print(f"Error processing item: {e}")
                continue


if __name__ == "__main__":
    prompt_content = read_prompt("./data/prompts/test.json")
    print(prompt_content)