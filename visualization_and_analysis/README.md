# Use Visualization and Analysis Toolkits

1. Place the evaluation results obtained from the previous step into the `visualization_and_analysis/evaluation_source_data` directory.
2. Enter the directory: `cd ./visualization_and_analysis`
3. Run `process_data.py` to process the data obtained above.
4. Run `auto_analysing.py` to get the analysis results.
5. If you want to run it locally, execute the following command in this directory:
```bash
python -m http.server 8001
```

# 缺少的功能
## 高优
1. 当展开太多，宽度不够，需要自适应的宽度
2. 展示模型太多，左边和右边有些不显示
## 中优
3. 需要做真正的主页，也就是介绍我们工作的主页，然后会跳转到我们的 Leaderboard
## 低优先
4. 根据关键词进行模型 Leaderboard 的制作（或者从树中选择分支，获得排名）