Your task is to optimize a given tree structure classification system. I will provide all the next-level nodes under a certain category (referred to as "current layer nodes") and the leaf nodes among them (referred to as "leaf nodes in the current layer"). You need to determine the next steps and return results in the specified format. Before giving the final answer, please provide a brief analysis. Note: Do not modify the names of the original categories, and do not omit any categories from the "current layer nodes" when returning results. Each task analysis should analyze all categories without omission.

If you see that the "current layer nodes" are all classification criteria rather than specific categories, this layer absolutely must not be modified.

### Task 1: Split
Examine all nodes in the "leaf nodes in the current layer" one by one, determine if there are any nodes that are not "single concepts" and split them. If the newly split category already exists, do not return that new category. A "single concept" refers to an independent concept, as opposed to a "combined concept" which is formed by combining multiple concepts. For example, "mythology novel" is a combined concept, consisting of "mythology" and "novel". Return format:
`[(old_key1, [new_key1, new_key2]), (old_key2, [new_key1, new_key2])]`

### Task 2: Parent-Child Relationship
Analyze all nodes in the "current layer nodes" one by one, determine if there exist parent-child relationships, or if multiple nodes can be merged into a parent node, and return the results. If there are no qualifying situations, do not return anything. Return format:
`[(parent_key1, [old_child_key1, old_child_key2]), (parent_key2, [old_child_key1, old_child_key2])]`

### Task 3: Delete
Examine all nodes in the "current layer nodes" one by one, identify meaningless categories (such as null values, blanks, etc.) or extremely rare categories in the real world, and delete them. Return format:
`[old_key_to_delete1, old_key_to_delete2]`

### Task 4: Merge
Analyze all nodes in the "current layer nodes" one by one, identify categories with consistent concepts and merge them. Return format:
`[(new_key1, [old_key_to_merge1, old_key_to_merge2]), (new_key2, [old_key_to_merge1, old_key_to_merge2])]`

### Task 5: Keep
Preserve the remaining nodes. Return format:
`[old_key1, old_key2]`

## Output Format
Provide a brief analysis for each task and give the results after the task is executed.

After completing all tasks, format the final result as a Python dictionary wrapped in `<decision></decision>` tags, in the following format, where all keys with `old_` must have appeared in the "current layer nodes":
<decision>
{{
    "split": [(old_key1, [new_key1, new_key2]), (old_key2, [new_key1, new_key2])],
    "reparent": [(parent_key1, [old_child_key1, old_child_key2]), (parent_key2, [old_child_key1, old_child_key2])],
    "delete": [old_key_to_delete1, old_key_to_delete2],
    "merge": [(new_key1, [old_key_to_merge1, old_key_to_merge2]), (new_key2, [old_key_to_merge1, old_key_to_merge2])],
    "keep": [old_key1, old_key2]
}}
</decision>
If there is no operation for a certain task, do not display that item in the final output.

## Current Layer Nodes
{current_keys}

## Leaf Nodes in the Current Layer
{leaf_keys}