import argparse
import os
import numpy as np
import statistics
from analysis_tools.base import BaseAnalyzer, load_json
import datetime


class AutomatedDifferenceReporter(BaseAnalyzer):
    def __init__(self, model_names, percentile=20, output_file="model_difference_report.html",
                 folder_path="../processed_data/"):
        """
        Initialize the difference reporter to compare multiple models.

        :param model_names: List of model names to compare (without .json extension)
        :param percentile: Percentile threshold for significant differences (default: 20)
        :param output_file: HTML output file path
        :param folder_path: Folder containing JSON files for the models
        """
        self.model_names = model_names
        self.percentile = percentile
        self.output_file = output_file
        self.folder_path = folder_path
        self.html_content = []
        self.model_data = {}
        self.root_rankings = {}
        self.nodes_with_differences = []

    def run(self):
        # Load all model data
        self._load_model_data()

        # Calculate root node differences
        self._calculate_root_differences()

        # Find nodes with significant differences
        self._find_significant_differences()

        # Generate HTML report
        self._generate_report()

        return self.nodes_with_differences

    def _load_model_data(self):
        """Load JSON data for all specified models"""
        for model_name in self.model_names:
            file_path = os.path.join(self.folder_path, f"{model_name}.json")
            if os.path.exists(file_path):
                self.model_data[model_name] = load_json(file_path)
            else:
                print(f"Warning: File not found for model {model_name}: {file_path}")

        # Verify we have data to process
        if not self.model_data:
            raise ValueError("No valid model data found. Please check model names and folder path.")

    def _calculate_root_differences(self):
        """Calculate the ranking value for each model at the root node"""
        for model_name, data in self.model_data.items():
            if 'ranking' in data:
                self.root_rankings[model_name] = data['ranking']
            else:
                print(f"Warning: No 'ranking' found in root node for model {model_name}")
                self.root_rankings[model_name] = None

    def _find_significant_differences(self):
        """Find nodes with significant differences across models"""
        # Keep track of all nodes and their statistics
        all_nodes = {}

        # Helper function to traverse the tree structure
        def traverse_all_models(path="root", node_refs=None):
            if node_refs is None:
                # First call - start with the root of each model
                node_refs = {model: data for model, data in self.model_data.items()}

            # Check if this node has ranking values for all models
            rankings = {}
            for model, node in node_refs.items():
                if node and 'ranking' in node:
                    rankings[model] = node['ranking']

            # If we have rankings for this node, calculate statistics
            if len(rankings) > 1:  # Need at least 2 models to compare
                values = list(rankings.values())
                std_dev = statistics.stdev(values) if len(values) > 1 else 0

                # Store node info with its standard deviation
                all_nodes[path] = {
                    'std_dev': std_dev,
                    'rankings': rankings,
                    'models': list(rankings.keys())
                }

            # Find all possible child keys across all models
            all_child_keys = set()
            for model, node in node_refs.items():
                if node:
                    for key, child in node.items():
                        if isinstance(child, dict):
                            all_child_keys.add(key)

            # Traverse into each child node
            for key in all_child_keys:
                next_refs = {}
                for model, node in node_refs.items():
                    if node and key in node and isinstance(node[key], dict):
                        next_refs[model] = node[key]
                    else:
                        next_refs[model] = None

                traverse_all_models(f"{path}.{key}", next_refs)

        # Start traversal from root
        traverse_all_models()

        # Calculate percentile threshold
        if all_nodes:
            std_devs = [node_info['std_dev'] for node_info in all_nodes.values()]
            if std_devs:
                threshold = np.percentile(std_devs, 100 - self.percentile)

                # Filter nodes with significant differences
                significant_nodes = {path: info for path, info in all_nodes.items()
                                     if info['std_dev'] >= threshold}

                # Sort by standard deviation (descending)
                self.nodes_with_differences = [(path, info) for path, info in
                                               sorted(significant_nodes.items(),
                                                      key=lambda x: x[1]['std_dev'],
                                                      reverse=True)]

    def _generate_report(self):
        """Generate the HTML report"""
        self._init_html()

        # Add report content
        self._add_model_overview()
        self._add_difference_table()

        self._finalize_html()

    def _add_model_overview(self):
        """Add model overview section to the report"""
        self.html_content.append("<h2>Model Root Rankings</h2>")
        self.html_content.append("<table border='1' cellpadding='5' cellspacing='0'>")
        self.html_content.append("<tr><th>Model</th><th>Root Ranking</th></tr>")

        for model, ranking in self.root_rankings.items():
            self.html_content.append(f"<tr><td>{model}</td><td>{ranking}</td></tr>")

        self.html_content.append("</table>")

    def _add_difference_table(self):
        """Add the main difference table to the report"""
        if not self.nodes_with_differences:
            self.html_content.append("<h2>No Significant Differences Found</h2>")
            self.html_content.append(
                "<p>No nodes with significant differences were found based on the given percentile threshold.</p>")
            return

        self.html_content.append(f"<h2>Nodes with Significant Differences (Top {self.percentile}%)</h2>")
        self.html_content.append("<p>The following nodes show significant variation in ranking across models:</p>")

        # Create the header row
        self.html_content.append("<table border='1' cellpadding='5' cellspacing='0'>")
        header_row = "<tr><th>Node Path</th><th>Std Dev</th>"
        for model in self.model_names:
            header_row += f"<th>{model}</th>"
        header_row += "</tr>"
        self.html_content.append(header_row)

        # Add rows for each significant node
        for path, info in self.nodes_with_differences:
            row = f"<tr><td>{path}</td><td>{info['std_dev']:.2f}</td>"

            for model in self.model_names:
                if model in info['rankings']:
                    ranking = info['rankings'][model]
                    root_ranking = self.root_rankings[model]

                    # Determine cell color based on comparison with root ranking
                    if root_ranking is not None:
                        if ranking < root_ranking:  # Better ranking (lower is better)
                            color = "green"
                        elif ranking > root_ranking:  # Worse ranking (higher is worse)
                            color = "red"
                        else:
                            color = "black"

                        row += f"<td style='color: {color};'>{ranking}</td>"
                    else:
                        row += f"<td>{ranking}</td>"
                else:
                    row += "<td>N/A</td>"

            row += "</tr>"
            self.html_content.append(row)

        self.html_content.append("</table>")

    def _init_html(self):
        """Initialize the HTML document"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.html_content = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "    <meta charset='UTF-8'>",
            "    <title>Model Difference Analysis Report</title>",
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
            f"    <h1>Model Difference Analysis Report</h1>",
            f"    <p>Generated on: {timestamp}</p>",
            f"    <p>Models compared: {', '.join(self.model_names)}</p>",
            f"    <p>Percentile threshold: {self.percentile}%</p>",
        ]

    def _finalize_html(self):
        """Finalize the HTML document and write to file"""
        self.html_content.extend([
            "    <div class='footer'>",
            "        <p>Automated Model Difference Analysis Report</p>",
            "    </div>",
            "</body>",
            "</html>"
        ])

        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.html_content))

        print(f"Report generated successfully: {self.output_file}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate HTML model difference report')
    parser.add_argument('--models', nargs='+', required=True,
                        help='List of model names to compare (without .json extension)')
    parser.add_argument('--percentile', type=float, default=20, help='Percentile threshold for significant differences')
    parser.add_argument('--folder', default="../processed_data/", help='Folder path containing JSON files')
    parser.add_argument('--output', default="../analysis_results/model_difference_report.html",
                        help='Output HTML file path')

    args = parser.parse_args()

    reporter = AutomatedDifferenceReporter(
        model_names=args.models,
        percentile=args.percentile,
        output_file=args.output,
        folder_path=args.folder
    )
    reporter.run()