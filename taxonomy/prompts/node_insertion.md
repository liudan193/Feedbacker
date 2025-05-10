Your task is to add a new node to a tree-structured classification system. I will give you some [Current Level Nodes] and a [New Node]. You need to determine the next action and respond strictly in the specified format. Before giving the final answer, you must perform brief analysis.

# Task 1
Analyze whether the [New Node] shares identical meaning with any [Current Level Nodes] (including exact matches, case variations, abbreviations, or conceptually equivalent expressions). If identical, return <decision>EXIST</decision> and skip subsequent tasks.
Analyze whether the [New Node] represents a specific category or a classification criterion. If it's a classification criterion, return <decision>EXIST</decision> and skip subsequent tasks.

# Task 2
Analyze whether the [New Node] doesn't belong to any subordinate node of [Current Level Nodes] but should be at the same level. If yes, return <decision>ADD</decision> and skip subsequent tasks.

# Task 3
Identify which [Current Level Node] the [New Node] should belong to as a subordinate node. Return the parent node's name wrapped in <decision></decision>.

## Example
Current Level Nodes: ["Fruits", "Vegetables", "Electronics"]
New Node: Phone
Output: <decision>Electronics</decision>

## New Node
{new_node}

## Current Level Nodes
{current_keys}

## Reference Classification System (for reference only)
{init_tree}