# Building Your Customized Taxonomy Tree

This guide explains how to use our **TaxBuilder** to create a customized taxonomy tree.

## 1. (Optional) Initialize Tree Structure

If you're building a completely new taxonomy tree from scratch, you should manually create a basic tree following the structure described in the language used in `init_tree/`. Once created, you need to do two things:

1. Save your tree in the same format as other trees in the `init_tree/` folder. 
2. Organize your tree in JSON format and update the `init_cate_tree` variable in `node_insertion.py`.

## 2. Insert New Nodes

When you want to insert some new nodes into the tree, you need to make some changes to `node_insertion.py`.

1. Configure the LLM service to determine node relationships. We use an OpenAI-compatible format to configure the LLM service, and you need to replace the following three variables with your own. We highly recommend using a reasoning model for this task, such as DeepSeek-R1 or QwQ-32B.

```python
model = "QwQ-32B"
base_url = 'http://localhost:8005/'
api_key = "any"
```

2. Modify the `new_types` variable, which is a list that contains all the new nodes you want to add.

Once you're done, you can run:

```bash
python node_insertion.py --domain your_domain
```

Since this is an iterative process, it will take a long time if there are a large number of new nodes. Once it finishes, you can check the last line of the JSONL file in the `outputs/` directory. The `tree_after_adding_node` key will contain the updated tree.

You can stop and restart it at any time, as it has **checkpoint resume** functionality!

## 3. Refine and Prune Nodes

When you have inserted all the nodes into the tree, it will usually contain many incorrect and redundant nodes. To address this, you can use the `node_refinement_pruning.py` script to refine and prune the nodes. This script recursively traverses the tree to do this.

You should also configure the LLM service in the code.

```python
model = "QwQ-32B"
base_url = 'http://localhost:8005/'
api_key = "any"
```

Then, you can run:

```bash
python node_refinement_pruning.py --domain your_domain
```

Once it completes, you can check the last line of the JSONL file in the `outputs_node_refinement_pruning/` directory. The `new_tree` key will contain the refined tree. It also has **checkpoint resume** functionality.

## 4. Prune Layers

In addition to redundant nodes, the tree may also contain redundant layers, such as overly deep layers or cases where a parent node only has one child. We can prune these layers. This step does not require LLM, and can be done using a rule-based method.

You can directly run:

```bash
python layer_pruning.py --domain your_domain
```

Once it completes, the final tree is stored in a JSONL file under the `outputs_layer_pruning/` directory.