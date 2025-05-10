I will provide three real user questions and a reference question’s type tags. Your task is to create a new question in the {domain} domain with the same tags as reference question. To ensure the question feels authentic, you should utilize real-world details drawn from the three real user questions. 

### You MUST follow these steps to generate the new question:

#### Task1: Real-world Details Selection:

Select a few real-world details (such as the real people, objects, scenes, settings, and any other details mentioned) from three real user questions that fit the given tags. If there are no suitable details, return [[I cannot generate a question based on the provided real user questions.]] and stop.

#### Task2: New Question Generation:

1. Although you should use details from real user questions, you must not mention the real user question in the new question.
2. The new question should be complex and challenging, requiring deep understanding and analysis of the subject. The length of the question should be at least as long as the reference question but should not be overly simplistic or repetitive. The question should be singular, not a multi-task question.
3. The new question must be **completely self-contained**, so that others can answer it without any additional information. 
4. Analyze how to create the new question with chosen real-world details and provided tags. While multiple tags are available, the newly generated question only needs to align with some of them, not all. Even if the original question already fits, generate a different version.

### Output Format:

[Anylysis]: You should first complete the anylysis of task1 and task2 here. 
[Question]: Summarize the newly generated question in the following format: <new_query>Insert the final new question here.<\new_query>

---

<|begin_of_reference_query|>
{reference_query}
<|end_of_reference_query|>

<|begin_of_reference_query_type_tags|>
{type_tags}
<|end_of_reference_query_type_tags|>

<|begin_of_real_user_query_1|>
{query1}
<|end_of_real_user_query_1|>

<|begin_of_real_user_query_2|>
{query2}
<|end_of_real_user_query_2|>

<|begin_of_real_user_query_3|>
{query3}
<|end_of_real_user_query_3|>