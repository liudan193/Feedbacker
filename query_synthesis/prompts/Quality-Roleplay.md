## Task
Your task is to assess the quality of a given query based on the checklists outlined below. For each checklist, provide a clear explanation of your reasoning before assigning "Yes" or "No". If your answer is "Borderline", please answer "Yes" for this checklist. 

## Checklists
Determine whether the provided question meets the following criteria. Return a Python array listing the numbers of all satisfied criteria:

1. **Clarity**: Is the question clear and well-defined?
2. **Completeness**: Does the question provide enough information for the LLM to answer the question?
3. **Complexity**: Does it involve in-depth understanding of any role-playing content, such as the psychology, characterization, and world-building of characters?
4. **Real-World Application**: Is this role-playing task something that would be proposed in the real world?
5. **Interactivity**: Does the question encourage meaningful interactions between characters, rather than single character?
6. **Engagement**: Does the task motivate active participation and emotional involvement from the audience or participants?
7. **Creativity:** Does it have creativity and novelty, or does solving it require creativity?

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