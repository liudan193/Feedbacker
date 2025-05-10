## Task
Your task is to assess the quality of a given query based on the checklists outlined below. For each checklist, provide a clear explanation of your reasoning before assigning "Yes" or "No". If your answer is "Borderline", please answer "No" for this checklist. 

## Checklists
Determine whether the provided question meets the following criteria. Return a Python array listing the numbers of all satisfied criteria:

1. **Clarity**: Is the question clear and well-defined?
2. **Completeness**: Does the question provide enough information for the LLM to answer the question?
3. **Complexity**: Does it involve multiple components, layers, or nuance?
4. **Real-World Application**: Is the question something that would be encountered in real-world development?
5. **Problem-Solving**: Does it require active problem-solving beyond simple and superficial script or fact recall?
6. **Domain-Specific Expertise**: Does the question require in-depth knowledge of at least one specific area of programming?
7. **Specified Requirements**: Does it specify particular requirements, such as execution time, space constraints, specific programming language, tools, packages, etc.?

For example, if the question meets Clarity, Completeness, and Real-World Application, return `[1, 2, 4]`.

## Final Output

For each question provided, return a Python dictionary in the following format:
```python
Final Labels: {{"question_quality": [1, 3, 4]}}
```

## The Query You Should Process
<|begin_of_query|>
{query}
<|end_of_query|>