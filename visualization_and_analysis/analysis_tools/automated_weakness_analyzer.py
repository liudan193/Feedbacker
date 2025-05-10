import argparse
import os
import time
from analysis_tools.base import BaseAnalyzer, load_json
import datetime
import json
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
import openai


class AutomatedWeaknessAnalyzer(BaseAnalyzer):
    def __init__(self, folder_path, threshold=5, output_file="report.html", model_name="gpt-4o", max_concurrency=32):
        """
        :param folder_path: 包含多个 JSON 文件的文件夹路径
        :param threshold: 判断 ranking 差异的阈值
        :param output_file: HTML输出文件的路径
        :param model_name: OpenAI 模型名称
        :param max_concurrency: 最大并发数
        """
        self.folder_path = folder_path
        self.threshold = threshold
        self.output_file = output_file
        self.model_name = model_name
        self.max_concurrency = max_concurrency
        self.html_content = []
        self.llm_reports = {}
        self.total_models = 0  # 新增：记录总模型数量

        # 验证OpenAI环境变量设置
        if "OPENAI_API_KEY" not in os.environ or "OPENAI_API_BASE" not in os.environ:
            print("Warning: OPENAI_API_KEY or OPENAI_API_BASE environment variables not set.")

        # 初始化线程安全的队列和锁
        self.report_queue = queue.Queue()
        self.html_lock = threading.Lock()

    def run(self):
        # 初始化HTML内容
        self._init_html()

        # 获取要处理的JSON文件列表
        json_files = [f for f in os.listdir(self.folder_path) if f.endswith('.json')]
        self.total_models = len(json_files)  # 新增：设置总模型数量
        print(f"Found {self.total_models} JSON files to process")

        # 使用线程池处理多个模型，限制最大并发数
        with ThreadPoolExecutor(max_workers=min(self.max_concurrency, self.total_models)) as executor:
            # 提交所有任务
            futures = {executor.submit(self.process_model, file_name): file_name for file_name in json_files}

            # 处理完成的任务
            for future in as_completed(futures):
                file_name = futures[future]
                try:
                    # 获取任务结果（如果有异常会在这里抛出）
                    future.result()
                except Exception as e:
                    print(f"Error processing {file_name}: {str(e)}")

        # 处理队列中的所有报告，按照文件名排序
        reports = []
        while not self.report_queue.empty():
            reports.append(self.report_queue.get())

        # 按模型名称排序报告
        reports.sort(key=lambda x: x[0])

        # 将排序后的报告添加到HTML
        for model_name, report_html in reports:
            with self.html_lock:
                self.html_content.append(report_html)

        # 完成HTML并写入文件
        self._finalize_html()

    def process_model(self, file_name):
        """处理单个模型文件（在单独的线程中运行）"""
        model_name = file_name[:-5]  # 去掉.json后缀
        full_path = os.path.join(self.folder_path, file_name)

        print(f"Processing model: {model_name}")

        # 准备模型报告的HTML内容
        model_html = []
        model_html.append(f"<h2>Model: {model_name}</h2>")

        # 加载并分析数据
        json_data = load_json(full_path)
        anomalies = self.analyze_tree(json_data)

        # 如果有异常，发送给LLM进行分析
        if anomalies and (anomalies.get("better_nodes") or anomalies.get("worse_nodes")):
            try:
                llm_report = self.get_llm_analysis(model_name, anomalies)

                # 将LLM报告添加到模型HTML中
                model_html.append("<div class='llm-report'>")
                model_html.append("<h3>LLM Analysis Report</h3>")
                model_html.append(f"<div class='report-content'>{llm_report}</div>")
                model_html.append("</div>")

                # 存储报告以供可能的进一步使用
                self.llm_reports[model_name] = llm_report
            except Exception as e:
                model_html.append(f"<p class='error'>Error generating LLM analysis: {str(e)}</p>")
        else:
            model_html.append("<p>No significant anomalies found for this model.</p>")

        # 将此模型的报告放入队列
        self.report_queue.put((model_name, "\n".join(model_html)))

        print(f"Completed processing for model: {model_name}")

    def analyze_tree(self, tree):
        """分析树结构并返回异常点"""
        root_ranking = tree.get('ranking')
        if root_ranking is None:
            return {"error": "No 'ranking' found in root node."}

        anomalies = {
            "model_root_ranking": root_ranking,
            "total_models": self.total_models,  # 新增：添加总模型数量
            "ranking_position": None,  # 将在_create_llm_prompt中计算
            "better_nodes": [],  # 排名更好的节点
            "worse_nodes": []  # 排名更差的节点
        }

        def traverse(node, path="root"):
            if 'ranking' in node:
                diff = node['ranking'] - root_ranking
                # 排名是值越小越好，所以小于root的是更好的节点
                if diff < -self.threshold:
                    anomalies["better_nodes"].append({
                        "path": path,
                        "ranking": node['ranking'],
                        "difference": diff
                    })
                elif diff > self.threshold:
                    anomalies["worse_nodes"].append({
                        "path": path,
                        "ranking": node['ranking'],
                        "difference": diff
                    })

            for key, child in node.items():
                if isinstance(child, dict):
                    traverse(child, f"{path}.{key}")

        traverse(tree)

        # 按照ranking值排序
        anomalies["better_nodes"].sort(key=lambda x: x["ranking"])
        anomalies["worse_nodes"].sort(key=lambda x: x["ranking"])

        return anomalies

    def get_llm_analysis(self, model_name, anomalies):
        """向OpenAI API发送异常数据并获取分析报告"""
        # 构建提示词
        prompt = self._create_llm_prompt(model_name, anomalies)

        # 重试机制
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                # 调用OpenAI API
                response = openai.ChatCompletion.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "You are a professional model performance analyst, skilled at "
                                                      "identifying a model's strengths and weaknesses and providing "
                                                      "expert analysis."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=4096
                )

                # 提取响应内容
                return_content = response.choices[0].message.content
                if "</think>" in return_content:
                    return_content = return_content.split("</think>")[1]
                return return_content

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"API call failed for {model_name}, retrying in {retry_delay}s... Error: {str(e)}")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    raise Exception(f"Failed to get LLM analysis after {max_retries} attempts: {str(e)}")

    def _create_llm_prompt(self, model_name, anomalies):
        """创建发送给LLM的提示词"""
        better_nodes = anomalies.get("better_nodes", [])
        worse_nodes = anomalies.get("worse_nodes", [])
        root_ranking = anomalies.get("model_root_ranking", "N/A")
        total_models = self.total_models

        # 计算排名位置（假设ranking值越小越好）
        ranking_position = None
        if isinstance(root_ranking, (int, float)) and total_models > 0:
            # 这里假设ranking就是模型的排名，如果是其他方式计算位置需要调整
            ranking_position = f"{root_ranking} out of {total_models}"

        prompt = f"""
Analyze the performance anomalies of model "{model_name}"

Background information:
- Overall ranking is: {root_ranking}
- Total models in comparison: {total_models}
- Ranking position: {ranking_position}
- A smaller ranking value indicates better performance
- The threshold is set to {self.threshold}; any difference beyond this is considered a significant anomaly

Nodes with better performance ({len(better_nodes)}):
"""

        # 添加表现较好的节点信息
        if better_nodes:
            for i, node in enumerate(better_nodes[:10], 1):  # 限制为前10个
                prompt += f"{i}. Path: {node['path']}, Ranking: {node['ranking']}, Difference: {node['difference']}\n"
            if len(better_nodes) > 10:
                prompt += f"...and {len(better_nodes) - 10} more nodes\n"
        else:
            prompt += "No significantly better-performing nodes\n"

        prompt += f"\nWorse-performing nodes ({len(worse_nodes)}):\n"

        # 添加表现较差的节点信息
        if worse_nodes:
            for i, node in enumerate(worse_nodes[:10], 1):  # 限制为前10个
                prompt += f"{i}. Path: {node['path']}, Ranking: {node['ranking']}, Difference: {node['difference']}\n"
            if len(worse_nodes) > 10:
                prompt += f"...and {len(worse_nodes) - 10} more nodes\n"
        else:
            prompt += "No significantly worse-performing nodes\n"

        prompt += """
Please provide a concise analysis report based on the above data, including:
1. Overall assessment of the model's performance
2. Areas of significant strength (if any)
3. Key weaknesses that need improvement (if any)
4. Hypotheses on the possible causes of these anomalies
5. Recommendations for improvement

Please format the output in HTML, including appropriate headings, lists, and emphasis to facilitate web display.
"""
        return prompt

    def _init_html(self):
        """初始化HTML文档"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.html_content = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "    <meta charset='UTF-8'>",
            "    <title>Model Weakness Analysis Report</title>",
            "    <style>",
            "        body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }",
            "        h1 { color: #333366; }",
            "        h2 { color: #336699; margin-top: 30px; border-bottom: 1px solid #ccc; padding-bottom: 5px; }",
            "        h3 { color: #3377AA; }",
            "        h4 { color: #3388BB; margin-bottom: 10px; }",
            "        table { border-collapse: collapse; margin: 15px 0; width: 100%; }",
            "        th { background-color: #f2f2f2; text-align: left; padding: 8px; }",
            "        td { padding: 8px; }",
            "        tr:nth-child(even) { background-color: #f9f9f9; }",
            "        .llm-report { background-color: #f8f8ff; border: 1px solid #e0e0e8; ",
            "                     padding: 15px; border-radius: 8px; margin: 20px 0; }",
            "        .report-content { line-height: 1.5; }",
            "        .error { color: #cc0000; background-color: #ffeeee; padding: 10px; border-radius: 5px; }",
            "        .footer { margin-top: 30px; font-size: 0.8em; color: #666; border-top: 1px solid #ccc; padding-top: 10px; }",
            "        ul { margin-top: 5px; }",
            "        .model-summary { background-color: #f0f8ff; padding: 10px; border-radius: 5px; margin: 10px 0; }",
            "    </style>",
            "</head>",
            "<body>",
            f"    <h1>Model Weakness Analysis Report</h1>",
            f"    <p>Generated on: {timestamp}</p>",
            f"    <p>Threshold for significant anomalies: {self.threshold}</p>",
            f"    <p>LLM model used for analysing: {self.model_name}</p>",
            f"    <p>Total models analyzed: {self.total_models}</p>",  # 新增：显示总模型数量
            "    <hr>",
        ]

    def _finalize_html(self):
        """完成HTML并写入文件"""
        self.html_content.extend([
            "    <div class='footer'>",
            "        <p>Automated Weakness Analysis Report - Generated by LLM Analysis</p>",
            "    </div>",
            "</body>",
            "</html>"
        ])

        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.html_content))

        print(f"Report generated successfully: {self.output_file}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate HTML weakness analysis report with LLM insights')
    parser.add_argument('--folder', default="../processed_data/", help='Folder path containing JSON files')
    parser.add_argument('--threshold', type=float, default=5, help='Threshold for ranking difference')
    parser.add_argument('--output', default="../analysis_results/automated_weakness_analysis.html",
                        help='Output HTML file path')
    parser.add_argument('--model', default="gpt-4", help='OpenAI model name to use for analysis')
    parser.add_argument('--max_concurrency', type=int, default=5, help='Maximum number of concurrent tasks')

    args = parser.parse_args()

    # 检查环境变量
    if "OPENAI_API_KEY" not in os.environ:
        print("Error: OPENAI_API_KEY environment variable not set")
        exit(1)
    if "OPENAI_API_BASE" not in os.environ:
        print("Error: OPENAI_API_BASE environment variable not set")
        exit(1)

    # 配置OpenAI客户端
    openai.api_key = os.environ["OPENAI_API_KEY"]
    openai.api_base = os.environ["OPENAI_API_BASE"]

    print(f"Starting analysis with model: {args.model}")
    analyzer = AutomatedWeaknessAnalyzer(
        folder_path=args.folder,
        threshold=args.threshold,
        output_file=args.output,
        model_name=args.model,
        max_concurrency=args.max_concurrency  # 新增：设置最大并发数
    )
    analyzer.run()