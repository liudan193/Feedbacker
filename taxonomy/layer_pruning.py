import os
import argparse
import json


def layer_pruning(tree):
    # Create a new dictionary as the result
    new_tree = {}

    # Iterate through all key-value pairs of the original tree
    for key, value in tree.items():
        # If the value is not a dictionary, copy it directly
        if not isinstance(value, dict):
            new_tree[key] = value
        else:
            # If it is a dictionary with only one child node
            if len(value) == 1:
                # Only keep the parent node, and the value is the value of the child node
                child_key = list(value.keys())[0]
                new_tree[key] = value[child_key]
            else:
                # Recursively process the subtree
                new_tree[key] = layer_pruning(value)

    return new_tree


def filter_tree(tree, max_depth, min_nodes):
    """
    Process the classification of the tree, keep the classification with a maximum of max_depth layers,
    and only keep layers deeper than max_depth if the number of direct child nodes is ≥ min_nodes

    Parameters:
    tree (dict): The input tree structure, represented as a nested dictionary
    max_depth (int): The maximum depth, default is 3
    min_nodes (int): The minimum number of direct child nodes required for layers deeper than max_depth, default is 5

    Returns:
    dict: The processed tree structure
    """

    def process_subtree(subtree, current_depth):
        """Process the subtree"""
        if not subtree:  # Empty dictionary
            return {}

        result = {}

        for key, value in subtree.items():
            if current_depth < max_depth:
                # If the current depth is less than max depth, process the subtree directly
                result[key] = process_subtree(value, current_depth + 1)
            else:
                # If the current depth reaches max depth, check the number of direct child nodes
                direct_child_count = len(value)
                if direct_child_count >= min_nodes:
                    # If the number of direct child nodes meets the requirement, keep it
                    result[key] = process_subtree(value, current_depth + 1)
                else:
                    # If the number of direct child nodes does not meet the requirement, do not keep the child nodes
                    result[key] = {}

        return result

    # Start processing from the root node
    return process_subtree(tree, 1)


if __name__ == "__main__":
    # Command-line argument parsing
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', type=str, default="roleplay", help='domain name')
    args = parser.parse_args()

    # Path configuration
    input_path = "outputs_node_refinement_pruning/"
    output_path = "outputs_layer_pruning/"
    os.makedirs(output_path, exist_ok=True)

    # Layer pruning parameters
    max_depth = 4
    min_nodes = 5
    max_depth -= 1

    # ===============================================================================================
    # Data
    domain = args.domain
    output_save_path = f"{domain}_cata_tree.jsonl"
    if domain not in ["roleplay", "coding", "knowledge", "mathematics", "reasoning", "writing"]:
        print("This domain does not exist")
        exit(0)
    # Read the last line of outputs/{domain}_cata_tree.jsonl that contains the key "tree_after_adding_node"
    with open(f"{input_path}/{domain}_cata_tree.jsonl", 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in reversed(lines):  # Iterate in reverse order
            line = json.loads(line)
            if "new_tree" in line.keys():
                tree = line["new_tree"]
                break

    # ===============================================================================================
    # Parameter processing
    output_save_path = os.path.join(output_path, output_save_path)

    # Processing
    tree = layer_pruning(tree)
    tree = filter_tree(tree, max_depth=max_depth, min_nodes=min_nodes)
    with open(output_save_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(tree, ensure_ascii=False) + '\n')
        f.flush()
