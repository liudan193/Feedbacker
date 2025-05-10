import argparse
import os
import numpy as np
from analysis_tools.base import BaseAnalyzer, load_json
import datetime


class FailureModeExplorer(BaseAnalyzer):
    def __init__(self, folder_path, threshold=5, percentile=20, output_file="report.html"):
        """
        :param folder_path: 包含多个 JSON 文件的文件夹路径
        :param threshold: 子节点数量的阈值，只分析子节点数 ≥ 阈值的节点
        :param percentile: 用于判断系统性与偶然性的百分位值
        :param output_file: HTML输出文件的路径
        """
        self.folder_path = folder_path
        self.threshold = threshold
        self.percentile = percentile
        self.output_file = output_file
        self.html_content = []
        self.all_std_values = []  # 存储所有被分析节点的标准差
        self.nodes_to_analyze = []  # 存储需要分析的节点信息
        self.model_list = []  # 存储所有模型名称

    def run(self):
        # 初始化HTML内容
        self._init_html()

        # 获取所有模型名称（从文件名）
        for file_name in os.listdir(self.folder_path):
            if file_name.endswith('.json'):
                model_name = file_name[:-5]
                self.model_list.append(model_name)

        # 第一遍扫描：收集所有需要分析的节点和计算标准差
        for file_name in os.listdir(self.folder_path):
            if file_name.endswith('.json'):
                full_path = os.path.join(self.folder_path, file_name)
                json_data = load_json(full_path)
                self.collect_nodes_and_std(json_data, file_name[:-5])

        # 计算标准差的阈值
        total_nodes = len(self.all_std_values)
        if total_nodes > 0:
            # 排序标准差值以确定阈值
            sorted_std = sorted(self.all_std_values)
            stable_threshold = sorted_std[int(total_nodes * self.percentile / 100)]
            unstable_threshold = sorted_std[int(total_nodes * (100 - self.percentile) / 100)]

            # 创建模型选择器
            self._add_model_selector()

            # 添加主信息区域
            self.html_content.append(f"""
            <div class="info-container">
                <div class="info-box">
                    <p>Total analyzed nodes: {total_nodes}</p>
                    <p>Systematic (stable) threshold (lower {self.percentile}%): <span class="stable">{stable_threshold:.4f}</span></p>
                    <p>Occasional (unstable) threshold (upper {self.percentile}%): <span class="unstable">{unstable_threshold:.4f}</span></p>
                </div>
            </div>
            """)

            # 创建双栏布局容器
            self.html_content.append("""
            <div class="container">
                <div class="column" id="systematic-column">
                    <h2 class="column-title stable">Systematic (Stable) Patterns</h2>
                    <div class="column-content" id="systematic-content"></div>
                </div>
                <div class="column" id="occasional-column">
                    <h2 class="column-title unstable">Occasional (Unstable) Patterns</h2>
                    <div class="column-content" id="occasional-content"></div>
                </div>
            </div>
            """)

            # 创建一个隐藏的数据容器
            self.html_content.append('<div id="data-container" style="display:none;">')

            # 处理每个节点，根据标准差归类
            systematic_nodes = {}
            occasional_nodes = {}

            for node_info in self.nodes_to_analyze:
                file_name, path, parent_ranking, children_rankings, std = node_info
                model_name = file_name

                # 只保留异常状态节点（系统性或偶然性）
                if std <= stable_threshold:  # 系统性（稳定）
                    if model_name not in systematic_nodes:
                        systematic_nodes[model_name] = []
                    systematic_nodes[model_name].append(node_info)
                elif std >= unstable_threshold:  # 偶然性（不稳定）
                    if model_name not in occasional_nodes:
                        occasional_nodes[model_name] = []
                    occasional_nodes[model_name].append(node_info)

            # 生成各个模型的系统性和偶然性节点HTML，放在隐藏的数据容器中
            for model_name in self.model_list:
                self.html_content.append(f'<div id="data-systematic-{model_name}">')

                # 处理系统性节点
                if model_name in systematic_nodes and systematic_nodes[model_name]:
                    for node_info in systematic_nodes[model_name]:
                        file_name, path, parent_ranking, children_rankings, std = node_info
                        node_html = self._generate_node_html(path, parent_ranking, children_rankings, std, "stable")
                        self.html_content.append(node_html)
                else:
                    self.html_content.append("<p class='no-data'>No systematic patterns found.</p>")

                self.html_content.append('</div>')

                self.html_content.append(f'<div id="data-occasional-{model_name}">')

                # 处理偶然性节点
                if model_name in occasional_nodes and occasional_nodes[model_name]:
                    for node_info in occasional_nodes[model_name]:
                        file_name, path, parent_ranking, children_rankings, std = node_info
                        node_html = self._generate_node_html(path, parent_ranking, children_rankings, std, "unstable")
                        self.html_content.append(node_html)
                else:
                    self.html_content.append("<p class='no-data'>No occasional patterns found.</p>")

                self.html_content.append('</div>')

            # 关闭数据容器
            self.html_content.append('</div>')

            # 添加JavaScript以处理模型选择
            self.html_content.append("""
            <script>
            function showModel(modelName) {
                // 更新系统性内容
                const systematicContent = document.getElementById('systematic-content');
                const systematicData = document.getElementById('data-systematic-' + modelName);
                systematicContent.innerHTML = systematicData.innerHTML;

                // 更新偶然性内容
                const occasionalContent = document.getElementById('occasional-content');
                const occasionalData = document.getElementById('data-occasional-' + modelName);
                occasionalContent.innerHTML = occasionalData.innerHTML;

                // 更新选择器标签
                const selector = document.getElementById('model-selector');
                selector.querySelector('.selector-label').textContent = 'Selected Model: ' + modelName;

                // 更新所有选项的活动状态
                const options = selector.querySelectorAll('.model-option');
                for (let i = 0; i < options.length; i++) {
                    if (options[i].getAttribute('data-model') === modelName) {
                        options[i].classList.add('active');
                    } else {
                        options[i].classList.remove('active');
                    }
                }
            }

            // 初始化显示第一个模型
            window.onload = function() {
                const firstModel = document.querySelector('.model-option');
                if (firstModel) {
                    showModel(firstModel.getAttribute('data-model'));
                }
            };
            </script>
            """)

        else:
            self.html_content.append("<p>No nodes found for analysis.</p>")

        # 完成HTML并写入文件
        self._finalize_html()

    def _add_model_selector(self):
        """添加模型选择器"""
        if not self.model_list:
            return

        selector_html = ['<div id="model-selector" class="model-selector">']
        selector_html.append('<div class="selector-label">Selected Model: </div>')
        selector_html.append('<div class="selector-options">')

        for model_name in self.model_list:
            selector_html.append(
                f'<div class="model-option" data-model="{model_name}" onclick="showModel(\'{model_name}\')">{model_name}</div>')

        selector_html.append('</div></div>')
        self.html_content.append(''.join(selector_html))

    def _generate_node_html(self, path, parent_ranking, children_rankings, std, type_class):
        """生成节点HTML"""
        html = [f'<div class="node-card {type_class}">']
        html.append(f'<h3 class="node-path">{path}</h3>')
        html.append(f'<div class="node-details">')
        html.append(f'<p>Parent ranking: {parent_ranking}</p>')
        html.append(f'<p>Children count: {len(children_rankings)}</p>')
        html.append(f'<p>Standard deviation: <span class="{type_class}">{std:.4f}</span></p>')
        html.append('</div>')

        # 添加子节点表格
        html.append('<div class="children-table-container">')
        html.append('<table class="children-table">')
        html.append('<tr><th>Child Key</th><th>Ranking</th><th>Difference</th></tr>')

        for key, ranking, diff in children_rankings:
            diff_class = "better" if diff < 0 else "worse" if diff > 0 else ""
            html.append(
                f'<tr><td>{key}</td><td>{ranking}</td>'
                f'<td class="{diff_class}">{diff:.4f}</td></tr>'
            )

        html.append('</table>')
        html.append('</div>')  # close table container
        html.append('</div>')  # close node card

        return ''.join(html)

    def collect_nodes_and_std(self, tree, file_name, path="root"):
        """收集所有需要分析的节点和计算标准差"""

        def count_children(node):
            """计算直接子节点数量"""
            return sum(1 for key, value in node.items() if isinstance(value, dict))

        def get_child_rankings(node):
            """获取所有子节点的ranking值列表"""
            rankings = []
            for key, child in node.items():
                if isinstance(child, dict) and 'ranking' in child:
                    rankings.append((key, child['ranking']))
            return rankings

        def traverse(node, current_path):
            # 检查节点是否有ranking值
            if 'ranking' not in node:
                return

            # 计算直接子节点数量
            child_count = count_children(node)

            # 只分析有足够子节点的节点
            if child_count >= self.threshold:
                # 获取子节点的ranking值
                children_rankings = get_child_rankings(node)

                # 计算子节点ranking与父节点ranking的差值
                parent_ranking = node['ranking']
                ranking_diffs = [(key, ranking, ranking - parent_ranking) for key, ranking in children_rankings]

                # 计算标准差
                if ranking_diffs:
                    diffs_only = [diff for _, _, diff in ranking_diffs]
                    std_dev = np.std(diffs_only)
                    self.all_std_values.append(std_dev)

                    # 存储节点信息供后续分析
                    self.nodes_to_analyze.append((
                        file_name,
                        current_path,
                        parent_ranking,
                        ranking_diffs,
                        std_dev
                    ))

            # 递归遍历子节点
            for key, child in node.items():
                if isinstance(child, dict):
                    traverse(child, f"{current_path}.{key}")

        traverse(tree, path)

    def _init_html(self):
        """初始化HTML文档"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.html_content = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "    <meta charset='UTF-8'>",
            "    <title>Failure Mode Explorer Report</title>",
            "    <style>",
            "        :root {",
            "            --stable-color: #2e7d32;",
            "            --unstable-color: #c62828;",
            "            --better-color: #4caf50;",
            "            --worse-color: #f44336;",
            "            --border-color: #e0e0e0;",
            "            --bg-light: #f5f5f5;",
            "            --bg-dark: #eeeeee;",
            "        }",
            "        body {",
            "            font-family: 'Segoe UI', Roboto, Arial, sans-serif;",
            "            margin: 0;",
            "            padding: 0;",
            "            background-color: #fafafa;",
            "            color: #333;",
            "        }",
            "        header {",
            "            background-color: #1976d2;",
            "            color: white;",
            "            padding: 1rem 2rem;",
            "            box-shadow: 0 2px 5px rgba(0,0,0,0.1);",
            "        }",
            "        h1 {",
            "            margin: 0;",
            "            font-weight: normal;",
            "        }",
            "        .info-container {",
            "            padding: 1rem 2rem;",
            "        }",
            "        .info-box {",
            "            background-color: white;",
            "            border-radius: 4px;",
            "            padding: 1rem;",
            "            box-shadow: 0 1px 3px rgba(0,0,0,0.1);",
            "        }",
            "        .model-selector {",
            "            display: flex;",
            "            align-items: center;",
            "            background-color: white;",
            "            margin: 1rem 2rem;",
            "            padding: 0.5rem 1rem;",
            "            border-radius: 4px;",
            "            box-shadow: 0 1px 3px rgba(0,0,0,0.1);",
            "        }",
            "        .selector-label {",
            "            font-weight: bold;",
            "            margin-right: 1rem;",
            "        }",
            "        .selector-options {",
            "            display: flex;",
            "            flex-wrap: wrap;",
            "            gap: 0.5rem;",
            "        }",
            "        .model-option {",
            "            padding: 0.5rem 1rem;",
            "            background-color: var(--bg-light);",
            "            border-radius: 4px;",
            "            cursor: pointer;",
            "            transition: all 0.2s;",
            "        }",
            "        .model-option:hover {",
            "            background-color: var(--bg-dark);",
            "        }",
            "        .model-option.active {",
            "            background-color: #1976d2;",
            "            color: white;",
            "        }",
            "        .container {",
            "            display: flex;",
            "            margin: 0 2rem 2rem;",
            "            gap: 2rem;",
            "        }",
            "        .column {",
            "            flex: 1;",
            "            background-color: white;",
            "            border-radius: 4px;",
            "            box-shadow: 0 1px 3px rgba(0,0,0,0.1);",
            "            overflow: hidden;",
            "        }",
            "        .column-title {",
            "            margin: 0;",
            "            padding: 1rem;",
            "            text-align: center;",
            "            border-bottom: 1px solid var(--border-color);",
            "        }",
            "        .column-content {",
            "            padding: 1rem;",
            "            max-height: 800px;",
            "            overflow-y: auto;",
            "        }",
            "        .node-card {",
            "            margin-bottom: 1.5rem;",
            "            border-radius: 4px;",
            "            border: 1px solid var(--border-color);",
            "            overflow: hidden;",
            "        }",
            "        .node-card.stable {",
            "            border-left: 4px solid var(--stable-color);",
            "        }",
            "        .node-card.unstable {",
            "            border-left: 4px solid var(--unstable-color);",
            "        }",
            "        .node-path {",
            "            margin: 0;",
            "            padding: 0.75rem;",
            "            background-color: var(--bg-light);",
            "            border-bottom: 1px solid var(--border-color);",
            "            font-size: 1rem;",
            "        }",
            "        .node-details {",
            "            padding: 0.75rem;",
            "            border-bottom: 1px solid var(--border-color);",
            "        }",
            "        .node-details p {",
            "            margin: 0.25rem 0;",
            "        }",
            "        .children-table-container {",
            "            padding: 0.75rem;",
            "            overflow-x: auto;",
            "        }",
            "        .children-table {",
            "            width: 100%;",
            "            border-collapse: collapse;",
            "        }",
            "        .children-table th, .children-table td {",
            "            padding: 0.5rem;",
            "            text-align: left;",
            "            border-bottom: 1px solid var(--border-color);",
            "        }",
            "        .children-table th {",
            "            background-color: var(--bg-light);",
            "        }",
            "        .stable, .better {",
            "            color: var(--stable-color);",
            "        }",
            "        .unstable, .worse {",
            "            color: var(--unstable-color);",
            "        }",
            "        .no-data {",
            "            text-align: center;",
            "            color: #757575;",
            "            font-style: italic;",
            "            padding: 2rem 0;",
            "        }",
            "        .footer {",
            "            margin-top: 2rem;",
            "            padding: 1rem 2rem;",
            "            background-color: var(--bg-light);",
            "            border-top: 1px solid var(--border-color);",
            "            text-align: center;",
            "            font-size: 0.9rem;",
            "            color: #757575;",
            "        }",
            "    </style>",
            "</head>",
            "<body>",
            "    <header>",
            f"        <h1>Failure Mode Explorer Report</h1>",
            "    </header>",
            f"    <div class='info-container'>",
            f"        <div class='info-box'>",
            f"            <p>Generated on: {timestamp}</p>",
            f"            <p>Threshold (minimum child nodes): {self.threshold}</p>",
            f"            <p>Percentile for stability classification: {self.percentile}%</p>",
            f"        </div>",
            f"    </div>",
        ]

    def _finalize_html(self):
        """完成HTML并写入文件"""
        self.html_content.extend([
            "    <div class='footer'>",
            "        <p>Failure Mode Explorer Report - Generated by FailureModeExplorer</p>",
            "    </div>",
            "</body>",
            "</html>"
        ])

        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.html_content))

        print(f"Report generated successfully: {self.output_file}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate Failure Mode Explorer Report')
    parser.add_argument('--folder', default="../processed_data/", help='Folder path containing JSON files')
    parser.add_argument('--threshold', type=int, default=5, help='Threshold for minimum number of child nodes')
    parser.add_argument('--percentile', type=int, default=20, help='Percentile for stability classification')
    parser.add_argument('--output', default="../analysis_results/failure_mode_explorer.html",
                        help='Output HTML file path')

    args = parser.parse_args()

    explorer = FailureModeExplorer(
        folder_path=args.folder,
        threshold=args.threshold,
        percentile=args.percentile,
        output_file=args.output
    )
    explorer.run()