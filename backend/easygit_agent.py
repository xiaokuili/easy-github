# This is our processing. This is where GitDiagram makes the magic happen
# There is a lot of DETAIL we need to extract from the repository to produce detailed and accurate diagrams
# I will immediately put out there that I'm trying to reduce costs. Theoretically, I could, for like 5x better accuracy, include most file content as well which would make for perfect diagrams, but thats too many tokens for my wallet, and would probably greatly increase generation time. (maybe a paid feature?)

# THE PROCESS:

# imagine it like this:
# def prompt1(file_tree, readme) -> explanation of diagram
# def prompt2(explanation, file_tree) -> maps relevant directories and files to parts of diagram for interactivity
# def prompt3(explanation, map) -> Mermaid.js code

# Note: Originally prompt1 and prompt2 were combined - but I tested it, and turns out mapping relevant dirs and files in one prompt along with generating detailed and accurate diagrams was difficult for Claude 3.5 Sonnet. It lost detail in the explanation and dedicated more "effort" to the mappings, so this is now its own prompt.

# This is my first take at prompt engineering so if you have any ideas on optimizations please make an issue on the GitHub!

SYSTEM_FIRST_PROMPT = """
You are tasked with explaining to a principal software engineer how to draw the best and most accurate system design diagram / architecture of a given project. This explanation should be tailored to the specific project's purpose and structure. To accomplish this, you will be provided with two key pieces of information:

1. The complete and entire file tree of the project including all directory and file names, which will be enclosed in <file_tree> tags in the users message.

2. The README file of the project, which will be enclosed in <readme> tags in the users message.

Analyze these components carefully, as they will provide crucial information about the project's structure and purpose. Follow these steps to create an explanation for the principal software engineer:

1. Identify the project type and purpose:
   - Examine the file structure and README to determine if the project is a full-stack application, an open-source tool, a compiler, or another type of software imaginable.
   - Look for key indicators in the README, such as project description, features, or use cases.

2. Analyze the file structure:
   - Pay attention to top-level directories and their names (e.g., "frontend", "backend", "src", "lib", "tests").
   - Identify patterns in the directory structure that might indicate architectural choices (e.g., MVC pattern, microservices).
   - Note any configuration files, build scripts, or deployment-related files.

3. Examine the README for additional insights:
   - Look for sections describing the architecture, dependencies, or technical stack.
   - Check for any diagrams or explanations of the system's components.

4. Based on your analysis, explain how to create a system design diagram that accurately represents the project's architecture. Include the following points:

   a. Identify the main components of the system (e.g., frontend, backend, database, building, external services).
   b. Determine the relationships and interactions between these components.
   c. Highlight any important architectural patterns or design principles used in the project.
   d. Include relevant technologies, frameworks, or libraries that play a significant role in the system's architecture.

5. Provide guidelines for tailoring the diagram to the specific project type:
   - For a full-stack application, emphasize the separation between frontend and backend, database interactions, and any API layers.
   - For an open-source tool, focus on the core functionality, extensibility points, and how it integrates with other systems.
   - For a compiler or language-related project, highlight the different stages of compilation or interpretation, and any intermediate representations.

6. Instruct the principal software engineer to include the following elements in the diagram:
   - Clear labels for each component
   - Directional arrows to show data flow or dependencies
   - Color coding or shapes to distinguish between different types of components

7. NOTE: Emphasize the importance of being very detailed and capturing the essential architectural elements. Don't overthink it too much, simply separating the project into as many components as possible is best.

Present your explanation and instructions within <explanation> tags, ensuring that you tailor your advice to the specific project based on the provided file tree and README content.
"""

# - A legend explaining any symbols or abbreviations used
# ^ removed since it was making the diagrams very long

# just adding some clear separation between the prompts
# ************************************************************
# ************************************************************

SYSTEM_SECOND_PROMPT = """
You are tasked with mapping key components of a system design to their corresponding files and directories in a project's file structure. You will be provided with a detailed explanation of the system design/architecture and a file tree of the project.

First, carefully read the system design explanation which will be enclosed in <explanation> tags in the users message.

Then, examine the file tree of the project which will be enclosed in <file_tree> tags in the users message.

Your task is to analyze the system design explanation and identify key components, modules, or services mentioned. Then, try your best to map these components to what you believe could be their corresponding directories and files in the provided file tree.

Guidelines:
1. Focus on major components described in the system design.
2. Look for directories and files that clearly correspond to these components.
3. Include both directories and specific files when relevant.
4. If a component doesn't have a clear corresponding file or directory, simply dont include it in the map.

Now, provide your final answer in the following format:

<component_mapping>
1. [Component Name]: [File/Directory Path]
2. [Component Name]: [File/Directory Path]
[Continue for all identified components]
</component_mapping>

Remember to be as specific as possible in your mappings, only use what is given to you from the file tree, and to strictly follow the components mentioned in the explanation. 
"""

# ❌ BELOW IS A REMOVED SECTION FROM THE ABOVE PROMPT USED FOR CLAUDE 3.5 SONNET
# Before providing your final answer, use the <scratchpad> to think through your process:
# 1. List the key components identified in the system design.
# 2. For each component, brainstorm potential corresponding directories or files.
# 3. Verify your mappings by double-checking the file tree.

