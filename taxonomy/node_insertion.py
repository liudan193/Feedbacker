import os
import argparse
import json
from tqdm import tqdm
import re
import copy
from functools import partial

import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from utils import utils


def parse_label_string(label_str):
    """Parse the raw label string and extract the JSON data"""
    try:
        # Match all {...} structures
        pattern = r"<decision>(.*?)(?:</decision>|<\\decision>|</\decision>)"
        json_matches = re.findall(pattern, label_str, re.DOTALL)
        if json_matches:
            json_str = json_matches[-1]
            return json_str
        else:
            raise ValueError("No valid JSON structure found")
    except (AttributeError, json.JSONDecodeError, ValueError) as e:
        print(f"Raw string: {label_str}")
        raise e


def add_node_to_tree(tree, new_node, llm_function):
    """
    Recursively traverse the tree and add a new node, using the LLM to decide which path to follow at each level.
    Args:
        tree (dict): The classification tree structure.
        new_node (str): The name of the new node to be added.
        llm_function: A function that takes the current keys of a node and the new node name,
                      and returns the next decision.
                      The return value could be an existing key or "new" indicating the creation of a new node at the current level.
    Returns:
        dict: The updated tree.
    """

    def traverse_recursively(current_tree, path=None):
        if path is None:
            path = []

        # Get the keys of the current level
        current_keys = list(current_tree.keys())
        if not current_keys:
            # If there are no keys at this level, directly add the new node
            current_tree[new_node] = {}
            return current_tree

        # Call the LLM function to decide the next step
        decision = llm_function(current_keys, new_node)
        if decision in current_keys:
            # LLM suggests continuing along the existing path
            current_tree[decision] = traverse_recursively(current_tree[decision], path + [decision])
        elif decision == "ADD":
            # LLM suggests adding the new node at the current level
            current_tree[new_node] = {}
        elif decision == "EXIST":
            pass  # No action is needed for existing nodes
        else:
            print(f"Error: LLM returned an invalid decision '{decision}', skipping this node")
            # exit(0)
        return current_tree

    return traverse_recursively(tree)


# LLM decision function
def find_node_llm_decision(current_keys, new_node, max_retries, base_url, api_key, model, sample_num, generation_params,
                           file, base_prompt):
    """
    This function is the LLM decision-making process.

    Args:
        current_keys (list): All keys of the current node.
        new_node (str): The new node to be added.

    Returns:
        str: "new" or one of the elements from current_keys.
    """

    obj = {
        "new_node": new_node,
        "current_keys": current_keys,
        "input_ques": [{"role": "user", "content": base_prompt.format(current_keys=current_keys, new_node=new_node)}]
    }
    unprocessed_data = [obj]
    decision = None
    i = 0
    while True:
        for responses, obj in utils.process_data_async(unprocessed_data, model, sample_num, base_url, api_key,
                                                       generation_params):
            try:
                decision = parse_label_string(responses[0])
                if decision not in current_keys + ["ADD", "EXIST"]:
                    raise ValueError(f"Invalid decision: {decision}")
                obj["raw_output"] = responses[0]
                obj["decision"] = decision
                file.write(json.dumps(obj, ensure_ascii=False) + '\n')
                file.flush()
                break
            except Exception as e:
                if i + 1 == max_retries:
                    obj["raw_output"] = responses[0]
                    obj["decision"] = "Exceeded maximum retry limit, skipping this node"
                    file.write(json.dumps(obj, ensure_ascii=False) + '\n')
                    file.flush()
                    return "Exceeded maximum retry limit, skipping this node"
        if decision:
            break
        i += 1
    return decision


