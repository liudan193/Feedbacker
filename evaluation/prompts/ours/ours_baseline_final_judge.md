Please act as an impartial judge and evaluate the quality of the response provided by an AI assistant to the user question displayed below. Your evaluation should consider the evaluation system displayed below. Begin your evaluation by providing an explanation for each metric, assessing the response objectively. Score each metric on a scale of 1 to 3. Use the baseline answer as a baseline; a higher score indicates a better response compared to the baseline answer, while a lower score indicates a worse response. The weights of the metrics must sum to 100, and the final weighted score should be calculated on a scale of 100 to 300, reflecting the weighted sum of the individual scores. After evaluation, you must summarize the results within <The Start of Evaluation Result> and <The End of Evaluation Result>. Below is an example output:
<The Start of Evaluation Result>
Metric 1 | score: [2]
Metric 2 | score: [3]
Metric 3 | score: [1]
...

Final Weighted Score: [[200]]
<The End of Evaluation Result>


[Question]
{question}

[The Start of Evaluation System]
{eval_system}
[The End of Evaluation System]

[The Start of Baseline Answer]
{answer_baseline}
[The End of Baseline Answer]

[The Start of Evaluation for Baseline Answer]
{critic_baseline}
[The End of Evaluation for Baseline Answer]

[The Start of Assistant’s Answer]
{answer}
[The End of Assistant’s Answer]
