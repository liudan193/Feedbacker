You are tasked with categorizing a given query into multiple tags based on the following hierarchical classification system. 

### Classification System:
```markdown
The first level of the following classification system is the basis for classification, the second level is main categories, and the third level is more specific subcategories.

Classification Basis 1: Task Types  
1. "Development and Maintenance": "Code Editing", "Code Conversion", "Code Analysis", "Code Generation", "Code Explanation", "Comment Generation", "Code Execution"  
2. "Debugging and Optimization": "Performance", "Error Handling", "Bug Fixing", "Logic Verification", "Testing", "Optimization"  
3. "Data Processing": "Database", "Data Manipulation", "Data Analysis", "Data Visualization", "File Processing", "Image Processing"  
4. "Tool Usage": "Platform Comparison", "Terminal Interaction", "Environment Configuration", "IDE Configuration", "Automated Workflow", "Version Control", "Test Development", "Automation"  
5. "Auxiliary Functions": "Regular Expression Parsing", "String Manipulation", "Fact Recall", "Learning Resources", "Conceptual Q&A", "Document Recommendation", "Self-Assessment"  

Classification Basis 2: Technical Domains  
1. "Data Structures and Algorithms"  
2. "Web Development"  
3. "Front-end Development": "DOM Manipulation", "Animation", "UI/UX Design", "Webpage Development", "Responsive Design"  
4. "Back-end Development": "API Development", "Microservices", "Database Integration", "Concurrent Programming"  
5. "Data Science": "Big Data", "Data Analysis Methods", "Model Creation", "Data Visualization Tools"  
6. "Systems Programming": "Cryptographic Programming", "Thread Concurrency", "Hardware Development", "Memory Management"  
7. "Game Development": "Game Logic", "Player Mechanics", "Physics Engine", "Graphics Rendering", "Sound Processing"  
8. "Artificial Intelligence": "Natural Language Processing", "Computer Vision", "Reinforcement Learning"  
9. "Embedded Development": "Sensors", "Hardware Interaction", "Firmware Development", "Hardware Technology", "Real-time Systems"  

Classification Basis 3: Programming Languages  
1. "General-purpose Languages": "C", "Python", "C#", "Java", "Rust", "Go", "Javascript", "TypeScript", "Swift"  
2. "Data Languages": "SQL", "R", "MATLAB", "PySpark"  
3. "Assembly Language"  
4. "Markup Languages": "HTML", "CSS", "XML", "LaTeX", "Markdown", "SVG", "JSON", "YAML"  
5. "Domain-specific Languages": "Solidity (Blockchain)", "GLSL (Graphics)", "CUDA (Parallel Computing)", "MQL (Finance)", "GDScript (Games)", "Excel (Spreadsheets)"  
6. "Scripting Languages": "VB", "Script", "Batch", "Shell", "Lua", "Ruby", "Perl", "PHP"  
```

### Rules for Tagging:
1. **Hierarchy Rule**: If a query matches both a parent node and its child nodes, include both in the tags.
2. **Multiple Matches**: If a query matches multiple nodes at the same level, include all matching nodes.
3. **No Match**: If a query does not match any nodes under the second-level main categories, assign the tag "Other" to that category.
4. **Output Format**: The final output must be enclosed within `<tags>` and `</tags>` tags, and the tags should be provided as a JSON object where the keys are the basis for classification and the values are lists of matching tags.

### Example:
Query: "How can I optimize a Python script that processes large datasets and visualizes the results?"
Output: <tags>{{"Task Types": ["Data Processing", "Data Analysis", "Data Visualization", "Debugging and Optimization", "Optimization"], "Technical Domains": ["Data Science", "Data Analysis Methods", "Data Visualization Tools"], "Programming Languages": ["General-purpose Languages", "Python"]}}</tags>

### Now, analyze the following query:  
<|begin_of_query|>  
{query}  
<|end_of_query|>