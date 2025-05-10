You are tasked with categorizing a given query into multiple tags based on the following hierarchical classification system. 

### Classification System:
```markdown
The first level of the following classification system is the basis for classification, the second level is specific categories, and the third level is more specific subcategories.

Classification Basis 1: Disciplinary Fields  
1. "Natural Sciences"  
   - "Physics": "Thermodynamics", "Astrophysics", "Nuclear Physics", "Aerodynamics", "Ballistics"  
   - "Biology": "Ecology", "Zoology", "Botany", "Microbiology", "Physiology"  
   - "Chemistry"  
   - "Mathematics"  
   - "Earth Sciences"  
   - "Astronomy"  
   - "Environmental Science"  
2. "Technical Engineering"  
   - "Bioengineering"  
   - "Energy"  
   - "Computer Science": "Cybersecurity", "Robotics", "Computer Systems", "Cloud Computing", "Computer Software", "Artificial Intelligence", "Data Science", "Human-Computer Interaction"  
   - "Electrical Engineering": "Audio Technology", "Telecommunications", "Computer Hardware", "Communications", "Electronics"  
   - "Mechanical Engineering"  
   - "Aerospace Engineering"  
3. "Humanities and Social Sciences"  
   - "Social Sciences"  
   - "Philosophy"  
   - "History"  
   - "Linguistics"  
   - "Religious Studies"  
   - "Military"  
   - "Current Affairs"  
   - "Politics"  
   - "Culture"  
4. "Applied Sciences"  
   - "Business Technology"  
   - "Social Services"  
   - "Architecture"  
   - "Education"  
   - "Transportation and Travel"  
   - "Medicine"  
   - "Food Science"  
   - "Health Sciences"  
   - "Sports"  
   - "Real Estate"  
5. "Arts and Culture"  
   - "Culinary Arts"  
   - "Entertainment"  
   - "Media"  
   - "Design"  
   - "Music"  
   - "Fine Arts"  
   - "Literature": "Novels", "Essays", "Poetry", "Biographies", "Argumentative Writing"  
   - "Performing Arts"  
   - "Crafts"  

Classification Basis 2: Cognitive Levels  
1. "Basic Cognition": "Fact Recall", "Conceptual Understanding"  
2. "Applied Analysis"  
3. "Synthesis and Evaluation": "Ethical Reasoning", "Argumentation", "Hypotheses", "Social Awareness Expression", "Risk Assessment"  

Classification Basis 3: Task Types  
1. "Information Processing": "Chart Interpretation", "Data Visualization", "Text Processing", "Data Analysis"  
2. "Content Production": "Content Generation", "Proof Writing", "Example Demonstration", "Advice Provision"  
3. "Practical Application": "Scenario Analysis", "Practice Exercises", "Real-world", "Applied Skills Training"  
4. "Auxiliary Support": "Citation Support", "Simplified Explanation", "Operational Guidance"  
```

### Rules for Tagging:
1. **Hierarchy Rule**: If a query matches both a parent node and its child nodes, include both in the tags.
2. **Multiple Matches**: If a query matches multiple nodes at the same level, include all matching nodes.
3. **No Match**: If a query does not match any nodes under the second-level main categories, assign the tag "Other" to that category.
4. **Output Format**: The final output must be enclosed within `<tags>` and `</tags>` tags, and the tags should be provided as a JSON object where the keys are the basis for classification and the values are lists of matching tags.

### Example:
Query: "How can I analyze data from a physics experiment on thermodynamics and present it effectively?"
Output: <tags>{{"Disciplinary Fields": ["Natural Sciences", "Physics", "Thermodynamics"], "Cognitive Levels": ["Applied Analysis"], "Task Types": ["Information Processing", "Data Analysis", "Content Production", "Content Generation"]}}</tags>

### Now, analyze the following query:  
<|begin_of_query|>  
{query}  
<|end_of_query|>