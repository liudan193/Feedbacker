import os
import argparse
import json
import re
from functools import partial
import ast

import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from utils import utils


def parse_label_string(label_str):
    """Parse the raw label string and extract JSON data"""
    try:
        # Match all {...} structures
        pattern = r"<decision>(.*?)(?:</decision>|<\\decision>|</\decision>)"
        json_matches = re.findall(pattern, label_str, re.DOTALL)
        if json_matches:
            json_str = json_matches[-1]
            return json_str
        else:
            raise ValueError("No valid JSON structure found")
    except (AttributeError, json.JSONDecodeError, ValueError) as e:
        print(f"Raw string: {label_str}")
        raise e


class TreeProcessor:
    def __init__(self, tree):
        """
        Initialize the tree processor
        :param tree: Tree structure in dictionary format
        """
        self.tree = tree

    def traverse_tree(self, process_callback):
        """
        Traverse the entire tree structure
        :param process_callback: Callback function to process each node
        :return: Processed tree
        """
        return self._traverse_node(self.tree, [], process_callback)

    def _traverse_node(self, node, path, process_callback):
        """
        Recursively traverse nodes
        :param node: Current node
        :param path: Current path
        :param process_callback: Processing callback function
        :return: Processed node
        """
        if not isinstance(node, dict) or not node:
            return node
        if len(node.keys()) == 1:
            return node

        # Get all direct children of the current node
        children_keys = list(node.keys())
        leaf_nodes = [key for key in children_keys if not node[key]]

        # If there are child nodes, pass them to the callback function for processing
        if children_keys:
            # Use LLM to process all child nodes at the current level
            updated_children = process_callback(current_keys=children_keys, leaf_keys=leaf_nodes)
            if "Exceeded max retry limit, abort modification" == updated_children:
                updated_children = {"keep": children_keys}
            else:
                updated_children = ast.literal_eval(updated_children)
                # print("updated_children", updated_children)

            # Update the tree structure based on the returned result
            new_node = {}

            # Handle each operation type
            for op_type, items in updated_children.items():
                if op_type == "keep":
                    # Keep the original nodes, but possibly rename them
                    # "keep": [(old_key)]
                    for old_key in items:
                        # Recursively process the subtree
                        child_path = path + [old_key]
                        child_node = self._traverse_node(node[old_key], child_path, process_callback)
                        new_node[old_key] = child_node

                elif op_type == "merge":
                    # Merge nodes
                    # "merge": [(new_key, [key_to_merge1, key_to_merge2])]
                    for new_key, keys_to_merge in items:
                        merged_node = {}
                        for key in keys_to_merge:
                            # Add content of the nodes to be merged into the new node
                            merged_node.update(node[key])
                        # Recursively process the merged subtree
                        merged_path = path + [new_key]
                        new_node[new_key] = self._traverse_node(merged_node, merged_path, process_callback)

                elif op_type == "split":
                    # Split leaf nodes
                    # split happens only inside leaf nodes, no further recursion is needed
                    # "split": [(old_key, [new_key1, new_key2])]
                    for old_key, sub_items in items:
                        for new_key in sub_items:
                            new_node[new_key] = {}

                elif op_type == "reparent":
                    # Reparent nodes
                    # "reparent": [(parent_key1, [child_key1, child_key2])]
                    for parent_key, child_keys in items:
                        # If the new parent node doesn't exist, create it
                        if parent_key not in new_node:
                            new_node[parent_key] = {}
                        # Move all child nodes to the new parent
                        for child_key in child_keys:
                            child_path = path + [child_key]
                            child_node = self._traverse_node(node[child_key], child_path, process_callback)
                            new_node[parent_key][child_key] = child_node

            return new_node

        return node