if __name__ == "__main__":
    # Command-line argument parsing
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', type=str, default="roleplay", help='domain name')
    args = parser.parse_args()

    # Model parameters
    generation_params = {}  # {"temperature": 0.7, "top_p": 0.95}
    sample_num = 1
    model = "gpt-4.1"
    base_url = 'http://localhost:8006/'
    api_key = "any"

    # Path configuration
    output_path = "outputs/"
    os.makedirs(output_path, exist_ok=True)

    # Prompt configuration
    base_prompt = utils.read_prompt("prompts/node_insertion.md")

    # Data configuration
    # new_types: List of nodes to be inserted
    # init_cate_tree: Initial category tree structure
    domain = args.domain
    if domain == "roleplay":
        new_types = [
            "Evaluation and Feedback", "Science Fiction", "Clear Romance", "Light Ecchi", "Character Analysis",
            "Task Simulation", "Conceptual Q&A", "Absurd Humor", "Lively/Character Interaction", "Fictional Drama",
            "Erotic Mind Control", "Explanation and Symbol Analysis", "Safe Roleplaying", "New Noir",
            "Family/Life Events",
            "Fantasy/Comedy/Anime", "Religion", "Content Creation", "Life Snippets and Absurd Humor",
            "Personalized Storytelling",
            "Contemporary Comedy", "Contextual-based", "Gaming",
            "Interpersonal Relationships/Entertainment Roleplaying",
            "Social and Cultural Exploration", "Comedy Roleplaying", "Professional Guidance", "Casual", "Anime/Cute",
            "Hypothetical Analysis", "Family History", "Educational", "Family", "Realistic Roleplay, Exaggerated Tone",
            "General NPC Roleplay", "Humor/Life Snippets", "Abstract Glitch Aesthetics", "Musical Interaction",
            "General Background",
            "Personal Style", "Satirical Parody", "Medical", "Travel", "Maritime/Sailing",
            "Scenario Analysis", "Decision Support", "Medieval Fantasy", "Alternate History with Political Undertones",
            "Western",
            "Interpersonal Tension", "Gothic", "Modern/Dialogical", "Narrative-driven", "Humor/Crude",
            "Simulation", "Realistic Interaction", "Anime", "Psychological Manipulation", "Political Fiction",
            "Humor/Absurd", "Social Media Character Mimicry", "Crime", "Psychology", "Supportive/Realistic Interaction",
            "Modern", "Animal Interaction", "Custom Description", "Sex/Power Dynamics",
            "Professional and Philosophical",
            "Adventure (Simulation)", "Personality-Centered", "Drama", "Art", "Comedy/Adult Humor",
            "Professional", "Sports", "Cross-Analysis", "General Advice", "(Blank)", "Professional",
            "School Life", "Functional Simulation", "Pop Culture", "Contemporary Realism", "Realism",
            "Gameplay", "Humor and Satire", "Neutral/Emotional", "Emotional/Melancholic", "Creative Simulation",
            "Psychological Thriller", "Inspirational", "Trivia", "Scenario Creation", "Absurd",
            "Academic Roleplaying", "Real-World Scenario", "Dark Humor", "Worldbuilding", "Nature",
            "Emotional Simulation", "Comedy Education Roleplaying", "Action/Adventure", "Interpersonal Dynamics",
            "Gothic Horror",
            "Chit-Chat", "Quirky", "Comedy", "Roleplaying Game (RPG)", "Introspection",
            "Real/Organizational", "General", "Social Commentary", "Nutritional Roleplaying", "Emotional/Supportive",
            "Art Criticism", "Satirical Assistant", "History", "Art and Philosophy", "Political Conspiracy",
            "Suspense", "Real-Life Dilemmas", "Philosophical Introspection", "Psychological Simulation",
            "Real-World Roleplaying",
            "Ethical Reasoning", "Nature Simulation", "Character-Centered", "Real-World", "Educational Roleplaying",
            "Culture", "Business Drama", "Real-Life Assumptions", "Cosmic Horror", "Vague Roleplay Input",
            "Humor/Comedy", "Political", "Toxic Simulation", "Casual Interaction",
            "High Emotional Simulation and Digital Life Scenarios",
            "Concept Understanding", "Speculative/Hypothetical", "Film History and Analysis",
            "Satire/Social Commentary", "Humor",
            "Introspective", "Adult", "Custom: Financial Decision Simulation", "Cooking Creation", "Didactic",
            "General Roleplaying", "Animal Roleplaying", "Superheroes", "Emotional", "Conceptual Puzzles",
            "Surreal", "General Interactive Scenarios", "Dystopian Fantasy", "Absurd Comedy",
            "Conceptual Explanation in Context",
            "Love/Fetish", "Real-Life", "Dystopia", "ASMR/Sensory Simulation", "Analytical",
            "Crime Investigation", "Military", "Creative Problem Solving", "Game-Related", "Interactive Text Games",
            "Business", "Custom Description: Cross-Universe Scenario Creation", "Cooperative Roleplaying Game (RPG)",
            "Behavioral Tone", "Real Conversations",
            "Technical Expertise", "Psychodrama", "Dialogical", "Humor/Satire", "Satire",
            "Professional/Interview Simulation", "Consultant Role", "Real Adventure", "Post-Apocalyptic", "Lively",
            "Online Subculture Simulation", "Self-Help", "Abstract", "Racially Sensitive Content",
            "Multimedia Character Search",
            "Deceptive Conversations", "Creative and Profound", "General Conversations", "Philosophical Exploration",
            "Mature/Erotic",
            "Real Social Interaction", "Dialogue Generation", "Inspirational Speech Creation", "Surrealism",
            "Cyberpunk",
            "Professional Roleplaying", "Bold", "Technology", "Comparative Analysis", "Fanfiction",
            "Urban", "Niche Adult Exploration", "Game Show", "Business Simulation", "Spiritual",
            "Light Humor", "Dark Themes", "Text-Based Games", "Real Personality Simulation", "Q&A",
            "Behavioral Simulation", "Erotica", "Skill Training", "Interactive Experience",
            "Game-Based Real Challenges",
            "Science", "Comedy/Surrealism", "Mythology", "Fantasy", "Character Interaction",
            "Political Thriller", "Adventure", "RPG Mechanics", "Emotional Character Interaction", "Real-World Drama",
            "Retro", "Romance", "Lighthearted Conversations", "Halloween", "Interpersonal Relationships",
            "Office/Comedy", "Philosophy", "Character Exploration", "Supernatural", "Other",
            "Fitness", "Party Games", "Sensitive Scenarios", "Healing", "Dark Fantasy",
            "Horror", "Social Simulation", "Freeform", "Experimental", "Real-Life Simulation",
            "Speculative Fiction", "Language Learning", "Military Operations", "Technical Hierarchical Simulation",
            "Post-Breakup Scenario",
            "Spy Thriller", "Hip-Hop", "Contemporary", "Emoji Advice", "Fanfiction and Anime Debate",
            "Social Scenarios", "Science-Based Realism", "Special Communication", "Action/Psychological Strategy",
            "Friendly and Dialogical",
            "Casual", "Dark Comedy", "Isekai", "Teen Drama", "Daily Conversation",
            "Existential", "Character Development", "Social Issues", "Context Understanding", "Military Strategy",
            "Animation", "Crime/Drama", "Realism Novel", "Educational Comedy", "Logic",
            "Survival", "Life Snippets", "Absurd Dystopian Fantasy", "Economic Policy Simulation"
        ]
        init_cate_tree = {
            "Theme Types": {
                "Fantasy": {
                    "Medieval Fantasy": {},
                    "Mythology": {},
                    "Magic": {},
                    "Cyberpunk": {},
                    "Dystopian": {},
                    "Cosmic Horror": {},
                    "Gothic Horror": {},
                    "Supernatural Phenomena": {},
                    "Science Fiction": {},
                    "Isekai": {}
                },
                "Realistic": {
                    "Retro": {},
                    "Historical Events": {},
                    "Contemporary Life": {},
                    "Urban Life": {},
                    "Business": {},
                    "Medical": {},
                    "Military": {},
                    "Legal": {},
                    "Family": {},
                    "Relationships": {},
                    "School Life": {},
                    "Workplace": {},
                    "Sports": {},
                    "Cooking": {},
                    "Maritime": {},
                    "Technology": {},
                    "Art": {},
                    "Music": {},
                    "Nature": {}
                },
                "Emotional": {
                    "Romantic": {},
                    "Erotic": {},
                    "Psychological Drama": {},
                    "Emotional Support": {},
                    "Post-breakup Scenario": {}
                },
                "Action-Adventure": {
                    "Spy Thriller": {},
                    "Crime Investigation": {},
                    "Military Operations": {},
                    "Travel": {},
                    "Survival": {},
                    "Exploration": {},
                    "War Simulation": {}
                },
                "Comedy": {
                    "Absurd Comedy": {},
                    "Dark Comedy": {},
                    "Sitcom": {},
                    "Satirical Parody": {}
                },
                "Horror": {
                    "Psychological Thriller": {},
                    "Supernatural Horror": {},
                    "Apocalyptic Theme": {},
                    "Crime Thriller": {}
                },
                "Thought": {
                    "Philosophy": {},
                    "Religion": {},
                    "Existentialism": {},
                    "Ethics": {}
                },
                "Pop Culture": {
                    "Superheroes": {},
                    "Anime": {},
                    "Fanfiction": {},
                    "Game Mechanics": {},
                    "Social Media": {},
                    "Film and TV Adaptations": {}
                }
            },
            "Task Types": {
                "Creative": {
                    "Worldbuilding": {},
                    "Character Design": {},
                    "Scriptwriting": {},
                    "Inspirational Speech": {},
                    "Custom Description": {}
                },
                "Simulation": {
                    "Social Simulation": {},
                    "Military Simulation": {},
                    "Business Decision": {},
                    "Life Scenario": {},
                    "Behavioral Simulation": {},
                    "Realistic Adventure": {}
                },
                "Educational": {
                    "Language Learning": {},
                    "Skill Training": {},
                    "Concept Explanation": {},
                    "Ethical Discussion": {},
                    "Academic Guidance": {}
                },
                "Interactive": {
                    "Character Dialogue": {},
                    "Emotional Interaction": {},
                    "Puzzle Solving": {},
                    "Scenario Q&A": {},
                    "Daily Conversation": {}
                },
                "Analytical": {
                    "Character Psychology": {},
                    "Political Conspiracy": {},
                    "Historical Events": {},
                    "Social Issues": {},
                    "Cultural Comparison": {}
                }
            },
            "Style Types": {
                "Humorous Style": {
                    "Dark Humor": {},
                    "Absurd Humor": {},
                    "Satirical Humor": {},
                    "Sitcom": {}
                },
                "Serious Style": {
                    "Political Thriller": {},
                    "Realism": {},
                    "Historical Drama": {},
                    "Professional Guidance": {}
                },
                "Dark Style": {
                    "Gothic": {},
                    "Psychological Oppression": {},
                    "Crime Theme": {},
                    "Apocalyptic Theme": {}
                },
                "Healing Style": {
                    "Inspirational Growth": {},
                    "Nature Healing": {},
                    "Warm Daily Life": {},
                    "Emotional Support": {}
                },
                "Experimental Style": {
                    "Surrealism": {},
                    "Glitch Art": {},
                    "Abstract Concepts": {},
                    "Cross-Media": {}
                }
            }
        }
        output_save_path = "roleplay_cata_tree.jsonl"
        base_prompt = utils.read_prompt("prompts/node_insertion.md").replace("{init_tree}", utils.read_prompt(
            f"init_tree/{domain}.md"))
    elif domain == "coding":
        new_types = ['xml', 'jvm-based languages', 'Data Manipulation', 'Runtime Analysis', 'matlab', 'Design Work',
                     'sql', 'Version Information',
                     'postgresql', 'autohotkey', 'p5js', 'DOM Manipulation', 'Code Formatting', 'cpp', 'f#',
                     'Fact Recall', 'Software Management',
                     'Security', 'systemc', 'elixir', 'svg', 'modelica', 'sourcepawn', 'Data Analysis', 'qml',
                     'puzzlescript',
                     'clojure', 'nodejs', 'Game Logic Development', 'Performance Testing', 'c#', 'Skill Training',
                     'Software Version Control', '6502 assembly',
                     'r', 'terraform', 'p5.js', 'zig', 'Code Source Analysis', 'lisp', 'Tool Suggestion', 'gdscript 2',
                     'xaml',
                     'Custom: Feature Comparison', 'overpass query language', 'vbscript', 'Documentation', 'tsql',
                     'guile scheme',
                     'Practical Application', 'Code Editing', 'lc3 assembly', 'GUI Implementation', 'excel formulas',
                     'UI/UX Assistance', 'Data Processing',
                     'batch script', 'freeswitch', 'gnuplot', 'Platform Comparison', 'Feedback', 'Logical Reasoning',
                     'tailwindcss', 'Code Review',
                     'scilab', 'plsql', 'Database Interaction', 'abap', 'next.js', 'minizinc',
                     'Configuration Assistance', 'solidity', 'autolisp',
                     'verilog', 'chisel', 'Code Translation', 'spark sql', 'ruby', 'Code Optimization', 'html5',
                     'delphi', 'Code Refinement',
                     'UI Development', 'Automation Setup', 'Feature Enhancement', 'html', 'Automation', 'xacml',
                     'nginx', 'shell', 'arm assembly',
                     'Optimization', 'js', 'tcl', 'Integration', 'Code Generation', 'Code Execution',
                     'Regression Modeling', 'ebpf', 'Feature Development', 'mermaid',
                     'gradle', 'jinja', 'go', 'curl', 'docker-compose', 'svelte js', 'tableau', 'react', 'json',
                     'ffmpeg', 'Database Processing', 'amibroker', 'Model Creation', 'foxpro', 'jsfx', 'C',
                     'Algorithm Development', 'forth',
                     'pddl', 'Web Development', 'Machine Learning', 'oracle sql', 'framework comparison', 'powershell',
                     'bash',
                     'Threading and Concurrency', 'Performance Improvement', 'Computation', 'Learning Methods', 'git',
                     'Code Conversion', 'Code Simplification', 'hcl', 'kotlin',
                     'x86_64 assembly', 'sql/postgres', 'dotnet', 'Animation and Interaction', 'mql5', 'rust',
                     'Setup and Configuration', 'vbs',
                     'perl', 'prism', 'Creative Ideation', 'Proof Writing', 'Data Cleaning and Preparation',
                     'mathematica', 'Animation', 'Conceptual Discussion',
                     'Container Management', 'c64 basic', 'Source Code Retrieval', 'Visualization', 'spss', 'g-code',
                     'Recommendation', 'Parsing and Transformation',
                     'html/css/javascript', 'nim', 'vue.js', 'UI Improvement', 'Code Analysis', 'Project Ideation',
                     'pine', 'metal',
                     'graphviz', 'dockerfile', 'Code Integration', 'json-ld', 'Geospatial Analysis', 'systemverilog',
                     'Correctness Proof',
                     'dot', 'zpl', 'postscript', 'Game Logic/Player Mechanics', 'c99', 'System Design', 'Plotting',
                     'streamlit', 'docker',
                     'excel', 'Game Design Mechanics', 'julia', 'jinja2', 'haskell', 'Performance Optimization',
                     'c/c++', 'String Manipulation', 'Sound Effects',
                     'svelte', 'Code Feedback', 'Algorithm Design', 'Evaluation and Feedback', 'Manual Code Execution',
                     'shell scripting',
                     'Regular Expression Parsing', 'IDE Configuration', 'Architecture Design',
                     'Command Line Automation', 'apache server configuration',
                     'Bug Fixing', 'hana sql', 'Software Installation and Configuration', 'pytorch', 'hdl', 'assembly',
                     'ansible', 'batch',
                     'vite js', 'Creative Problem Solving', 'Environment Setup', 'UX Design', 'mongodb', 'gdshader',
                     'python', 'regex',
                     'User Input Handling', 'null', 'UI/UX Code', 'c++', 'Cryptographic Programming',
                     'Algorithm Analysis', 'episode interactive',
                     'mathml', 'UI Design', 'Conceptual Design', 'plpgsql', 'node.js', 'graphql', 'batch scripting',
                     'typescript',
                     'latex', 'GUI Development', 'antlr3', 'odin', 'Event Handling', 'extendscript', 'Testing', 'move',
                     'Content Optimization',
                     'sed', 'html/css/js', 'matter.js', 'wgsl', 'cuda', 'prolog', 'Comparative Analysis',
                     'react native',
                     'Learning Resources', 'Problem Solving', 'unreal engine blueprints', 'Plotting and Visualization',
                     'php', 'sparql', 'C++',
                     'Image Processing', 'jruby', 'Code Compilation', 'javascript', 'File Operations',
                     'File Conversion', 'Conceptual Exploration of Coding Contributions',
                     'mysql', 'csharp', 'makefile', 'pseudo-programming language', 'groovy', 'Programming Ethics',
                     'Workflow Automation',
                     'null', 'html/css', 'flask', 'Data Visualization', 'swift', 'taichi', 'sqlite', 'Code Explanation',
                     'dax', 'vba',
                     'Database Operations', 'assembly language', 'stateflow', 'express.js', 'Database Integration',
                     'Source Analysis', 'tikz',
                     'ahk', 'lean', 'yaml', 'gml', 'redis', 'peoplecode', 'Environment Management',
                     'Event-driven Programming', 'puppet', 'lean4',
                     'pl/sql', 'spa-json', 'Callback Handling', 'mips', 'power query', 'database design',
                     'Self-assessment', 'vb.net',
                     'nasm', 'java', 'awk', 'jsf', 'Error Handling', 'golang', 'markdown',
                     'Self-reflective Programming Strengths', 'pyspark',
                     'eng', 'nix', 'jq', 'mql4', 'javascript/react', 'vimscript', 'Simulation', 'Debugging',
                     'Custom Description: Unclear Coding Tasks', 'docker compose', 'File Processing',
                     'Library Recommendation', 'Content Creation', 'lua',
                     'Code Refactoring', 'gdscript', 'UI/UX Design', 'html css javascript',
                     'Data Structures and Algorithms', 'Statistical Analysis',
                     'mit app inventor', 'Build Configuration', 'm query', 'aws cli', 'postcss', 'Code Understanding',
                     'vue', 'c',
                     'Code Completion', 'Code Security', 'shell script', 'pine script', 'Conceptual Q&A',
                     'Code Alignment Evaluation', 'Configuration Management',
                     'Concurrency', 'C#', None, 'react.js', 'Terminal Interaction', 'Using AI for Data Queries', 'glsl',
                     'tensorflow', 'less',
                     'houdini', 'swiftui', 'vhdl', 'coq', 'ocaml', 'plantuml', 'dart', 'pinescript', 'Code Debugging',
                     'mql',
                     'Algorithm Implementation', 'Correlation Analysis', 'verse', 'Custom Logic Addition', 'scala',
                     'UI/UX Programming', 'apex', 'Simulation',
                     'Tool Recommendation', 'css', 'blueprints', 'Exploratory Data Analysis (EDA)']
        init_cate_tree = {
            "Task Types": {
                "Development and Maintenance": {
                    "Code Generation": {},
                    "Code Explanation": {},
                    "Comment Generation": {},
                    "Code Editing": {},
                    "Code Review": {},
                    "Code Completion": {},
                    "Code Translation": {},
                    "Code Execution": {},
                },
                "Debugging and Optimization": {
                    "Debugging": {},
                    "Performance Optimization": {},
                    "Error Handling": {},
                    "Bug Fixing": {},
                    "Runtime Analysis": {},
                    "Logic Verification": {},
                },
                "Data Processing": {
                    "Data Cleaning": {},
                    "Data Analysis": {},
                    "Data Visualization": {},
                    "Database Operations": {},
                    "File Processing": {},
                    "Image Processing": {},
                    "Geospatial Analysis": {},
                    "Data Transformation": {},
                },
                "System Design": {
                    "Architecture Design": {},
                    "Algorithm Design": {},
                    "Feature Development": {},
                    "Security Design": {},
                    "Concurrent Programming": {},
                    "Interface Design": {},
                    "Hardware Interaction": {},
                },
                "Tools and Workflow": {
                    "Automation Scripts": {},
                    "Version Control": {},
                    "Environment Configuration": {},
                    "Test Development": {},
                    "IDE Configuration": {},
                    "Container Management": {},
                    "Continuous Integration": {},
                    "Build Configuration": {},
                    "Software Management": {},
                },
                "Auxiliary Functions": {
                    "Document Generation": {},
                    "Tool Recommendation": {},
                    "Code Understanding": {},
                    "Regular Expression Parsing": {},
                    "Learning Resource Recommendation": {},
                    "String Manipulation": {},
                },
            },
            "Technical Domains": {
                "Front-end Development": {
                    "UI Design": {},
                    "UX Design": {},
                    "Webpage Development": {},
                    "Animation Implementation": {},
                    "DOM Manipulation": {},
                    "Event-driven Programming": {},
                    "Responsive Design": {},
                },
                "Back-end Development": {
                    "API Development": {},
                    "Microservices": {},
                    "Database Integration": {},
                    "Concurrent Programming": {},
                },
                "Data Science": {
                    "Machine Learning": {},
                    "Statistical Analysis": {},
                    "Big Data Processing": {},
                    "Regression Modeling": {},
                    "Model Creation": {},
                },
                "Systems Programming": {
                    "Memory Management": {},
                    "Driver Development": {},
                    "Cryptographic Programming": {},
                    "Hardware Control": {},
                },
                "Game Development": {
                    "Physics Engine": {},
                    "Graphics Rendering": {},
                    "Sound Processing": {},
                    "Game Logic Design": {},
                    "Player Mechanics Design": {},
                },
                "Artificial Intelligence": {
                    "Natural Language Processing": {},
                    "Computer Vision": {},
                    "Reinforcement Learning": {},
                },
                "Embedded Development": {
                    "Sensor Programming": {},
                    "Real-time Systems": {},
                    "Hardware Interaction": {},
                    "Firmware Development": {},
                },
            },
            "Programming Languages": {
                "General-purpose Languages": {
                    "Python": {},
                    "Java": {},
                    "C": {},
                    "C++": {},
                    "JavaScript": {},
                    "C#": {},
                    "Rust": {},
                    "Go": {},
                    "TypeScript": {},
                    "Kotlin": {},
                    "Swift": {},
                },
                "Data Languages": {
                    "SQL": {},
                    "R": {},
                    "MATLAB": {},
                    "DAX": {},
                    "PySpark": {},
                },
                "System Languages": {
                    "Assembly": {},
                    "Verilog": {},
                },
                "Markup Languages": {
                    "HTML": {},
                    "CSS": {},
                    "XML": {},
                    "JSON": {},
                    "LaTeX": {},
                    "Markdown": {},
                },
                "Domain-specific Languages": {
                    "Solidity (Blockchain)": {},
                    "GLSL (Graphics)": {},
                    "MQL (Finance)": {},
                    "GDScript (Games)": {},
                    "CUDA (Parallel Computing)": {},
                },
                "Scripting Languages": {
                    "Bash": {},
                    "PowerShell": {},
                    "Lua": {},
                    "Ruby": {},
                    "Perl": {},
                },
            },
        }
        output_save_path = "coding_cata_tree.jsonl"
        base_prompt = utils.read_prompt("prompts/node_insertion.md").replace("{init_tree}", utils.read_prompt(
            f"init_tree/{domain}.md"))
    elif domain == "knowledge":
        new_types = ['Skateboarding', 'Aerodynamics', 'Geology', 'Health and Nutrition', 'Marketing', 'Energy',
                     'Psychology', 'Logistics', 'Film', 'Mathematics',
                     'Business Technology', 'Social Awareness Expression', 'Neuroscience', 'Project Management',
                     'Communication', 'Nutrition', 'International Relations', 'Art and Design',
                     'Climate Science', 'Computer Networks', 'Human-Computer Interaction', 'Cooking', 'Sports Science',
                     'Esports', 'Literature', 'Government', 'Health and Fitness',
                     'Art', 'Folklore', 'Computer Science', 'Advertising', 'Business Operations', 'Military',
                     'Military Logistics', 'Career Development', 'Food Science',
                     'Sustainability', 'Cybersecurity', 'Advice', 'Beverages', 'Content Generation',
                     'Audio Engineering', 'Telecommunications', 'Career', 'Fashion', 'Examples',
                     'Taxation', 'Self-Improvement', 'Consumer Technology', 'Classification', 'Business',
                     'Artificial Intelligence', 'Film Studies', 'Natural History', 'Gaming',
                     'Skills Training', 'Space Exploration', 'Advice with Reasoning', 'Religious Studies',
                     'Data Analysis', 'Proof Writing', 'Martial Arts', 'Evaluation and Feedback',
                     'Ballistics', 'Business Studies', 'Information Technology', 'Textiles', 'Civic Education',
                     'Software Architecture', 'Home Appliances', 'Biology', 'Electronics',
                     'Social Policy', 'Mechanical Engineering', 'Transportation', 'Cosmology', 'Novels', 'Automotive',
                     'Content Creation', 'Technology', 'Music History',
                     'Materials Science', 'Current Affairs', 'Comparative Analysis', 'Astronomy', 'Chemistry',
                     'Audio Technology', 'Food', 'Design', 'Language Translation',
                     'Social Media', 'Aviation', 'Culinary Arts', 'Travel', 'Business Processes', 'Analysis',
                     'Text Summarization', 'Immigration Policy', 'Computer Vision',
                     'Automotive Engineering', 'History and Geopolitics', 'Operating Systems', 'Botany',
                     'Visual Presentation Creation', 'Computers and Technology', 'Real-World Applications',
                     'Space Science', 'Simplification', 'Sports', 'Scenario Analysis', 'Education',
                     'Professional Development', 'Language Learning', 'Management', 'Pharmacology',
                     'Space Technology', 'Business and Economics', 'News', 'Translation', 'Philosophy',
                     'Computer Hardware', 'Anime/Manga', 'Mechanics',
                     'Evolutionary Biology', 'Wildlife Management', 'Urban Planning', 'Job Market',
                     'Environmental Science', 'Political Science', 'Robotics',
                     'Logical Deduction', 'Internet Culture', 'English Language', 'Travel and Tourism',
                     'Food and Beverages', 'Networking Technology', 'Evaluation', 'Cloud Computing',
                     'Etymology', 'Geopolitics', 'Personal Development', 'Entertainment', 'Social Services',
                     'Career Counseling', 'General Knowledge', 'Physics', 'Accounting',
                     'Problem Solving', 'Supporting Evidence', 'Chess', 'History of Science', 'Software Testing',
                     'Current Events', 'Parenting', 'Popular Culture', 'Agriculture',
                     'Computation', 'Theology', 'Arts and Crafts', 'Population Estimation', 'Source Provision',
                     'Business Management', 'Paleontology', 'Mental Health', 'Health',
                     'Finance', 'Legal Studies', 'Consumer Goods', 'Software Technology', 'Consumer Advice',
                     'Linguistics', 'Practice Exercises', 'Veterinary Medicine',
                     'Data Visualization', 'Zoology', 'Personal Finance', 'Crafts', 'Null', 'Biology/Ecology',
                     'Exercise Science', 'Real Estate',
                     'Media/Entertainment', 'Geography', 'Chart Interpretation', 'Sociolinguistics', 'Social Issues',
                     'Hypothetical Thinking', 'Science', 'Engineering',
                     'Nuclear Physics', 'Sociology', 'History', 'Summary Summarization', 'Practical Application',
                     'Cultural Symbols', 'Public Health', 'Sexuality', 'Horticulture', 'Cuisine',
                     'Game Design', 'Fact Recall', 'Music Theory', 'Ethical Reasoning', 'Physiology',
                     'Self-Development', 'Military Technology', 'Practical Problem Solving',
                     'Entrepreneurship', 'Business and Management', 'Politics', 'Hospitality',
                     'Creative Problem Solving', 'Media/Literature', 'Culture', 'Aerospace Engineering',
                     'Child Development', 'Cultural Studies', 'Audio Processing', 'Health and Wellness', 'Statistics',
                     'Animal Behavior', 'Mythology', 'Religion', 'Leisure',
                     'Thermodynamics', 'Video Games', 'Information Security', 'Fictional Media', 'Digital Art',
                     'Social Dynamics', 'Automotive Industry', 'Art and Culture',
                     'Military Science', 'Electrical Engineering', 'Computer Engineering', 'Fictional Worlds',
                     'Interpersonal Communication', 'Computer Systems', 'Anatomy', 'Art and Photography',
                     'Business Strategy', 'Causal Reasoning', 'Language and Culture', 'Architecture', 'Career Guidance',
                     'Consumer Products', 'Cognitive Science', 'Meteorology',
                     'Demographics', 'Opinion-Based', 'Software Engineering', 'Earth Sciences', 'Renewable Energy',
                     'Statistics and Probability', 'Firearms', 'Economics',
                     'Automotive Technology', 'Ethics', 'Systems Administration', 'Ecology', 'Conceptual Understanding',
                     'Business and Technology', 'Lifestyle', 'Citation', 'Society',
                     'Law', 'Data Science', 'Sustainable Fashion', 'Consumer Electronics', 'Astrology', 'Music',
                     'Creative ID Generation', 'Literature and Mythology',
                     'Anthropology', 'E-commerce', 'Photography', 'Software', 'Practical Advice', 'Tourism',
                     'Governance', 'Cryptocurrency', 'Media Studies', 'Anime',
                     'Hardware', 'Cosmetics', 'Computer Architecture', 'Digital Design', 'Biography', 'Personal Care',
                     'Television', 'Spirituality', 'Machine Learning', 'Language',
                     'Sociopolitical Issues', 'Media and Entertainment', 'Event Planning', 'Biochemistry',
                     'Social Sciences', 'Medicine', 'Fitness', 'Public Policy',
                     'Astrophysics', 'Biotechnology', 'Healthcare', 'Cryptography', 'Media', 'Art History',
                     'Argument Evaluation', 'Fictional Lore']
        init_cate_tree = {
            "Disciplinary Fields": {
                "Natural Sciences": {
                    "Physics": {
                        "Thermodynamics": {},
                        "Astrophysics": {},
                        "Nuclear Physics": {},
                        "Aerodynamics": {},
                    },
                    "Biology": {
                        "Ecology": {},
                        "Evolutionary Biology": {},
                        "Zoology": {},
                        "Botany": {},
                        "Microbiology": {},
                    },
                    "Chemistry": {
                        "Biochemistry": {},
                        "Materials Science": {},
                    },
                    "Mathematics": {},
                    "Earth Sciences": {
                        "Geology": {},
                        "Meteorology": {},
                        "Paleontology": {},
                        "Geography": {},
                    },
                    "Astronomy": {
                        "Cosmology": {},
                    },
                    "Environmental Science": {
                        "Climate Science": {},
                    },
                },
                "Technical Engineering": {
                    "Computer Science": {
                        "Artificial Intelligence": {},
                        "Cybersecurity": {},
                        "Data Science": {},
                        "Robotics": {},
                        "Software Engineering": {},
                        "Computer Networks": {},
                        "Cloud Computing": {},
                        "Cryptography": {},
                    },
                    "Electrical Engineering": {
                        "Telecommunications": {},
                        "Computer Hardware": {},
                    },
                    "Mechanical Engineering": {},
                    "Aerospace Engineering": {},
                    "Biotechnology": {},
                    "Energy Engineering": {},
                },
                "Humanities and Social Sciences": {
                    "Philosophy": {
                        "Ethics": {},
                    },
                    "History": {
                        "History of Science": {},
                        "Military History": {},
                    },
                    "Linguistics": {
                        "Sociolinguistics": {},
                        "Etymology": {},
                    },
                    "Political Science": {
                        "Geopolitics": {},
                        "International Relations": {},
                    },
                    "Economics": {
                        "Finance": {},
                        "Personal Finance": {},
                        "Marketing": {},
                        "Accounting": {},
                    },
                    "Law": {},
                    "Religious Studies": {},
                    "Military": {},
                    "Sociology": {
                        "Anthropology": {},
                        "Cultural Studies": {},
                    },
                    "Psychology": {
                        "Cognitive Science": {},
                        "Neuroscience": {},
                    },
                },
                "Applied Sciences": {
                    "Medicine": {
                        "Pharmacology": {},
                        "Public Health": {},
                        "Veterinary Medicine": {},
                        "Anatomy": {},
                    },
                    "Education": {
                        "Career Development": {},
                        "Language Learning": {},
                    },
                    "Architecture": {},
                    "Food Science": {},
                    "Transportation": {},
                    "Health Sciences": {
                        "Nutrition": {},
                        "Mental Health": {},
                        "Fitness": {},
                    },
                },
                "Arts and Culture": {
                    "Music": {
                        "Music Theory": {},
                        "Music History": {},
                    },
                    "Literature": {
                        "Novels": {},
                        "Poetry": {},
                        "Mythology": {},
                    },
                    "Film": {
                        "Film Studies": {},
                    },
                    "Gaming": {
                        "Video Games": {},
                        "Esports": {},
                        "Game Design": {},
                    },
                    "Fashion": {},
                    "Photography": {},
                    "Design": {
                        "Digital Design": {},
                    },
                    "Performing Arts": {},
                    "Anime": {},
                },
            },
            "Cognitive Levels": {
                "Basic Cognition": {
                    "Fact Recall": {},
                    "Conceptual Understanding": {},
                },
                "Applied Analysis": {
                    "Problem Solving": {},
                    "Causal Reasoning": {},
                    "Comparative Analysis": {},
                    "Logical Deduction": {},
                },
                "Synthesis and Evaluation": {
                    "Ethical Reasoning": {},
                    "Argument Evaluation": {},
                    "Hypothetical Thinking": {},
                    "Social Awareness Expression": {},
                    "Risk Assessment": {},
                },
            },
            "Task Types": {
                "Information Processing": {
                    "Translation": {},
                    "Text Summarization": {},
                    "Chart Interpretation": {},
                    "Data Visualization": {},
                    "Classification": {},
                    "Computation": {},
                },
                "Content Production": {
                    "Content Generation": {
                        "Creative Generation": {},
                        "Visual Creation": {},
                    },
                    "Proof Writing": {},
                    "Advice Provision": {},
                    "Example Demonstration": {},
                },
                "Practical Application": {
                    "Skills Training": {},
                    "Scenario Analysis": {},
                    "Practice Exercises": {},
                },
                "Auxiliary Support": {
                    "Citation Support": {
                        "Source Provision": {},
                        "Evidence Support": {},
                    },
                    "Simplified Explanation": {},
                    "Operational Guidance": {},
                },
            },
        }
        output_save_path = "knowledge_cata_tree.jsonl"
        base_prompt = utils.read_prompt("prompts/node_insertion.md").replace("{init_tree}", utils.read_prompt(
            f"init_tree/{domain}.md"))
    elif domain == "mathematics":
        new_types = ['Statics', 'Acoustics', 'Mathematical Foundations', 'Scenario Analysis',
                     'Combinatorics and Probability', 'Basic Arithmetic', 'Group Theory', 'Problem Solving',
                     'Mechanical Vibrations', 'Applied Physics Computation', 'Algebra and Number Theory',
                     'Function Design', 'Numerical Methods', 'Number Comparison', 'Linear Systems',
                     'Computational Complexity Theory', 'Game Theory', 'History of Mathematics', 'Formal Logic',
                     'Combinatorial Structures', 'Accounting', 'Number Systems and Binary Arithmetic',
                     'Pre-Calculus', 'Logic', 'Patterns and Sequences', 'Set Theory', 'Graphing and Visualization',
                     'Proportion', 'Geometry',
                     'Physics-Related Problem Solving', 'Mathematics for Physics and Engineering', 'Cost Calculation',
                     'Proportions and Ratios', 'Combinatorics and Symmetry', 'Logic and Foundations',
                     'Differential Equations and Systems Theory', 'Logic and Arithmetic', 'Date Calculation',
                     'Coordinate Geometry', 'Stochastic Processes', 'Logical Reasoning', 'Discrete Mathematics',
                     'Numerical Analysis', 'Curriculum Design', 'Physics and Mechanics', 'Finance and Accounting',
                     'Conceptual Understanding', 'Misleading Example Generation', 'Physics and Electromagnetism',
                     'Applied Mechanics', 'Statistics and Probability', 'Mathematics for Physics', 'Algebra',
                     'Classical Mechanics', 'Automata Theory', 'Comparative Analysis', 'Probability',
                     'Thermodynamics', 'Linear Programming', 'Mathematics for Machine Learning', 'Signal Processing',
                     'Logic and Information Theory', 'Database Theory', 'Economics', 'Optimization',
                     'Control Theory', 'Probability and Statistics', 'Fourier Analysis and Transforms', 'Calculus',
                     'Logical Reasoning and Constraints', 'Word Problems', 'Calendar Mathematics',
                     'Theoretical Analysis', 'Computation', 'Finance and Financial Mathematics',
                     'Dynamical Systems and Optimization', 'Physics-Related Mechanics', 'Unit Conversion',
                     'Critical Review',
                     'Arithmetic', 'Series and Sequences', 'Practical Application', 'Analysis', 'Puzzle Solving',
                     'Theoretical Computer Science', 'Mathematics for Finance', 'Proof Writing',
                     'Number Systems', 'Electrical Physics', 'Combinatorics and Limits', 'Arithmetic and Logic',
                     'Physics-Oriented Mathematics', 'Mechanics', 'Mathematical Analysis', 'Complex Analysis',
                     'Number Theory', 'Physics', 'Modular Arithmetic', 'Complex Numbers', 'Mathematical Physics',
                     'Sequences and Series', 'Optimal Control Theory', 'Measure Theory', 'Trigonometry',
                     'Topology', 'Crystallography and Geometry', 'Special Functions', 'Null Values', 'Combinatorics',
                     'Functions and Transforms', 'Finance', 'Sequences and Combinatorics',
                     'Information Theory', 'Mathematics for Astronomy', 'Classification', 'Counting',
                     'Symbols and Notations', 'Proportions and Scaling', 'Astronomy and Astrophysics',
                     'Image Processing', 'Mathematical Logic', 'Physics-Related Computation',
                     'Kinematics and Rotational Motion', 'Applied Mathematics in Games', 'Kinematics',
                     'Mathematics for Finance and Investment', 'Algebraic Geometry',
                     'Accounting and Business Mathematics', 'Linear Algebra', 'Dynamical Systems',
                     'Physics (Mechanics)', 'Logarithms',
                     'Computational Mathematics', 'Multiple Subfields', 'Sequences', 'Mathematical Astronomy',
                     'Financial Mathematics', 'Creative Problem Solving', 'Creative Modeling', 'Measurement',
                     'Theoretical Reasoning', 'Graph Theory', 'Functional Analysis and Operator Theory', 'Statistics',
                     'Applied Mathematics', 'Physics/Mechanics', 'Operations Research',
                     'Logic and Puzzle Solving', 'Coding Theory', 'Abstract Algebra', 'Real Analysis',
                     'Differential Equations', 'Combinatorics and Geometry', 'Recreational Mathematics',
                     'Electromagnetism',
                     'Linear Algebra and Geometry', 'Algebra and Calculus', 'Fact Recall', 'Boolean Algebra',
                     'Category Theory']
        init_cate_tree = {
            "Mathematical Subfields": {
                "Algebra": {
                    "Linear Algebra": {},
                    "Abstract Algebra": {},
                    "Boolean Algebra": {},
                    "Algebraic Geometry": {},
                    "Group Theory": {},
                    "Modular Arithmetic": {},
                    "Logarithms": {},
                },
                "Geometry": {
                    "Coordinate Geometry": {},
                    "Differential Geometry": {},
                    "Topology": {},
                    "Crystallography": {},
                },
                "Analysis": {
                    "Real Analysis": {},
                    "Complex Analysis": {},
                    "Functional Analysis": {},
                    "Mathematical Analysis": {},
                    "Fourier Analysis": {},
                    "Measure Theory": {},
                    "Limits": {},
                    "Calculus": {},
                },
                "Probability and Statistics": {
                    "Probability Theory": {},
                    "Statistics": {},
                    "Stochastic Processes": {},
                },
                "Discrete Mathematics": {
                    "Graph Theory": {},
                    "Combinatorics": {},
                    "Game Theory": {},
                    "Automata Theory": {},
                },
                "Mathematical Foundations": {
                    "Set Theory": {},
                    "Arithmetic": {},
                    "Number Systems": {},
                    "Category Theory": {},
                    "History of Mathematics": {},
                },
                "Applied Mathematics": {
                    "Physics": {
                        "Mechanics": {},
                        "Dynamical Systems": {},
                        "Control Theory": {},
                        "Electrical Physics": {},
                        "Astronomy": {},
                        "Acoustics": {},
                        "Electromagnetism": {},
                    },
                    "Signals": {
                        "Signal Processing": {},
                        "Information Theory": {},
                        "Image Processing": {},
                        "Machine Learning": {},
                    },
                    "Financial Mathematics": {},
                    "Operations Research": {},
                    "Game Mathematics": {},
                },
                "Numerical Analysis": {},
                "Number Theory": {},
            },
            "Task Types": {
                "Computation": {
                    "Arithmetic Operations": {},
                    "Numerical Methods": {},
                    "Symbolic Computation": {},
                },
                "Problem Solving": {
                    "Practical Application": {},
                    "Word Problems": {},
                    "Creative Modeling": {},
                },
                "Logical Reasoning": {
                    "Logical Deduction": {},
                    "Theoretical Derivation": {},
                    "Puzzle Solving": {},
                },
                "Visualization": {
                    "Geometric Drawing": {},
                    "Function Graphing": {},
                    "Data Visualization": {},
                },
                "Modeling": {
                    "Differential Equation Modeling": {},
                    "Statistical Modeling": {},
                },
                "Conceptual Understanding": {},
            },
        }
        output_save_path = "mathematics_cata_tree.jsonl"
        base_prompt = utils.read_prompt("prompts/node_insertion.md").replace("{init_tree}", utils.read_prompt(
            f"init_tree/{domain}.md"))
    elif domain == "reasoning":
        new_types = ['Critical Thinking', 'Theoretical Reasoning', 'Philosophical Reasoning', 'Critical Reasoning',
                     'Design Evaluation', 'Practical Problem Solving', 'Symbolic Reasoning',
                     'Causal Reasoning', 'Uniqueness Evaluation', 'Abstract Exploration', 'Classification Reasoning',
                     'Basic Counting Reasoning', 'Analogical Reasoning', 'Evaluation and Feedback',
                     'Comparative Analysis',
                     'Bayesian Reasoning', 'Conceptual Reasoning', 'Situational Analysis', 'Itinerary Decision Making',
                     'Explanatory Reasoning', 'Hypothetical Reasoning', 'Organizational Reasoning',
                     'Creative Biology', 'Null Value', 'Comparative Reasoning', 'Conceptual Understanding',
                     'Psychological Reasoning', 'Speculative Reasoning', 'Decision Support', 'Puzzle Solving',
                     'Conceptual Explanation', 'Problem Solving', 'Argument Evaluation', 'Analytical Reasoning',
                     'Deductive Reasoning', 'Ethical Evaluation', 'Hypothetical Thinking',
                     'Creative Experiment', 'Simple Counting', 'Relational Decision Making', 'Puzzle Design',
                     'Moral Reasoning', 'Social Situational Analysis', 'Strategic Planning',
                     'Analytical Thinking', 'Conceptual Analysis', 'Abstract Problem Solving', 'Text Analysis',
                     'Spatial Reasoning', 'Logical Reasoning', 'Conceptual Thinking',
                     'Decision Making', 'Creative Problem Solving', 'Personal Development Guidance',
                     'Emotional Reasoning', 'Conceptual Exploration', 'Legal Negotiation', 'Basic Counting Reasoning',
                     'Interpersonal Dynamics', 'Ethical Reasoning', 'Fashion Terminology', 'Metaphorical Reasoning',
                     'Creative Reasoning', 'Strategic Reasoning Presidente', 'Abstract Reasoning']
        init_cate_tree = {
            "Reasoning Methods": {
                "Logical Reasoning": {
                    "Deductive Reasoning": {},
                    "Inductive Reasoning": {},
                    "Symbolic Reasoning": {},
                    "Basic Counting Reasoning": {},
                },
                "Causal Reasoning": {
                    "Direct Causal Chain": {},
                    "Multi-factor Attribution": {},
                    "Bayesian Reasoning": {},
                },
                "Analogical Reasoning": {
                    "Structural Mapping": {},
                    "Cross-domain Analogy": {},
                    "Metaphorical Reasoning": {},
                },
                "Spatial Reasoning": {
                    "Geometric Relationships": {},
                    "Topological Relationships": {},
                },
                "Speculative Reasoning": {},
                "Classification Reasoning": {},
            },
            "Application Domains": {
                "Ethical Reasoning": {},
                "Legal Negotiation": {},
                "Mathematical Reasoning": {},
                "Philosophical Reasoning": {},
                "Biological Reasoning": {},
                "Psychological Reasoning": {},
                "Strategic Planning": {},
                "Social Reasoning": {},
                "Organizational Reasoning": {},
            },
            "Thinking Modes": {
                "Analytical": {
                    "System Deconstruction": {},
                    "Pattern Recognition": {},
                    "Text Analysis": {},
                },
                "Creative": {
                    "Divergent Association": {},
                    "Concept Reorganization": {},
                    "Abstract Exploration": {},
                },
                "Critical": {
                    "Hypothesis Challenge": {},
                    "Evidence Evaluation": {},
                },
                "Strategic": {
                    "Resource Optimization": {},
                    "Risk Assessment": {},
                },
            },
            "Task Types": {
                "Problem Solving": {},
                "Puzzle Solving": {},
                "Decision Making": {},
                "Argument Evaluation": {},
                "Conceptual Understanding and Analysis": {},
                "Evaluation and Feedback": {},
                "Uniqueness Evaluation": {},
                "Design Evaluation": {},
                "Situational Analysis": {},
                "Theoretical Reasoning": {},
            },
        }
        output_save_path = "reasoning_cata_tree.jsonl"
        base_prompt = utils.read_prompt("prompts/node_insertion.md").replace("{init_tree}", utils.read_prompt(
            f"init_tree/{domain}.md"))
    elif domain == "writing":
        new_types = ['Story Review', 'Content Creation', 'Summarization and Compression', 'Romantic Literature',
                     'Stylized Enhancement', 'Marketing Copy Refinement', 'Complaint Letter Creation',
                     'Microfiction Creation', 'Semantic Analysis', 'Text Expansion', 'Literary Naming',
                     'Art Critique Dialogue', 'Artistic Writing', 'Transformative Writing',
                     'Erotic Fiction Synopsis Creation', 'Critical Review', 'Satirical Analysis', 'Rap Translation',
                     'Philosophical and Analytical Writing', 'Parody Analysis',
                     'Creative Writing', 'Multilingual Communication', 'Personal Writing', 'Spelling',
                     'Fashion Prompt Creation', 'Opinion-Based Rhetoric', 'Grammar-Focused Writing',
                     'Definition Writing', 'Marketing Writing', 'Informative Summarization', 'Legal/Technical Writing',
                     'Sentence Writing', 'Title Design', 'Translation Review',
                     'Summary Writing', 'Opinion Review', 'Science Fiction', 'Language Education',
                     'Recommendation Letter', 'Structured Content Development', 'Prompt Creation and Optimization',
                     'Story Development', 'Grammar and Language Rules', 'Instruction Optimization',
                     'Historical Rewriting', 'Formal Submission Creation', 'Institutional Summarization',
                     'Fact-Based Technical Description', 'Language Assessment', 'Philosophical Summarization',
                     'Professional Title Creation', 'Creative Exploration', 'Dining or Restaurant Context',
                     'Summarization and Synthesis', 'Promotion', 'Philosophical Review', 'Creative Content Development',
                     'Media Review', 'Narrative Analysis Discussion', 'Translation and Stylized Enhancement',
                     'Article Review Creation', 'Informative Article Writing',
                     'Content Building and Generation for Academic Chapters', 'Translation and Refinement',
                     'Grammar Analysis', 'Text Extraction',
                     'Persuasive Writing', 'Creative Information Delivery', 'Custom: Unit Conversion',
                     'Information Retrieval', 'Article Introduction', 'Content Refinement', 'Query Creation',
                     'Mystery', 'Scene Creation', 'Fact Recall', 'Thesis Writing', 'Illustration Prompt Refinement',
                     'List-Based Writing', 'True Crime Podcast Script Creation',
                     'Content Conceptualization', 'Proverbial Expression', 'Professional Application Writing',
                     'Historical Presentation Writing', 'Naming/Branding', 'Lyrics', 'Situational Analysis',
                     'Classification Refinement', 'Literary Planning and Analysis', 'General Writing',
                     'Formal Communication', 'Greentext Writing', 'Social Media Interaction',
                     'Descriptive Prompt Creation', 'Response Creation', 'Culinary Writing', 'Vocabulary Enhancement',
                     'Thematic Creative Conceptualization', 'Meta-Writing',
                     'Pattern-Based Vocabulary Matching', 'Content Revision', 'Language Usage', 'Citation Recognition',
                     'Political Commentary', 'Content Retrieval', 'Instructional Prompt Creation',
                     'Retrospective Article Analysis', 'Linguistics', 'Literary Writing', 'Vocabulary Practice',
                     'Language Editing', 'Argument Evaluation', 'Prompt Engineering/Prompt Creation',
                     'Roasting', 'Style Editing', 'Forensic Writing', 'Explanatory Definition Creation',
                     'Document Formatting', 'Structured Text Analysis', 'Interpersonal Communication',
                     'Poetry Lyrics Translation', 'Selective Vocabulary Usage', 'Language Comprehension',
                     'Text Editing', 'Username Generation', 'Translation and Style Enhancement',
                     'Interview Writing', 'Formulating User Stories', 'Greentext Story Creation', 'Q&A',
                     'Pronunciation', 'Adaptation', 'Copywriting', 'Political Commentary Writing',
                     'Immigration Application Review', 'Philosophical Exploration', 'Text Structuring', 'Sitcom',
                     'Translation and Linguistics', 'Concept Exploration', 'Lyrics Adaptation',
                     'Character Writing', 'Prompt Optimization', 'Tone Adjustment', 'Speech Writing',
                     'IELTS Speaking Practice', 'Cultural Description', 'Video Analysis and Summarization',
                     'Lesson Planning', 'Professional Writing', 'Discussion Facilitation', 'Formal Explanation',
                     'Technical Document Summarization', 'Philosophical Writing', 'Variant Generation',
                     'Content Synthesis',
                     'Summary Generation', 'Branding and Marketing', 'IELTS Preparation', 'Publication and Adaptation',
                     'Phonetics and Spelling', 'Horror Story Creation',
                     'Nonsense Text Creation', 'Transcription Analysis', 'Letter Counting', 'Text Generation',
                     'Research Support', 'Prompt Writing', 'Professional Correspondence',
                     'Artistic Prompt Creation', 'Creative Interpretation', 'Text Optimization for Art',
                     'Theoretical Rewriting', 'Digital Content Creation', 'Encyclopedic Writing',
                     'Program Title Creation', 'Classification', 'Transliteration and Historical Linguistics',
                     'Format/Style Compliance', 'Branding/Naming', 'Cliché Listing',
                     'Humorous Writing', 'Professional Translation', 'Simplification',
                     'Simplification for Accessibility', 'Instructional Descriptive Writing', 'Art Prompt Creation',
                     'Anime Episode Creation',
                     'Adult-Themed Narrative', 'Literary Summarization', 'Problem Solving',
                     'Fill-in-the-Blank Exercises', 'Creative Description of Artistic Effects', 'Situational Writing',
                     'Philosophical Argumentation',
                     'Markdown Rendering', 'Language Comparison', 'Article Summarization',
                     'Fictional Legal Analysis Paper', 'Tone Analysis', 'Orthographic Conversion',
                     'Sentence Reorganization', 'Structured Data Translation', 'Writing Ethics',
                     'Language Standardization Development', 'Grammar and Linguistics', 'Text Translation and Editing',
                     'Music Video Script Creation', 'Language Correctness', 'Sentence Rewriting',
                     'Language and Grammar', 'Visual Storytelling', 'Personal Statement Summarization',
                     'Creative Link Creation', 'Political Statement Creation', 'Technical Refinement',
                     'Simulated Content Building', 'Text Standardization', 'Hierarchical Design', 'Prompt Integration',
                     'Vocabulary Analysis', 'Immigration Legal Writing', 'Professional Resume Creation',
                     'Songwriting Prompt Creation', 'Content Restructuring', 'Design Description Writing',
                     'Creative Format Development', 'Academic Project Conceptualization', 'International Commentary',
                     'Nonsense Text Generation', 'Constrained Creative Writing', 'Fantasy Literature Creation',
                     'Translation and Sentence Writing', 'Concept Explanation', 'Grammar and Vocabulary Examples',
                     'Political Writing', 'Creative Language', 'Style Transformation', 'Item Description',
                     'Summarizing Culturally Relevant Content', 'Mnemonic Creation', 'Vocabulary Usage',
                     'Text Analysis and Interpretation', 'Translation into Daoist Style', 'Conceptual Explanation',
                     'Tone Interpretation', 'Nickname Creation', 'Content Classification', 'Literature Review',
                     'Grammar and Language Analysis', 'Medical Technical Writing', 'Language Correction',
                     'HTML Assembly', 'Clarity Enhancement', 'Situational Creation', 'Scholarship Question Drafting',
                     'Resume Content', 'Literary Interpretation', 'Insurance Scenario Drafting',
                     'Toxic Language Generation', 'Fictional Constitution Creation', 'Content Editing and Improvement',
                     'Character Analysis', 'Resume Creation', 'Instructional Text',
                     'Translation and Adaptation', 'Specific Language Writing', 'SEO Writing', 'Word Puzzle Solving',
                     'Structured Clustering Generation', 'Social Media Content',
                     'Phonetics and Vocabulary', 'Chart Representation', 'EB2 NIW Petition Title Creation',
                     'Content Structuring and Enhancement', 'Outline Creation',
                     'Prompt Creation for Text-to-Video', 'Vocabulary and Word Usage', 'Review Optimization',
                     'Translation and Text Polishing', 'Online Argumentative Writing',
                     'Sentence Completion', 'List Creation', 'Prompt Example Creation', 'Morphology and Etymology',
                     'Text Refinement', 'Lyrics Creation', 'Instruction Clarification',
                     'Tutorial Creation with Jargon', 'Linguistics/Grammar', 'Empathetic Communication',
                     'Translation and Proofreading', 'Historical Writing', 'Fictional Story Creation',
                     'Vocabulary Precision', 'MBA Application Story Creation', 'Philosophical and Religious Commentary',
                     'Tone Analysis in Information Delivery', 'Formal Writing', 'Content Marketing',
                     'Academic Writing - Assessment Practices', 'Vocabulary Generation', 'Financial Document Creation',
                     'Product Description Editing', 'Naming Creation', 'Situation Generation',
                     'Medical Proofreading', 'Puzzle Creation', 'Grammar and Clarity Adjustment',
                     'Tone and Neutrality Editing', 'Stylized Sentence Creation', 'Hypnotic Writing',
                     'Metaphor Explanation', 'Creative Visuals and Style', 'Language Practice',
                     'Game Concept Development', 'Lyrics Interpretation', 'Guide Creation',
                     'Variant Generation and Elaboration', 'Tone and Style Adjustment', 'Philosophical Reflection',
                     'Note-Taking Technique Creation', 'Personal Profile Creation', 'Vocabulary Recognition',
                     'Clarity Rewriting', 'Translation and Content Adaptation', 'List Generation',
                     'Rap/Lyrics Analysis', 'Query Generation', 'Phrase Translation', 'Scriptwriting',
                     'Sports News', 'Claim Evaluation', 'Vocabulary Recall and Listing', 'Creative Prompt Creation',
                     'Professional Expansion Email Writing', 'Grammar and Semantic Analysis',
                     'Compliance Discussion', 'Translation and Sentence Enhancement', 'Grammar and Style Editing',
                     'Legal Translation Analysis', 'Naming and Branding', 'Legal Writing Review',
                     'Professional Email Communication', 'Ethics and Technology', 'Design Description',
                     'Fictional Instructional Writing', 'Video Game Translation', 'Text Paraphrasing',
                     'Product Categorization Clustering', 'Text Summarization', 'Grammar Exercises',
                     'Translation Analysis', 'Sentence Generation', 'Vocabulary Sentence Creation',
                     'Character Development', 'Literature',
                     'Personal Narrative', 'Event Structuring', 'Strategic Prompt Design', 'Sentence Revision',
                     'Evaluation and Feedback', 'Music Analysis',
                     'AI Safety Prompt Creation', 'Transliteration Analysis', 'Metaphysical Interpretation',
                     'Affirmative Writing', 'Language and Vocabulary Development', 'Film Review',
                     'Sentence Transformation',
                     'Text Comparison Analysis', 'Historical Dialogue Analysis', 'Language Explanation',
                     'Text Suggestions', 'Brand Writing', 'Citation Formatting', 'Sports Commentary',
                     'Information Summarization', 'Instructional Writing', 'Hypnotic Induction',
                     'Tone and Style Decision', 'Biographical Story Creation', 'Summarization and Translation',
                     'Discussion Response Creation', 'Erotic Literature Creation', 'Example Sentence Generation',
                     'Fan Fiction Creation', 'ASCII Art', 'Conversational Writing', 'Language Design',
                     'Journalism', 'Stream of Consciousness', 'Personal Branding', 'Online Interaction',
                     'Regulatory Writing', 'Literary Analysis (Erotic Literature Representation)',
                     'Technical Prompt Refinement',
                     'Crossword Clue Creation', 'Analytical Content Processing', 'Literary Parody Creation',
                     'Persuasive Speech Instruction', 'Narrative Summarization', 'Script Transformation',
                     'Survey Question Creation', 'Grammar-Based Example Sentence Generation', 'Language Adaptation',
                     'Historical Narrative', 'Social Communication', 'Product Review Writing',
                     'Quiz Show and Video Script Creation', 'Formatting and Structuring', 'Executive Summary',
                     'Multimedia Prompt Generation', 'Language Translation',
                     'Film Script Creation', 'Prompt Design for AI Art Creation',
                     'Character Analysis and Narrative Speculation', 'Language Style',
                     'Visual Storytelling and Prompt Creation', 'Transcription Rewriting', 'Grant Application Writing',
                     'Tone Adjustment and Rewriting', 'Dialogue Refinement', 'Text Interpretation',
                     'Quiz Show Design', 'Collocation Generation', 'Science Fiction Writing', 'Report Analysis',
                     'Character Creation', 'Stylized Rewriting', 'Product Marketing',
                     'Prompt Organization', 'Game Design', 'Medical Text Proofreading', 'Tag Review Process',
                     'Grammar-Focused Sentences', 'Language Analysis and Translation',
                     'Academic and Creative Fusion', 'Template Design', 'Sentence Similarity Check', 'Prompt Design',
                     'Content Expansion', 'Sentence Expansion', 'Response Writing Feedback',
                     'World-Building and Background Analysis', 'Deceptive Writing', 'Program Refactoring',
                     'Curriculum Development', 'Descriptive Content Generation', 'Contract/Agreement Drafting',
                     'Speech Content', 'Language Structuring', 'Literary Analysis', 'Professional Communication',
                     'Grammar and Semantics', 'Educational Prompt Creation', 'Writing Feedback',
                     'News Writing', 'Medical Case Report', 'Clickbait Title Creation', 'Structured Content Creation',
                     'Writing Process', 'Meaning Analysis',
                     'Petition Cover Review', 'Fan Fiction', 'Text Transformation', 'Recommendation Writing',
                     'Story Analysis', 'Grammar and Vocabulary Generation', 'Health-Themed Writing',
                     'Email Writing', 'Character Dialogue Adaptation', 'Educational Writing', 'Unit Conversion Editing',
                     'Ideological Commentary', 'Music Review',
                     'Comparative Writing', 'Sentiment Analysis', 'Sentence Structure Analysis', 'Text Analysis',
                     'Language Annotation', 'Technical Content Refinement', 'Prompt Rewriting',
                     'Language Style and Structure', 'Word Count Analysis', 'AI Prompt Creation', 'List Compilation',
                     'Storytelling', 'Professional Document Creation', 'Web Content Summarization',
                     'Title and Tag Creation', 'Structured Summarization', 'Terminology Refinement',
                     'Sentence Correction', 'Biography Creation', 'Creative Naming', 'Letter Writing',
                     'Marketing and Branding', 'Language Learning Support', 'Grammar and Style', 'Consumer Review',
                     'Cultural Analysis', 'Text Decoding', 'Creative Prompt Creation',
                     'Spelling Check', 'Art Description Creation', 'Insurance Documentation',
                     'Personal Development Planning', 'Music Creation', 'Legal/Professional Writing',
                     'Promotional and Persuasive Writing', 'Meta-Writing Challenge',
                     'Content Rewriting and Translation', 'Literary Text Translation',
                     'Text Comprehension and Translation',
                     'Spiritual Writing', 'Professional Email', 'Metric Unit Conversion', 'Slogan Writing',
                     'Conceptual Translation', 'System Prompt Design', 'Information Rewriting',
                     'Subtitle Writing', 'Language and Translation', 'AI Video Generation Prompt Creation',
                     'Custom Task: Metric Unit Conversion', 'Language and Expression',
                     'Film Review', 'Policy-Oriented Writing', 'Vocabulary and Language', 'Citation Integration',
                     'Greeting Card Writing', 'Rulebook Editing', 'Research', 'Story Summarization',
                     'Title Generation', 'Translation and Text Editing', 'Character Creation', 'Prompt for AI Creation',
                     'Opinion-Based Writing', 'Vocabulary List',
                     'Sentence Revision', 'Logo Creation', 'Language Mechanics', 'Word/Vocabulary Selection',
                     'Image Prompt Creation', 'Concept Analysis', 'Prompt Organization and Refinement',
                     'Instruction Creation', 'Hard Science Fiction Narrative', 'Jokes', 'APA Formatting',
                     'Marketing/Promotional Content', 'Application Support', 'Adventure Writing',
                     'Data Consistency and Editing', 'Customer Communication', 'Query Analysis and Generation',
                     'Web Content Creation', 'Editing and Review', 'Financial Writing',
                     'Contest Rule Creation', 'Book Summarization', 'SCP Writing', 'Social Media Script Creation',
                     'Technical Writing (Physics)', 'Language and Vocabulary Selection',
                     'Information Evaluation', 'Narrative Writing', 'Legal Writing', 'Grammar and Rewriting',
                     'Text Summarization and Organization', 'Character Monologue', 'Character Design',
                     'AI-Generated Art Prompt', 'Naming Assistance', 'Immigration Application Writing',
                     'Alias Creation', 'Language Refinement', 'Structured Response Writing',
                     'Sentence Polishing', 'Plot Development', 'Policy Communication', 'Journal Writing',
                     'Summary Creation', 'Health Writing', 'Personal Communication Enhancement',
                     'Personal and Creative Writing', 'Fictional Declaration', 'Creative Conceptualization',
                     'Philosophical Reflection', 'Speech Writing', 'Content Development', 'Romanization',
                     'Vocabulary Formatting', 'Language Learning', 'Text Processing',
                     'Note Formatting and Tone Stylization', 'Occult Analysis', 'Information Improvement',
                     'Telemarketing Script Creation', 'Grammar and Usage', 'Naming and Abbreviation Creation',
                     'AI Art Prompt', 'Media Adaptation', 'Religious Studies Prompt Creation',
                     'Image Description', 'Personal Statement Creation', 'Creative Description',
                     'SCP/Fictional Story Creation', 'Viral Content Creation', 'Marketing',
                     'Content Evaluation', 'Fictional Dialogue Analysis', 'Emoji Enhancement',
                     'Philosophical Essay Creation', 'Concept Description', 'Image Prompt Enhancement',
                     'System Prompt Creation', 'Etymology Explanation', 'Terminology Analysis', 'Contest Writing',
                     'Language and Diction', 'Vocabulary Recommendation', 'ASCII Art Creation',
                     'Satire', 'Symbolic Interpretation', 'Professional Writing (EB2 NIW Cover Letter)',
                     'Policy and Sustainability Writing', 'Research and Summarization',
                     'Technical Milestone Documentation', 'Cyberpunk Style Creation', 'Grammar and Style Enhancement',
                     'Template Creation', 'Quote Analysis', 'Proposal Creation',
                     'Design Prompt Writing', 'Literary Translation and Analysis', 'Personal Communication Writing',
                     'Visual Content Creation', 'World Building', 'Word Selection',
                     'Grammar and Clarity Enhancement', 'Concept Elucidation', 'Online Narrative', 'Romantic Fiction',
                     'Content Adjustment', 'Sentence Structure',
                     'Text-to-Video Prompt Creation', 'Phrase Refinement', 'Vocabulary Listing', 'Comparative Analysis',
                     'Grammar and Punctuation', 'Descriptive Art Prompt Writing',
                     'Grammar Usage', 'Legal/Professional Petition Writing', 'Reflective Writing',
                     'Online Review Generation', 'Paraphrasing', 'Philosophical Literature',
                     'Idioms and Clichés', 'Historical Fiction', 'Personal Development Writing', 'Art Description',
                     'Note-Taking', 'Lexicography Creation', 'Instruction Compliance',
                     'Metaphorical Expression', 'Narrative Voice Selection', 'Workflow Drafting',
                     'Language/Style Analysis', 'Prompt Engineering', 'Vocabulary Manipulation',
                     'Language Quality Check', 'Idioms and Expressions', 'Travel Planning', 'Workshop Prompt Creation',
                     'Vocabulary Selection Enhancement', 'Romantic Song Creation',
                     'Branding and Naming', 'Executive Synthesis and Creative Report Writing',
                     'Content Expansion and Translation', 'Sentence Analysis',
                     'Prompt Creation Tailored for Text-to-Image Models', 'Grammar and Sentence Correction',
                     'Proposal Writing', 'Lyrics Translation', 'Reddit-Style Story Creation',
                     'Expository Writing', 'Product Description and Creative List Generation',
                     'Phonetics and Stress Patterns', 'Sentimental Advice Writing',
                     'Tone Adjustment for Business Communication',
                     'Philosophical Inquiry', 'Scholarship Application', 'Business Communication',
                     'Translation/Rewriting', 'Language Exercises and Vocabulary Derivation',
                     'Clustering-Based Content Creation',
                     'SEO', 'Advertising Script', 'Analytical Comprehension', 'Art Critique and Analysis',
                     'Suspense Writing', 'Technical Translation',
                     'Translation Metadata Writing', 'Curation', 'Nuanced Explanation', 'Document Refinement',
                     'Alternate History', 'Game Clue Creation', 'Informal Style Transformation',
                     'Game Translation', 'Sentence Creation', 'Translation Tasks', 'Horror', 'Branding and Copywriting',
                     'Project Documentation', 'News Commentary', 'Personal Messaging',
                     'Recipe Writing', 'Tutorial Creation', 'Prompt Development', 'Definition Creation',
                     'Meme Creation', 'Survey Design', 'Financial Explanation',
                     'Prompt Optimization for AI Music Creation', 'Custom Transformation', 'Translation Evaluation',
                     'Script Presentation', 'Stylized Analysis', 'Dramatic Script Creation',
                     'Language Experimentation', 'Creative Game Design', 'Translation and Content Refinement',
                     'Vocabulary Assistance', 'Decision Support Writing',
                     'Erotic Literature Creation with Compelling Elements', 'Creative AI Prompt Creation',
                     'Informal Tone Translation', 'Fantasy', 'Educational Assessment Design',
                     'Personal Journal', 'Report Creation', 'Quote Collection', 'Review Writing', 'Content Management',
                     'Literal Translation', 'Fake News Creation', 'Idiom and Phrase Analysis',
                     'Grammar', 'News Summarization', 'Language Transformation', 'Script Creation', 'Lyrics Analysis',
                     'Video Review and Summarization', 'Song Creation', 'Vocabulary and Grammar',
                     'Social Media Content Creation', 'Grammar and Sentence Reorganization', 'Grammar Enhancement',
                     'Context Assessment', 'Theme Interpretation', 'Idiomatic Expression', 'Editing',
                     'Political Article Summarization', 'Shonen Battle Design for TTRPG Story Creation', 'Naming',
                     'Content Revision for Professional Guides',
                     'Prompt Creation for Creative Descriptions', 'Advertising Story Creation', 'Sentence Refinement',
                     'Technical Translation and Editing', 'Speculative Fiction with Historical Analysis',
                     'Communication', 'Literary Knowledge Query', 'Syntactic Analysis', 'Advertising',
                     'Word Choice and Tone', 'Language Simplification', 'Medical Translation', 'Technical Explanation',
                     'Satirical Script Creation', 'Content Analysis', 'Speech Formatting',
                     'Vocabulary Structure Exploration', 'Science Fiction Story Creation', 'Informative Writing',
                     'Language Translation and Definition', 'Grammar and Syntax Analysis', 'Conceptual Analysis',
                     'Stylized Experimentation', 'Branding and Marketing Writing', 'Biotechnology Writing',
                     'Writing Themes', 'Email Communication', 'Concept Comprehension', 'Nu-Metal Song Creation',
                     'Task-Specific Formatting', 'Vocabulary Retrieval',
                     'Opinion-Based Analysis', 'Prompt Optimization and Standard Development',
                     'Quiz Show Format Design', 'Astrology Content Creation',
                     'SEO Content Creation', 'Daily Workflow Design', 'Sentence Comprehension',
                     'Language Fluency Enhancement', 'Concept Naming', 'Promotional Writing',
                     'Theoretical Exploration', 'Narrative Theory', 'Formatting', 'Expansion',
                     'Symbolic Story Creation and Visualization', 'Personal Communication Editing',
                     'Formal Letter Writing',
                     'Structured Documentation for Clinical Standards', 'Comedy Writing', 'Casual Writing',
                     'Opinion Writing', 'Fact-Checking', 'Document Revision', 'Clustering Creation',
                     'Predictive Writing', 'Humor Analysis', 'Historical Analysis', 'Conceptual Q&A',
                     'Language Translation and Enhancement', 'Critical Analysis', 'Rhetoric',
                     'Article Review', 'Language and Cultural Explanation', 'Prompt Creation with Flowchart Logic',
                     'Question Creation', 'Formal Legal Writing', 'Concise Communication',
                     'Lyrics Translation and Adaptation', 'Professional Tone Adjustment', 'Prompt Refinement',
                     'Tone and Style Guidance', 'Sentence Construction', 'Technical Adjustment',
                     'Persuasive Explanation', 'Plot Structuring', 'Naming or Branding', 'Instruction Creation',
                     'Speech Template', 'Scripted Story Creation', 'Argument Development',
                     'Question Generation', 'Word Choice Analysis', 'Concept Explanation',
                     'Task Documentation Creation', 'Figurative Language', 'Instructional Framework Creation',
                     'Web Link Creation', 'Form Content Creation', 'Analytical Essay Creation', 'Personal Reflection',
                     'Marketing and Localization', 'Technical Writing Enhancement',
                     'Technical Writing', 'Text Analysis and Translation', 'Horoscope Writing', 'Opinion-Based Ranking',
                     'Text Validation', 'Creative Descriptive Writing',
                     'Factual Descriptive Writing', 'Translation', 'Scientific Text', 'Branding and Design',
                     'Grammar Correction', 'Resume Writing', 'Vision Creation',
                     'Explaining Translation Decisions', 'Theme Identification', 'Historical Linguistics Writing',
                     'Vocabulary Description', 'Writing Assessment', 'Academic and Business Reports',
                     'Event-Themed Content Variant Creation', 'Thematic Descriptive Content Creation',
                     'Precise Text Reproduction', 'Polishing', 'Document Editing', 'Argumentation',
                     'Media Compliance Writing', 'Product Description', 'Business Idea Generation',
                     'Language Creativity', 'Data Generation for Content Review', 'Language and Cultural Usage',
                     'Grammar and Spelling', 'Philosophical Essay Creation', 'Text Correction', 'Application Writing',
                     'Creative Home Design Story Creation',
                     'Human-Like Response Creation', 'Assessment Writing', 'Experimental Prose', 'Biography Writing',
                     'Prompt Improvement', 'Text Completion', 'Challenge Creation',
                     'Instructional Explanation', 'Vocabulary Explanation', 'Language Flexibility',
                     'Professional Interview Preparation', 'Game Localization and Translation',
                     'Language and Grammar Education',
                     'Blog Writing', 'Novel Analysis', 'Custom Adjustment', 'Educational Content on Certification',
                     'Language Trivia', 'Language Expression', 'Information Structuring',
                     'Character Matching', 'Vocabulary', 'Demotivational Poster Concept Creation', 'Article Polishing',
                     'Expressive Writing', 'Character Ability Conceptualization', 'Content Editing',
                     'Diary', 'Grammar Explanation', 'Grammar Critique', 'Religious Text Summarization',
                     'Markdown Output Display', 'Sentence Interpretation', 'Advertising Copywriting',
                     'Game Design Writing', 'Translation and Interpretation', 'Content Rewriting',
                     'Language and Phonetics', 'Citation', 'Stylized Writing', 'Product Description Refinement',
                     'Language-Related Tasks', 'Creation', 'Reality Adjustment', 'Language Processing',
                     'Logical Inference', 'Grammar and Spelling Correction', 'Paraphrasing and Language Reorganization',
                     'Event Creativity', 'Interior Design Description', 'Daily Planning', 'Creative Analysis',
                     'Language and Cultural Nuances', 'Content Organization', 'Language Games',
                     'Story Enhancement', 'Language Analysis', 'Grammar and Paraphrasing', 'Vocabulary Creation',
                     'Vocabulary List Generation', 'Translation and Style Editing',
                     'Translation and Error Correction', 'Business Insights', 'Manifesto Creation', 'Analogy Creation',
                     'Prompt and Summary Creation', 'Bias Analysis',
                     'Grammar and Vocabulary Enhancement', 'Card Legend Creation', 'Curriculum Design',
                     'Author Analysis', 'Recommendation', 'Language and Vocabulary Enhancement', 'Grammar Check',
                     'Instruction Creation for Musical Lyric Style', 'User Stories', 'Grammar and Language Precision',
                     'Social Media Writing', 'Content Localization',
                     'Game Narrative Development', 'Vocabulary and Definition Selection', 'Content Exploration',
                     'Vocabulary Exploration', 'Design Writing', 'Erotic Fiction', 'Content Writing',
                     'General Text Refinement', 'Romantic Writing', 'Content Integration', 'Project Review',
                     'Question Simplification', 'Abbreviation Creation', 'Scientific Writing',
                     'Vocabulary Matching', 'Advertising Copy', 'Grammar and Vocabulary', 'Title Evaluation',
                     'AI Art Scene Description', 'Metric Evaluation', 'Environmental Writing',
                     'Coherent Fragment Generation', 'Isekai Comedy', 'Formalization',
                     'Grammar and Vocabulary Derivation', 'Entity Extraction', 'System Prompt Improvement',
                     'Inspirational Writing',
                     'Technical Explanation (Egyptian Arabic)', 'Code Snippet Integration', 'Analytical Writing',
                     'Interview Summarization', 'Vocabulary Accumulation', 'Humor Evaluation',
                     'Rhetorical Analysis', 'Structured Classification', 'Language Precision', 'Summarization',
                     'Casual Communication', 'Content Recall', 'Linguistics and Phonetics',
                     'Response Evaluation', 'Dark Humor Content Creation', 'System Prompt Refinement',
                     'Vocabulary Development', 'Explanatory Writing', 'News Brief Synthesis', 'Poetry',
                     'Branding and Naming Creation', 'Quote Creation', 'Annotation', 'Anki Flashcard Creation',
                     'Style Application', 'Informative Content Creation', 'Language Philosophy',
                     'Philosophical Interpretation', 'Sentence Meaning Analysis', 'Text Assessment',
                     'Text Manipulation', 'Genre Analysis', 'Marketing Content', 'Proposal Conceptualization',
                     'Note Writing',
                     'Translation and Interpretation', 'Technical Review', 'Personal Biography',
                     'Audience Advisory Creation', 'Editing for Diversity Enhancement', 'Self-Description Enhancement',
                     'Product Description Creation', 'Satirical Writing', 'Fantasy Sitcom', 'Data Adjustment',
                     'Prompt Enhancement', 'Prompt Creation and Structuring',
                     'Study Plan Creation', 'Fiction', 'Written Opening Assessment', 'Logical Reasoning',
                     'Descriptive Writing', 'Professional Planning', 'Text Formatting',
                     'Interpretation and Editing', 'Character-Centered Dialogue Writing',
                     'Translation and Language Correction', 'Quiz Creation', 'Language and Editing', 'Proofreading',
                     'Dating Profile Creation', 'Art Critique', 'Health and Wellness Writing', 'Informal Communication',
                     'Steampunk', 'Song Creation (Lyrics and Structure)',
                     'Interview Question Creation', 'Dialogue Facilitation', 'Historical Summarization', 'Game Writing',
                     'Instructional Content Creation', 'Media Content Creation',
                     'Data Prioritization', 'Sports Translation', 'Language Restriction',
                     'Translation and Entity Extraction', 'Content Simplification', 'Concept Summarization',
                     'Answer Rewriting',
                     'Adaptation Review', 'Financial Analysis Report Creation', 'Brainstorming',
                     'Speech Content Creation', 'Mnemonic Creation for Language Learning',
                     'Financial Audit Memo', 'Data Preparation', 'Research Summarization', 'Humorous Translation',
                     'Task Customization', 'Brainstorming Ideas', 'Fitness Content Creation',
                     'Language Proficiency Test Preparation', 'Concept Conceptualization', 'Language Interpretation',
                     'Structured Response', 'Branding', 'Prompt Creation for Text-to-Image',
                     'Social Messaging', 'Translation and Promotional Text', 'Creative Fragment Creation',
                     'Article Analysis', 'Dialogue Generation', 'Personal Preferences',
                     'Visual Prompt Creation', 'Translation and Contextual Fidelity', 'Sports Writing', 'Transcription',
                     'E-commerce Title Generation', 'Detail Expansion', 'Literary Fiction',
                     'Language Model Evaluation', 'Language Semantics', 'Daily Workflow Development',
                     'Abstract Text Classification', 'Speech Analysis', 'Critical Writing', 'Data Structuring',
                     'Bullet Point Generation for Technical Content', 'Unit Conversion', 'Art and Design Concepts',
                     'Artistic Description', 'Sports Narrative', 'Creative Concept Development',
                     'Text Checking', 'Text Simplification', 'Advertising Writing', 'Data Rewriting',
                     'Business Writing', 'Name Generation', 'Educational Content Creation', 'Evaluation',
                     'Prompt for Media Creation', 'Localization', 'Experimental Writing', 'Humor',
                     'Academic Adaptation', 'Literary Recommendation', 'Academic Curriculum Design',
                     'Rhetorical Expression', 'Reflective Journal Creation', 'Wine Description',
                     'Argumentative Writing', 'Language Phrasing', 'Character Creation',
                     'Email Writing Management', 'Financial/Business Writing', 'Author Inference',
                     'Content Summarization', 'Mind Mapping Creation', 'Political Fiction',
                     'Ornamental Writing', 'Personal Message Creation', 'Narrative Analysis',
                     'Grammar and Sentence Reconstruction', 'Social Critique', 'Health/Medical Writing',
                     'Editing and Revision', 'Philosophical Text Translation', 'Technical Creative Writing',
                     'Speculative Writing', 'Image Generation Prompt Creation', 'Situational Analysis and Ranking',
                     'Content Branding', 'Fictional Narrative', 'Travel Writing', 'Translation and Editing Enhancement',
                     'Assignment Evaluation', 'Experimental Creative Writing', 'Format Design',
                     'Quiz Question Creation', 'Language Creation', 'Critical Text Analysis', 'Script Presentation',
                     'Phrase Improvement', 'Visual Art Prompt Creation',
                     'Grammar and Translation', 'Opinion Expression', 'Medical Writing', 'Language Wordplay',
                     'Educational Content Creation', 'Obituary Writing', 'Language Enhancement',
                     'Twitter Content Summarization', 'Data Curation', 'Inference', 'Grammar Editing',
                     'Social Media Caption Creation', 'Grammar and Language Usage',
                     'Creative Problem Solving', 'Process Design', 'Rewriting', 'Text Reproduction',
                     'Question Refinement', 'Rap Lyrics Creation',
                     'E-commerce SEO', 'AI Prompt Creation for Text-to-Video', 'Instructional Design',
                     'Translation and Text Refinement', 'Tongue-Twister Format Jokes', 'Synonym Generation',
                     'Writing Analysis', 'Style Suggestions', 'Prompt Creation for Video', 'Literary Critique',
                     'Professional Content Assessment', 'Marketing Copy Creation',
                     'Melancholic Storytelling with Multimedia Impact', 'Encyclopedic Fan Fiction Creation',
                     'Dialogue Creation',
                     'Machine-Readable Image Description', 'Personal Communication', 'Joke Creation',
                     'Text Formatting for Narrative', 'Descriptive Design Writing', 'Literary Translation',
                     'Drama', 'Personal Narrative Translation', 'Academic Writing', 'Language Learning Materials',
                     'Pun Translation', 'Personality Design', 'Content Planning and Script Creation',
                     'Technical Documentation', 'Advertising Script Creation', 'Content Flow Enhancement',
                     'Phrase Rewriting', 'Meaning and Key Point Analysis', 'Humorous/Comedy Writing',
                     'Custom Query', 'Custom Metric Unit Conversion', 'Product Categorization', 'Author Identification',
                     'Educational Content', 'Marketing and Promotional Writing',
                     'Cultural Interpretation and Creative Context', 'Subconscious Writing', 'Content Structuring',
                     'Metaphor Recognition', 'Design Project Description', 'Social Media Formatting',
                     'Vocabulary Sentence Formation', 'Idiomatic Expression Translation',
                     'Petition Cover Letter Writing', 'Product Clustering', 'Choreography Writing',
                     'Descriptive Comparison',
                     'Predictive Text Writing', 'Hard Science Fiction Battle Analysis', 'Eulogy',
                     'Question Structuring', 'Professional Marketing Communication', 'Explanation',
                     'Personal Correspondence',
                     'Brand Naming Creation', 'Text Enhancement', 'Grammar and Language Exercises',
                     'Marketing and Product Description', 'Framework Decomposition', 'Grammar and Language',
                     'Structured Formatting', 'Workplace Writing', 'Prompt for Design Creation', 'Text Optimization',
                     'Tag Generation', 'Theoretical Reasoning', 'Video Description Creation',
                     'Wordplay', 'Vocabulary Generation', 'Creative Photography Description',
                     'Business Document Creation', 'Speculative Fiction', 'Language Query', 'Short Story Creation',
                     'Translation and Text Correction', 'Book Title Localization', 'Sentence Structuring',
                     'Naming Conventions', 'Decision Support', 'Travel and Leisure Writing',
                     'Product Content Writing', 'Idiom Creation', 'Media Summarization',
                     'Translation and Summarization', 'Document Transformation and Preparation', 'Response Rewriting',
                     'Style Adjustment',
                     'Translation and Logical Enhancement', 'Game Conceptualization', 'Sentence Clarity',
                     'Technical Translation and Language Refinement', 'Grammar and Language Refinement',
                     'Lifestyle Planning', 'Bioethics', 'Entertainment Writing', 'Opinion-Based List Creation',
                     'Writing Optimization', 'Dialect Translation',
                     'Transcription Editing', 'Game Localization', 'Scientific Communication',
                     'Memory-Based Content Creation', 'Cognitive Text Simulation', 'Media Analysis',
                     'Data Storytelling', 'Vocabulary Categorization', 'Consulting Writing', 'Vocabulary Refinement',
                     'Language Humor and Wordplay Analysis',
                     'Tone Adjustment and Clarity Enhancement', 'Literary Review Creation',
                     'Leadership Principles Creation', 'Career Planning', 'Transcription Summarization',
                     'Event Script Creation',
                     'Content Generation', 'Technical Writing Refinement and Translation',
                     'Philosophical Language Exploration', 'Prompt Creation', 'Business Writing',
                     'Music Profile Creation',
                     'Detailed Descriptive Writing', 'Video Prompt Creation', 'Constrained Writing',
                     'Translation and Editing', 'Title Creation', 'Science Fiction Speculative Writing',
                     'Document Structuring', 'Grammar and Syntax', 'Language and Vocabulary', 'AI Art Prompt Creation',
                     'Encyclopedic Writing with Stylized Features',
                     'Question Design', 'Therapeutic Question Creation', 'Brand Design Conceptualization', 'Analysis',
                     'Marketing Copy Writing', 'Occult Interpretation',
                     'Biomaterials Science Translation', 'Definition Analysis', 'Data-Driven Prompt Creation',
                     'Blockchain Adoption Strategy', 'Lyrics Retrieval',
                     'Creative Personal Narrative Writing', 'Text Revision', 'Technical Translation and Refinement',
                     'Persuasive Slogan Creation', 'Video Script Creation',
                     'Editing/Writing Review', 'Content Optimization', 'Game Design Documentation', 'Greeting Message']
        init_cate_tree = {
            "Creative Stages": {
                "Conceptualization Stage": {
                    "Brainstorming": {},
                    "Outline Construction": {},
                    "Character Development": {},
                    "World Building": {},
                    "Concept Analysis": {},
                    "Literature Review": {},
                    "Scenario Analysis": {},
                    "Material Collection": {}
                },
                "Writing Stage": {
                    "Draft Writing": {},
                    "Data Integration": {},
                    "Case Study": {},
                    "Dialogue Generation": {},
                    "Citation Integration": {},
                    "Content Generation": {},
                    "Unit Conversion": {},
                    "Example Generation": {},
                    "Argument Construction": {}
                },
                "Optimization Stage": {
                    "Grammar Check": {},
                    "Style Adjustment": {},
                    "Logic Validation": {},
                    "Content Structuring": {},
                    "Text Simplification": {},
                    "Content Rewriting": {},
                    "Polishing": {},
                    "Expansion": {},
                    "Multilingual Translation": {},
                    "Format Conversion": {}
                },
                "Post-processing Stage": {
                    "Text Summarization": {},
                    "Text Interpretation": {},
                    "Theme Identification": {},
                    "Evaluation and Feedback": {}
                }
            },
            "Writing Domains": {
                "Professional Writing": {
                    "Natural Sciences": {},
                    "Law": {},
                    "Medicine": {},
                    "Technology": {},
                    "Academic": {},
                    "Finance": {},
                    "Sports": {},
                    "Business": {},
                    "Philosophy": {},
                    "Politics": {},
                    "History": {},
                    "Music": {},
                    "Art": {},
                    "Psychology": {}
                },
                "Everyday Writing": {
                    "Society": {},
                    "Travel": {},
                    "Shopping": {},
                    "Food": {},
                    "Sports": {},
                    "Health": {},
                    "Gaming": {},
                    "Family": {},
                    "Pets": {},
                    "Teaching": {},
                    "Interpersonal Communication": {},
                    "Emotions": {},
                    "Exams": {},
                    "Entertainment": {}
                },
                "Creative Expression": {
                    "Science Fiction": {},
                    "Horror": {},
                    "Mythology": {},
                    "Film and Television": {},
                    "Comics": {}
                },
                "Literary Writing": {
                    "Scriptwriting": {},
                    "Drama": {},
                    "Prose": {},
                    "Poetry": {},
                    "Fiction": {}
                },
                "Functional Writing": {
                    "User Manuals": {},
                    "Teaching": {},
                    "Project Planning": {},
                    "Resume Writing": {},
                    "Speech Writing": {},
                    "Meeting Minutes": {},
                    "Argumentative Writing": {},
                    "Official Document Writing": {},
                    "Recommendation Letters": {}
                },
                "Media Writing": {
                    "News Reporting": {},
                    "Blog Posts": {},
                    "Web Content": {},
                    "Social Media": {},
                    "Video Scripts": {},
                    "Advertising and Marketing": {},
                    "Podcast Scripts": {}
                }
            },
            "Styles": {
                "Classicism": {},
                "Romanticism": {},
                "Realism": {},
                "Modernism": {},
                "Postmodernism": {},
                "Concise": {},
                "Rigorous": {},
                "Formal": {},
                "Serious": {},
                "Light-hearted": {},
                "Natural": {},
                "Humorous": {},
                "Satirical": {},
                "Exaggerated": {},
                "Plain": {},
                "Melancholic": {},
                "Tragic": {},
                "Comedic": {}
            }
        }
        output_save_path = "writing_cata_tree.jsonl"
        base_prompt = utils.read_prompt("prompts/node_insertion.md").replace("{init_tree}", utils.read_prompt(
            f"init_tree/{domain}.md"))
    else:
        print(f"The domain {domain} does not exist.")
        exit(0)

    # ===============================================================================================
    # Parameter processing
    output_save_path = os.path.join(output_path, output_save_path)

    # Delete completed items and read the current tree
    cur_cate_tree = copy.deepcopy(init_cate_tree)
    if os.path.exists(output_save_path):
        existing_items = utils.read_jsonl_file(output_save_path)
        for obj in existing_items:
            if "tree_after_adding_node" in obj:
                new_types.remove(obj["new_node"])
                cur_cate_tree = obj["tree_after_adding_node"]
    print("Remaining items to process:", len(new_types))

    # Iterate and process
    with open(output_save_path, 'a', encoding='utf-8') as f:
        for i in tqdm(range(len(new_types)), desc="Processing..."):
            # Add node to create a new tree
            new_type = new_types[i]
            find_node_llm_decision_partial = partial(find_node_llm_decision, base_url=base_url, max_retries=10,
                                                     api_key=api_key,
                                                     model=model, sample_num=sample_num,
                                                     generation_params=generation_params, file=f,
                                                     base_prompt=base_prompt)
            cur_cate_tree = add_node_to_tree(cur_cate_tree, new_type, find_node_llm_decision_partial)

            # Save log
            obj = {
                "new_node": new_type,
                "tree_after_adding_node": cur_cate_tree
            }
            f.write(json.dumps(obj, ensure_ascii=False) + '\n')
            f.flush()
