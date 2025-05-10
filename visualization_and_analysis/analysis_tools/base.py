import json
import os
from collections import defaultdict
import numpy as np
import copy

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

"""每一个都需要有 run 这个函数，功能是将结果保存到一个 html 中"""
class BaseAnalyzer(object):
    def run(self):
        raise NotImplementedError