# <scratchpad>
# [Your thought process here]
# </scratchpad>

# just adding some clear separation between the prompts
# ************************************************************
# ************************************************************

SYSTEM_THIRD_PROMPT = """
You are a principal software engineer tasked with creating a system design diagram using Mermaid.js based on a detailed explanation. Your goal is to accurately represent the architecture and design of the project as described in the explanation.

The detailed explanation of the design will be enclosed in <explanation> tags in the users message.

Also, sourced from the explanation, as a bonus, a few of the identified components have been mapped to their paths in the project file tree, whether it is a directory or file which will be enclosed in <component_mapping> tags in the users message.

To create the Mermaid.js diagram:

1. Carefully read and analyze the provided design explanation.
2. Identify the main components, services, and their relationships within the system.
3. Determine the appropriate Mermaid.js diagram type to use (e.g., flowchart, sequence diagram, class diagram, architecture, etc.) based on the nature of the system described.
4. Create the Mermaid.js code to represent the design, ensuring that:
   a. All major components are included
   b. Relationships between components are clearly shown
   c. The diagram accurately reflects the architecture described in the explanation
   d. The layout is logical and easy to understand

Guidelines for diagram components and relationships:
- Use appropriate shapes for different types of components (e.g., rectangles for services, cylinders for databases, etc.)
- Use clear and concise labels for each component
- Show the direction of data flow or dependencies using arrows
- Group related components together if applicable
- Include any important notes or annotations mentioned in the explanation
- Just follow the explanation. It will have everything you need.

IMPORTANT!!: Please orient and draw the diagram as vertically as possible. You must avoid long horizontal lists of nodes and sections!

You must include click events for components of the diagram that have been specified in the provided <component_mapping>:
- Do not try to include the full url. This will be processed by another program afterwards. All you need to do is include the path.
- For example:
  - This is a correct click event: `click Example "app/example.js"`
  - This is an incorrect click event: `click Example "https://github.com/username/repo/blob/main/app/example.js"`
- Do this for as many components as specified in the component mapping, include directories and files.
  - If you believe the component contains files and is a directory, include the directory path.
  - If you believe the component references a specific file, include the file path.
- Make sure to include the full path to the directory or file exactly as specified in the component mapping.
- It is very important that you do this for as many files as possible. The more the better.

- IMPORTANT: THESE PATHS ARE FOR CLICK EVENTS ONLY, these paths should not be included in the diagram's node's names. Only for the click events. Paths should not be seen by the user.

Your output should be valid Mermaid.js code that can be rendered into a diagram.

Do not include an init declaration such as `%%{{init: {{'key':'etc'}}}}%%`. This is handled externally. Just return the diagram code.

Your response must strictly be just the Mermaid.js code, without any additional text or explanations.
No code fence or markdown ticks needed, simply return the Mermaid.js code.

Ensure that your diagram adheres strictly to the given explanation, without adding or omitting any significant components or relationships. 

For general direction, the provided example below is how you should structure your code:

```mermaid
flowchart TD 
    %% or graph TD, your choice

    %% Global entities
    A("Entity A"):::external
    %% more...

    %% Subgraphs and modules
    subgraph "Layer A"
        A1("Module A"):::example
        %% more modules...
        %% inner subgraphs if needed...
    end

    %% more subgraphs, modules, etc...

    %% Connections
    A -->|"relationship"| B
    %% and a lot more...

    %% Click Events
    click A1 "example/example.js"
    %% and a lot more...

    %% Styles
    classDef frontend %%...
    %% and a lot more...
```

EXTREMELY Important notes on syntax!!! (PAY ATTENTION TO THIS):
- Make sure to add colour to the diagram!!! This is extremely critical.
- In Mermaid.js syntax, we cannot include special characters for nodes without being inside quotes! For example: `EX[/api/process (Backend)]:::api` and `API -->|calls Process()| Backend` are two examples of syntax errors. They should be `EX["/api/process (Backend)"]:::api` and `API -->|"calls Process()"| Backend` respectively. Notice the quotes. This is extremely important. Make sure to include quotes for any string that contains special characters.
- In Mermaid.js syntax, you cannot apply a class style directly within a subgraph declaration. For example: `subgraph "Frontend Layer":::frontend` is a syntax error. However, you can apply them to nodes within the subgraph. For example: `Example["Example Node"]:::frontend` is valid, and `class Example1,Example2 frontend` is valid.
- In Mermaid.js syntax, there cannot be spaces in the relationship label names. For example: `A -->| "example relationship" | B` is a syntax error. It should be `A -->|"example relationship"| B` 
- In Mermaid.js syntax, you cannot give subgraphs an alias like nodes. For example: `subgraph A "Layer A"` is a syntax error. It should be `subgraph "Layer A"` 
"""

# LangChain 0.3 implementation
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_deepseek.chat_models import ChatDeepSeek
from dotenv import load_dotenv
import os 

load_dotenv()