# Example LLM decision function
def pruning_node_llm_decision(current_keys, leaf_keys, max_retries, base_url, api_key, model, sample_num,
                              generation_params, file, base_prompt, existing_items):
    """
    This function is the LLM decision process
    Args:
        current_keys (list): All keys of the current node
        leaf_keys (list): All leaf nodes of the current node
    Returns:
        Decision
    """

    # If there are already processed items in the file
    for obj in existing_items:
        if obj["current_keys"] == current_keys:
            return obj["decision"]

    # New query
    obj = {
        "current_keys": current_keys,
        "leaf_keys": leaf_keys,
        "input_ques": [{"role": "user", "content": base_prompt.format(current_keys=current_keys, leaf_keys=leaf_keys)}]
    }
    unprocessed_data = [obj] * 1
    decision = None
    i = 0
    while True:
        for responses, obj in utils.process_data_async(unprocessed_data, model, sample_num, base_url, api_key,
                                                       generation_params):
            try:
                decision = parse_label_string(responses[0])

                # Try to decode and raise if any issues
                decision_dict = ast.literal_eval(decision)
                for op_type, items in decision_dict.items():
                    if op_type == "keep":
                        for old_key in items:
                            if old_key not in current_keys:
                                raise ValueError(f"{old_key} not in {current_keys}")
                    elif op_type == "merge":
                        for new_key, keys_to_merge in items:
                            for old_key in keys_to_merge:
                                if old_key not in current_keys:
                                    raise ValueError(f"{old_key} not in {current_keys}")
                    elif op_type == "split":
                        for old_key, sub_items in items:
                            if old_key not in leaf_keys:
                                raise ValueError(f"{old_key} not in {current_keys}")
                    elif op_type == "reparent":
                        for parent_key, child_keys in items:
                            for old_key in child_keys:
                                if old_key not in current_keys:
                                    raise ValueError(f"{old_key} not in {current_keys}")

                print("decision", decision)
                obj["raw_output"] = responses[0]
                obj["decision"] = decision
                file.write(json.dumps(obj, ensure_ascii=False) + '\n')
                file.flush()
                return decision
            except Exception as e:
                print(e)
                if i + 1 >= max_retries:
                    obj["raw_output"] = responses[0]
                    obj["decision"] = "Exceeded max retry limit, abort modification"
                    print("Exceeded max retry limit, abort modification")
                    file.write(json.dumps(obj, ensure_ascii=False) + '\n')
                    file.flush()
                    return obj["decision"]
        i += 1
        print("Retry", i)


if __name__ == "__main__":
    # Command-line argument parsing
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', type=str, default="roleplay", help='domain name')
    args = parser.parse_args()

    # Model configuration
    generation_params = {}  # {"temperature": 0.7, "top_p": 0.95}
    sample_num = 1
    model = "gpt-4.1"
    base_url = 'http://localhost:8006/'
    api_key = "any"

    # Path configuration
    input_path = "outputs/"
    output_path = "outputs_node_refinement_pruning/"
    os.makedirs(output_path, exist_ok=True)

    # ===============================================================================================
    # Data
    domain = args.domain
    output_save_path = f"{domain}_cata_tree.jsonl"
    base_prompt = utils.read_prompt("prompts/node_refinement_pruning.md")
    if domain not in ["roleplay", "coding", "knowledge", "mathematics", "reasoning", "writing"]:
        print("This domain does not exist")
        exit(0)

    # Read the last line with the key "tree_after_adding_node" from outputs/{domain}_cata_tree.jsonl
    with open(f"{input_path}/{domain}_cata_tree.jsonl", 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in reversed(lines):  # Traverse in reverse
            line = json.loads(line)
            if "tree_after_adding_node" in line.keys():
                tree = line["tree_after_adding_node"]
                break

    # ===============================================================================================
    # Parameter processing
    output_save_path = os.path.join(output_path, output_save_path)
    existing_items = []
    if os.path.exists(output_save_path):
        existing_items = utils.read_jsonl_file(output_save_path)

    # Iterative processing
    with open(output_save_path, 'a', encoding='utf-8') as f:
        # Add nodes to create a new tree
        pruning_node_llm_decision_partial = partial(pruning_node_llm_decision, max_retries=5, base_url=base_url,
                                                    api_key=api_key,
                                                    model=model, sample_num=sample_num,
                                                    generation_params=generation_params, file=f,
                                                    base_prompt=base_prompt, existing_items=existing_items)
        processor = TreeProcessor(tree)
        new_tree = processor.traverse_tree(pruning_node_llm_decision_partial)

        # Save log
        obj = {
            "finished": True,
            "new_tree": new_tree
        }
        f.write(json.dumps(obj, ensure_ascii=False) + '\n')
        f.flush()
