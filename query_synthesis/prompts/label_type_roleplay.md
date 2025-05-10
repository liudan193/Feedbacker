You are tasked with categorizing a given query into multiple tags based on the following hierarchical classification system. 

### Classification System:
```markdown
The first level of the following classification system is the basis for classification, the second level is specific categories, and the third level is more specific subcategories.

Classification Basis 1: Theme Types  
1. "Cultural"  
2. "Fantasy": "Medieval", "Fantasy", "Cosmic", "Horror", "Gothic", "Isekai", "Time Travel", "Animals", "Science Fiction", "Mythology", "Magic", "Supernatural"  
3. "Realistic": "Urban", "Life", "School", "History", "Business", "Medical", "Military", "Legal", "Family", "Relationships", "Work", "Sports", "Cooking", "Maritime", "Technology", "Art", "Music", "Nature", "Modern", "Professional", "Real World"  
4. "Emotional": "Emotional Support", "Sensitive", "Psychological", "Romantic", "Erotic"  
5. "Action-Adventure": "Spy", "War", "Crime", "Military", "Travel", "Survival", "Exploration"  
6. "Comedy": "Light Comedy", "Absurd Comedy", "Dark Comedy", "Surreal Comedy", "Humorous Comedy"  
7. "Horror": "Psychological Thriller", "Crime", "Supernatural Horror"  
8. "Thought": "Philosophy", "Religion", "Politics"  
9. "Safety"  
10. "Fictional Script"  
11. "Sensory Simulation"  

Classification Basis 2: Task Types  
1. "Creative": "Scriptwriting", "Description", "Scenario Creation", "Worldbuilding", "Character Design"  
2. "Simulation": "Military Simulation", "Life Scenario", "Gameplay", "Creative Simulation", "Social Simulation", "Business Decision", "Realistic Adventure", "Behavioral Simulation", "Task Simulation", "Functional Simulation", "Emotional Simulation", "Psychological Simulation"  
3. "Educational": "Language Learning", "Skill Training", "Concept Explanation", "Ethical Discussion", "Academic Guidance", "General Advice", "Trivia"  
4. "Interactive": "Character Interaction", "Scenario Interaction", "Dialogue Type", "Emotional Interaction", "Realistic Interaction", "Interactive Text Game", "Q&A", "Multiplayer", "Social Interaction"  
5. "Analytical": "Character Analysis", "Analytical Methods", "Culture", "Social and Political Issues", "Political Conspiracy", "Historical Events", "Social Issues", "Evaluation and Feedback", "Interpretation and Symbolic Analysis", "Scenario Analysis", "Decision Support", "Cross-Analysis", "Comparative Analysis", "Character Development"  
6. "Character-Centered"  

Classification Basis 3: Style Types  
1. "Humorous Style": "Vulgar", "Satirical", "Sitcom", "Light Humor"  
2. "Serious Style": "Political", "Thriller", "Realism", "Historical Drama", "Professional Guidance"  
3. "Dark Style": "Psychological Oppression", "Apocalyptic", "Gothic"  
4. "Experimental Style": "Freeform", "Formal", "Surreal", "Glitch Art", "Abstract Concepts", "Cross-Media", "Eccentric"  
5. "Healing Style"  
6. "Narrative"  
7. "Relaxed"  
```

### Rules for Tagging:
1. **Hierarchy Rule**: If a query matches both a parent node and its child nodes, include both in the tags.
2. **Multiple Matches**: If a query matches multiple nodes at the same level, include all matching nodes.
3. **No Match**: If a query does not match any nodes under the second-level main categories, assign the tag "Other" to that category.
4. **Output Format**: The final output must be enclosed within `<tags>` and `</tags>` tags, and the tags should be provided as a JSON object where the keys are the basis for classification and the values are lists of matching tags.

### Example:
Query: "Write a script for a medieval fantasy story involving a knight’s adventure and a magical encounter, with a humorous twist."
Output: <tags>{{"Theme Types": ["Fantasy", "Medieval", "Magic", "Comedy", "Humorous Comedy"], "Task Types": ["Creative", "Scriptwriting"], "Style Types": ["Humorous Style", "Light Humor", "Narrative"]}}</tags>

### Now, analyze the following query:  
<|begin_of_query|>  
{query}  
<|end_of_query|>