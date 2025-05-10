import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from utils import utils

# Read the first jsonl file
output_path = "outputs/"

data1_path = os.path.join(output_path, "generated_queries_with_quality.jsonl")
data2_path = os.path.join(output_path, "generated_queries_with_tags.jsonl")
save_path = os.path.join(output_path, "generated_queries_with_quality_tags.jsonl")

data1 = utils.read_jsonl_file(data1_path)
data2 = utils.read_jsonl_file(data2_path)

merged_data = []
for obj in data1:
    for obj2 in data2:
        if obj['id'] == obj2['id']:
            obj["meta_data"]["type_tags"] = obj2["meta_data"]["type_tags"]
            merged_data.append(obj)
            break

# Save the merged data
utils.write_jsonl_file(merged_data, save_path)

# Output the number of merged data entries
print(len(merged_data))
