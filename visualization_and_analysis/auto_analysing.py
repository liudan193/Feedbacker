from analysis_tools import (AutomatedWeaknessReporter, AutomatedWeaknessAnalyzer, FailureModeExplorer,
                            AutomatedDifferenceReporter)


# AutomatedWeaknessReporter
params = {
    "folder_path": "./processed_data/",
    "threshold": 3,
    "output_file": "./analysis_results/automated_weakness_reporter.html"
}
analyzer = AutomatedWeaknessReporter(**params)
analyzer.run()


# AutomatedWeaknessAnalyzer
"""
# Set the environment variables
export OPENAI_API_BASE="http://0.0.0.0:8004"
export OPENAI_API_KEY="any"
"""
params = {
    "folder_path": "./processed_data/",
    "threshold": 3,
    "output_file": "./analysis_results/automated_weakness_analyzer.html",
    # "model_name": "gpt-4o",
    "model_name": "QwQ-32B",
    "max_concurrency": 32
}
analyzer = AutomatedWeaknessAnalyzer(**params)
analyzer.run()


# FailureModeExplorer
# Calculated using standard deviation
params = {
    "folder_path": "./processed_data/",
    "threshold": 5,  # Different from the above threshold
    "percentile": 20,  # Percentage based
    "output_file": "./analysis_results/failure_mode_explorer.html"
}
analyzer = FailureModeExplorer(**params)
analyzer.run()


# AutomatedDifferenceReporter
params = {
    "folder_path": "./processed_data/",
    # "model_names": ["deepseek-r1-250120", "deepseek-v3-250324"],
    "model_names": ["claude3.7-sonnet-20250219", "gpt-4o-2024-11-20"],
    "percentile": 20,  # Percentage based
    "output_file": "./analysis_results/automated_difference_reporter.html"
}
analyzer = AutomatedDifferenceReporter(**params)
analyzer.run()