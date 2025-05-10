import argparse
import os
from analysis_tools.base import BaseAnalyzer, load_json
import datetime


class AutomatedWeaknessReporter(BaseAnalyzer):
    def __init__(self, folder_path, threshold=5, output_file="report.html"):
        """
        :param folder_path: 包含多个 JSON 文件的文件夹路径
        :param threshold: 判断 ranking 差异的阈值
        :param output_file: HTML输出文件的路径
        """
        self.folder_path = folder_path
        self.threshold = threshold
        self.output_file = output_file
        self.html_content = []

    def run(self):
        # 初始化HTML内容
        self._init_html()

        for file_name in os.listdir(self.folder_path):
            if file_name.endswith('.json'):
                full_path = os.path.join(self.folder_path, file_name)
                self.html_content.append(f"<h2>Processing: {file_name[:-5]}</h2>")
                json_data = load_json(full_path)
                self.process_tree(json_data)

        # 完成HTML并写入文件
        self._finalize_html()

    def process_tree(self, tree):
        root_ranking = tree.get('ranking')
        if root_ranking is None:
            self.html_content.append("<p>No 'ranking' found in root node.</p>")
            return

        higher_ranking_nodes = []
        lower_ranking_nodes = []

        def traverse(node, path="root"):
            if 'ranking' in node:
                diff = node['ranking'] - root_ranking
                # 排名是值越小越好，所以小于root的是更好的节点
                if diff < -self.threshold:
                    higher_ranking_nodes.append((path, node['ranking'], diff))
                elif diff > self.threshold:
                    lower_ranking_nodes.append((path, node['ranking'], diff))

            for key, child in node.items():
                if isinstance(child, dict):
                    traverse(child, f"{path}.{key}")

        traverse(tree)

        # 更好排名节点表格（值更小）
        self.html_content.append(
            "<h3>Nodes with significantly <span style='color: green;'>better</span> ranking than root:</h3>")
        if higher_ranking_nodes:
            # 按照ranking值排序（从小到大）
            higher_ranking_nodes.sort(key=lambda x: x[1])
            self._add_table(higher_ranking_nodes, is_higher=True)
        else:
            self.html_content.append("<p>No nodes found with significantly better ranking.</p>")

        # 更差排名节点表格（值更大）
        self.html_content.append(
            "<h3>Nodes with significantly <span style='color: red;'>worse</span> ranking than root:</h3>")
        if lower_ranking_nodes:
            # 按照ranking值排序（从小到大）
            lower_ranking_nodes.sort(key=lambda x: x[1])
            self._add_table(lower_ranking_nodes, is_higher=False)
        else:
            self.html_content.append("<p>No nodes found with significantly lower ranking.</p>")

    def _add_table(self, nodes, is_higher=True):
        """添加HTML表格"""
        self.html_content.append("<table border='1' cellpadding='5' cellspacing='0'>")
        self.html_content.append("<tr><th>Path</th><th>Ranking</th><th>Difference</th></tr>")

        for path, ranking, diff in nodes:
            # 对于更好的节点(is_higher=True)，差值是负数；对于更差的节点，差值是正数
            diff_str = f"{diff}"  # 保留原始差值格式
            diff_color = "green" if is_higher else "red"

            self.html_content.append(
                f"<tr><td>{path}</td><td>{ranking}</td>"
                f"<td style='color: {diff_color};'>{diff_str}</td></tr>"
            )

        self.html_content.append("</table>")

    def _init_html(self):
        """初始化HTML文档"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.html_content = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "    <meta charset='UTF-8'>",
            "    <title>Weakness Analysis Report</title>",
            "    <style>",
            "        body { font-family: Arial, sans-serif; margin: 20px; }",
            "        h1 { color: #333366; }",
            "        h2 { color: #336699; margin-top: 30px; border-bottom: 1px solid #ccc; }",
            "        table { border-collapse: collapse; margin: 15px 0; width: 100%; }",
            "        th { background-color: #f2f2f2; text-align: left; }",
            "        tr:nth-child(even) { background-color: #f9f9f9; }",
            "        .footer { margin-top: 30px; font-size: 0.8em; color: #666; border-top: 1px solid #ccc; padding-top: 10px; }",
            "    </style>",
            "</head>",
            "<body>",
            f"    <h1>Weakness Analysis Report</h1>",
            f"    <p>Generated on: {timestamp}</p>",
            f"    <p>Threshold: {self.threshold}</p>",
        ]

    def _finalize_html(self):
        """完成HTML并写入文件"""
        self.html_content.extend([
            "    <div class='footer'>",
            "        <p>Automated Weakness Analysis Report</p>",
            "    </div>",
            "</body>",
            "</html>"
        ])

        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.html_content))

        print(f"Report generated successfully: {self.output_file}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate HTML weakness report')
    parser.add_argument('--folder', default="../processed_data/", help='Folder path containing JSON files')
    parser.add_argument('--threshold', type=float, default=5, help='Threshold for ranking difference')
    parser.add_argument('--output', default="../analysis_results/automated_weakness_reporter.html", help='Output HTML file path')

    args = parser.parse_args()

    reporter = AutomatedWeaknessReporter(
        folder_path=args.folder,
        threshold=args.threshold,
        output_file=args.output
    )
    reporter.run()