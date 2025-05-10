import json
import os
from collections import defaultdict
import numpy as np
import copy


def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_jsonl(file_path):
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line.strip()))
    return data


def save_json(data, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def calculate_leaf_scores(tree, jsonl_data):
    # Process each domain individually
    domains = tree.keys()
    for domain in domains:
        jsonl_data_domain = [obj for obj in jsonl_data if obj["meta_data"]["domain"] == domain]
        tree_domain = copy.deepcopy(tree[domain])

        # print(domain, len(jsonl_data_domain))

        def traverse(node, jsonl_data_domain):
            # Recursively traverse the tree to find leaf nodes
            new_tree = {}
            for key, value in node.items():
                if value == {}:  # Leaf node
                    # Perform operations on leaf nodes to get new values
                    all_linked_data_id = []
                    all_linked_data_score = []
                    for obj in jsonl_data_domain:
                        type_tags = [item for sublist in obj["meta_data"]["type_tags"].values() for item in sublist]
                        if key in type_tags:
                            all_linked_data_id.append(obj["id"])
                            all_linked_data_score.append(min(500, obj["score"]))
                    new_tree[key] = {"data_size": len(all_linked_data_score),
                                     "score": sum(all_linked_data_score) / len(all_linked_data_score),
                                     "ques_ids": all_linked_data_id}
                else:  # Non-leaf node, process recursively
                    new_tree[key] = traverse(value, jsonl_data_domain)
            return new_tree

        tree[domain] = traverse(tree_domain, jsonl_data_domain)
    return tree


def calculate_non_leaf_scores(tree, jsonl_data):
    # 1) Create id->score mapping
    id_to_score = {obj['id']: min(500, obj["score"]) for obj in jsonl_data}

    def traverse(node):
        # If it's already a leaf (contains data_size & score), return directly
        if 'data_size' in node and 'score' in node:
            return node
        aggregated = {}
        unique_ids = set()
        # 2) Process child nodes recursively
        for child_name, child_node in node.items():
            scored_child = traverse(child_node)
            aggregated[child_name] = scored_child
            unique_ids.update(scored_child.get('ques_ids', []))
        # 3) Calculate data_size and average score after deduplication
        avg_score = sum(id_to_score[qid] for qid in unique_ids) / len(unique_ids)
        # 4) Return with original subtree structure preserved
        return {
            'data_size': len(unique_ids),
            'score': avg_score,
            'ques_ids': list(unique_ids),
            **aggregated
        }

    # Process each domain separately
    scored_tree = {}
    for domain, subtree in tree.items():
        scored_tree[domain] = traverse(copy.deepcopy(subtree))
    scored_tree['data_size'] = len(jsonl_data)
    scored_tree['score'] = sum([min(500, obj["score"]) for obj in jsonl_data]) / len(jsonl_data)
    scored_tree['ques_ids'] = [obj["id"] for obj in jsonl_data]

    return scored_tree


def ranking_by_query_type(current_tree, current_model_name, jsonl_files):
    """
    Traverse the tree to get the rankings of all nodes across all jsonl_files (based on score)
    current_tree: The tree with scores already calculated for the current model
    current_model_name: The name of the current model being processed
    jsonl_files: List of all model filenames
    Returns a tree with ranking information
    """
    # Store scores of all models for each path
    path_scores = defaultdict(dict)

    # Collect scores for the current model for all paths
    def collect_scores(node, model_name, path="root"):
        # Process root node
        if path == "root":
            path_scores[path][model_name] = node.get("score", 0)

        # Traverse child nodes
        for key, value in node.items():
            if key not in ["data_size", "score", "ques_ids"]:  # These are node attributes, not child nodes
                current_path = f"{path}.{key}" if path != "root" else key

                # If the child node has a score attribute, collect it
                if isinstance(value, dict) and "score" in value:
                    path_scores[current_path][model_name] = value["score"]

                # Continue recursively processing deeper nodes
                if isinstance(value, dict):
                    collect_scores(value, model_name, current_path)

    # Collect scores for the current model
    collect_scores(current_tree, current_model_name)

    # Process scores for other models (assuming they have been calculated and saved)
    tree_file = 'cata_tree.json'
    input_folder_path = "evaluation_source_data"
    output_folder_path = "processed_data"

    for model_name in jsonl_files:
        if model_name == current_model_name:
            continue  # Skip the current model as it's already processed

        # Try to load from processed output files
        processed_file = os.path.join(output_folder_path, f"{model_name}.json")
        if os.path.exists(processed_file):
            try:
                model_tree = load_json(processed_file)
                collect_scores(model_tree, model_name)
                continue  # Successfully loaded, continue to next model
            except:
                pass  # If loading fails, continue with recalculation below

        # If no processed file exists, recalculate
        model_tree = load_json(tree_file)
        jsonl_file = os.path.join(input_folder_path, f"{model_name}.jsonl")

        try:
            model_jsonl_data = load_jsonl(jsonl_file)
            leaf_score_tree = calculate_leaf_scores(model_tree, model_jsonl_data)
            all_score_tree = calculate_non_leaf_scores(leaf_score_tree, model_jsonl_data)
            collect_scores(all_score_tree, model_name)
        except Exception as e:
            print(f"Error processing {model_name}: {e}")
            # If processing a model fails, skip it but continue with others

    # Calculate rankings for each path
    path_rankings = {}
    for path, scores in path_scores.items():
        # Sort by score in descending order
        ranked_models = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        # Create ranking mapping
        rankings = {model: rank + 1 for rank, (model, _) in enumerate(ranked_models)}
        path_rankings[path] = rankings

    # Add ranking information to the original tree
    def add_rankings(node, path="root"):
        # Add ranking for current node
        if path in path_rankings and current_model_name in path_rankings[path]:
            node["ranking"] = path_rankings[path][current_model_name]

        # Process child nodes
        for key, value in list(node.items()):
            if key not in ["data_size", "score", "ques_ids", "ranking"]:
                current_path = f"{path}.{key}" if path != "root" else key

                if isinstance(value, dict):
                    add_rankings(value, current_path)

        # Rearrange keys in specified order
        if isinstance(node, dict):
            ordered_keys = ["data_size", "score", "ranking", "ques_ids"]
            ordered_dict = {k: node[k] for k in ordered_keys if k in node}

            # Add other keys
            for k in sorted([k for k in node if k not in ordered_keys]):
                ordered_dict[k] = node[k]

            # Replace original node content
            for k in list(node.keys()):
                del node[k]
            node.update(ordered_dict)

        return node

    # Add rankings to the tree
    result_tree = add_rankings(copy.deepcopy(current_tree))

    return result_tree


def main():
    # File paths
    tree_file = 'cata_tree.json'
    input_folder_path = "evaluation_source_data"
    output_folder_path = "processed_data"
    jsonl_files = [f[:-6] for f in os.listdir(input_folder_path) if f.endswith('.jsonl')]

    # First calculate score trees for all models
    models_trees = {}
    for jsonl_file_name in jsonl_files:
        print(f"Processing {jsonl_file_name}...")
        jsonl_file = os.path.join(input_folder_path, f"{jsonl_file_name}.jsonl")

        # Load data
        tree = load_json(tree_file)
        jsonl_data = load_jsonl(jsonl_file)
        print(f"Loaded {len(jsonl_data)} records from {jsonl_file_name}")

        # Traverse leaf nodes to get scores for all leaf nodes
        leaf_score_tree = calculate_leaf_scores(tree, jsonl_data)

        # Traverse the tree to give scores to all non-leaf nodes, preserving tree structure
        all_score_tree = calculate_non_leaf_scores(leaf_score_tree, jsonl_data)

        # Save the calculation results
        models_trees[jsonl_file_name] = all_score_tree

    # Then calculate rankings for each model and save results
    for model_name, model_tree in models_trees.items():
        print(f"Calculating rankings for {model_name}...")
        ranked_score_tree = ranking_by_query_type(model_tree, model_name, jsonl_files)

        output_file = os.path.join(output_folder_path, f"{model_name}.json")
        save_json(ranked_score_tree, output_file)
        print(f"Saved processed data to {output_file}")


if __name__ == '__main__':
    main()

