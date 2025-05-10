# Evaluating Models

In this repository, we explain how to use our new evaluation method for model assessment.

## 1. Generation

You first need to provide the service of the model to be tested, which should be OpenAI-compatible. Afterward, use the following command to generate the model's responses.

```bash
python 1.generation.py --model "gpt-4o" --base_url "http://localhost:8005" --api_key "any_key" --max_workers 32
```

## 2. Evaluation

You need to modify the model configuration variables in all the files below to match your own LLM service.

## (Optional) 2.1 Prepare Evaluation Criteria and Baseline Evaluation Results

If you want to generate your own criteria or replace the baseline, please run the following two commands.

```bash
# 1. Generate criteria. Once the criteria are generated, they can be fixed, and there is no need to regenerate them for subsequent evaluations.
python 2.1.generate_criteria.py

# 2. Evaluate the baseline. This step only needs to be run once as well.
python 2.2.evaluate_baseline.py
```

## 2.3 Evaluation Execution

Run the following command to execute the evaluation. 

```bash
# 3. Execute the evaluation. The parameters need to be consistent with those used in generation.
python 2.3.final_evaluation.py --model "gpt-4o"
```