## Task
Your task is to assess the query of a given question based on the rules outlined below. For each rule, provide a clear explanation of your reasoning before assigning a label.

## Rule
Determine whether the provided query meets the following criteria. Return a Python array listing the numbers of all satisfied criteria:

1. **Clarity**: Is the question clear and well-defined?
2. **Completeness**: Does the question provide enough information for the LLM to answer the question?
3. **Complexity**: Does it involve multiple steps, analysis, or reasoning instead of simple concept memorization?
4. **Real-World Application**: Is the question something that would be encountered in real-world?
5. **Problem-Solving**: Does it require devising a solution or strategy?  
6. **Deep Thinking**: Does it require deep reasoning and consideration of multiple factors?  
7. **Novelty:** Does the question present a unique or unusual scenario that the LLM is unlikely to have encountered before?

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