class GitDiagramAgent:
    def __init__(self, api_key=os.getenv("DEEPSEEK_API_KEY"), model_name=os.getenv("BASE_MODEL_NAME"), api_base=os.getenv("DEEPSEEK_BASE_URL")):
        """
        Initialize the GitDiagram agent.
        
        Args:
            api_key (str, optional): Anthropic API key. Defaults to None.
            model_name (str, optional): Model to use. Defaults to "claude-3-5-sonnet-20240620".
        """
        print(api_key, model_name, api_base)
        self.model = ChatDeepSeek(
            api_key=api_key,
            api_base=api_base,
            model_name=model_name
        )
        
        # Initialize prompts
        self.explanation_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(SYSTEM_FIRST_PROMPT),
            HumanMessagePromptTemplate.from_template("Please analyze the following repository:\n\n<file_tree>\n{file_tree}\n</file_tree>\n\n<readme>\n{readme}\n</readme>")
        ])
        
        self.mapping_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(SYSTEM_SECOND_PROMPT),
            HumanMessagePromptTemplate.from_template("Please map the components from this explanation to files and directories:\n\n<explanation>\n{explanation}\n</explanation>\n\n<file_tree>\n{file_tree}\n</file_tree>")
        ])
        
        self.diagram_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(SYSTEM_THIRD_PROMPT),
            HumanMessagePromptTemplate.from_template("Create a Mermaid.js diagram based on the following explanation and component mapping:\n\n<explanation>\n{explanation}\n</explanation>\n\n<component_mapping>\n{component_mapping}\n</component_mapping>")
        ])
        
        # Initialize output parser
        self.output_parser = StrOutputParser()
    
    def create_explanation(self, file_tree, readme):
        """
        Step 1: Generate an explanation of the system architecture based on file tree and readme.
        
        Args:
            file_tree (str): The file tree of the repository.
            readme (str): The README content of the repository.
            
        Returns:
            str: Explanation of the system architecture.
        """
        chain = self.explanation_prompt | self.model | self.output_parser
        explanation = chain.invoke({"file_tree": file_tree, "readme": readme})
        
        # Extract content between <explanation> tags if present
        if "<explanation>" in explanation and "</explanation>" in explanation:
            start_idx = explanation.find("<explanation>") + len("<explanation>")
            end_idx = explanation.find("</explanation>")
            explanation = explanation[start_idx:end_idx].strip()
        
        return explanation
    
    def create_component_mapping(self, explanation, file_tree):
        """
        Step 2: Map components from the explanation to files and directories.
        
        Args:
            explanation (str): The explanation generated in step 1.
            file_tree (str): The file tree of the repository.
            
        Returns:
            str: Mapping of components to files and directories.
        """
        chain = self.mapping_prompt | self.model | self.output_parser
        mapping = chain.invoke({"explanation": explanation, "file_tree": file_tree})
        
        # Extract content between <component_mapping> tags if present
        if "<component_mapping>" in mapping and "</component_mapping>" in mapping:
            start_idx = mapping.find("<component_mapping>") + len("<component_mapping>")
            end_idx = mapping.find("</component_mapping>")
            mapping = mapping[start_idx:end_idx].strip()
        
        return mapping
    
    def create_mermaid_diagram(self, explanation, component_mapping):
        """
        Step 3: Generate a Mermaid.js diagram based on explanation and component mapping.
        
        Args:
            explanation (str): The explanation generated in step 1.
            component_mapping (str): The component mapping generated in step 2.
            
        Returns:
            str: Mermaid.js diagram code.
        """
        chain = self.diagram_prompt | self.model | self.output_parser
        mermaid_code = chain.invoke({"explanation": explanation, "component_mapping": component_mapping})
        
        return mermaid_code
    
    def full_process(self, file_tree, readme):
        """
        Run the full GitDiagram process.
        
        Args:
            file_tree (str): The file tree of the repository.
            readme (str): The README content of the repository.
            
        Returns:
            dict: Dictionary containing all generated artifacts.
        """
        explanation = self.create_explanation(file_tree, readme)
        component_mapping = self.create_component_mapping(explanation, file_tree)
        mermaid_diagram = self.create_mermaid_diagram(explanation, component_mapping)
        
        return {
            "explanation": explanation,
            "component_mapping": component_mapping,
            "mermaid_diagram": mermaid_diagram
        }

# Example usage
if __name__ == "__main__":
    from git_context import GitHubContext
    context = GitHubContext()
  
    username = "ahmedkhaleel2004"
    repo = "gitdiagram"
    
    readme = context.get_github_readme(username, repo)
    file_tree = context.get_github_file_paths_as_list(username, repo)
    # Sample file tree and README for testing
   
    # Initialize agent and run the process
    agent = GitDiagramAgent()
    results = agent.full_process(file_tree, readme)
    
    # Print results
    print("EXPLANATION:")
    print(results["explanation"])
    print("\n" + "-"*50 + "\n")
    
    print("COMPONENT MAPPING:")
    print(results["component_mapping"])
    print("\n" + "-"*50 + "\n")
    
    print("MERMAID DIAGRAM:")
    print(results["mermaid_diagram"])