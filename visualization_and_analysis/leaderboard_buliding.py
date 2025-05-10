import os
import json
from tabulate import tabulate

# Directory containing .json files
folder_path = 'processed_data'

# Keys to exclude from first-level children
excluded_keys = {'data_size', 'score', 'ques_ids'}

# Collect model data
models = []
for filename in os.listdir(folder_path):
    if not filename.endswith('.json'):
        continue
    file_path = os.path.join(folder_path, filename)
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    model_name = os.path.splitext(filename)[0]
    overall_score = data.get('score', 'N/A')

    # Extract first-level child scores
    sub_scores = {}
    for key in sorted(data.keys()):
        if key in excluded_keys:
            continue
        value = data[key]
        if isinstance(value, dict):
            sub_scores[key] = value.get('score', 'N/A')
        else:
            sub_scores[key] = 'N/A'

    models.append({
        'model': model_name,
        'overall_score': overall_score,
        'sub_scores': sub_scores
    })

# Prepare all keys
all_sub_keys = sorted({k for m in models for k in m['sub_scores'].keys()})

# Compute rankings
model_scores = []
for m in models:
    scores = {'overall_score': m['overall_score']}
    for key in all_sub_keys:
        scores[key] = m['sub_scores'].get(key, 'N/A')
    model_scores.append((m['model'], scores))

# Ranking for each score column
def rank_column(score_list):
    sorted_list = sorted([(i, v) for i, v in enumerate(score_list) if isinstance(v, (int, float))], key=lambda x: x[1], reverse=True)
    ranks = [None] * len(score_list)
    for rank, (i, _) in enumerate(sorted_list):
        ranks[i] = rank + 1
    return ranks

# Collect all score columns for ranking
columns = ['overall_score'] + all_sub_keys
column_data = {col: [scores[col] for _, scores in model_scores] for col in columns}
column_ranks = {col: rank_column(vals) for col, vals in column_data.items()}

# Prepare header and table data
header = ['Model'] + [f"{col.replace('_', ' ').title()}" for col in columns]
table_data = []

for idx, (model_name, scores) in enumerate(model_scores):
    row = [model_name]
    for col in columns:
        val = scores[col]
        rank = column_ranks[col][idx]
        if isinstance(val, (int, float)):
            val_str = f"{val:.2f}({rank})" if rank is not None else f"{val:.2f}"
        else:
            val_str = val
        row.append(val_str)
    table_data.append(row)

# Sort table_data by overall_score descending
def extract_sort_key(row):
    val = row[1].split('(')[0]
    try:
        return float(val)
    except ValueError:
        return -float('inf')

table_data.sort(key=extract_sort_key, reverse=True)

# Print the table
print(tabulate(table_data, headers=header, tablefmt='github'))

# Optional: Write to file
with open('ranked_scores_table.txt', 'w', encoding='utf-8') as out_f:
    out_f.write(tabulate(table_data, headers=header, tablefmt='github'))