You are an impartial judge responsible for evaluating the quality of responses provided by different LLMs to a given [question]. Your task is to design a comprehensive evaluation framework that includes clearly defined metrics and their respective weights. You shuold answer step by step. You should answer in English. Please carefully follow these steps:

1. **Analyze Responses**: You must first compare several provided [answers] and identify their differences. The objective of this comparison is to pinpoint distinguishing factors that significantly influence the quality of the responses.
2. **Develop Metrics**: Establish a hierarchical set of evaluation metrics. There should be 3 to 9 primary metrics. Each primary metric should have several detailed sub-metrics to provide specific, measurable criteria for evaluating the responses.
3. **Assign Weights**: Allocate appropriate weights to each metric based on its relative importance in distinguishing the quality of the responses. The weights should be integers, and the sum of all weights should equal 100.
4. **Output Format**: Present the final evaluation framework in a structured list format. You do not need to include the primary metrics; only the secondary metrics are required, in the following format:
<Evaluation_Framework>
1. Description of Secondary Metric 1 | Weight 1
2. Description of Secondary Metric 2 | Weight 2
3. Description of Secondary Metric 3 | Weight 3
...
<\Evaluation_Framework>

[User Question]
{question}

[The Start of Assistant 1’s Answer]
{answer_1}
[The End of Assistant 1’s Answer]

[The Start of Assistant 2’s Answer]
{answer_2}
[The End of Assistant 2’s Answer]

[The Start of Assistant 3’s Answer]
{answer_3}
[The End of Assistant 3’s Answer]