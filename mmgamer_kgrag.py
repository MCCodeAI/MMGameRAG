from neo4j import GraphDatabase
import json
from dotenv import load_dotenv,find_dotenv
import os
from tqdm import tqdm  
import uuid
from time import sleep

from langchain_community.vectorstores import Neo4jVector
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI, OpenAI

from userlib.user_logger import log_message
from userlib.manualcheck import *
from userlib.shared import *
from userlib.agentx import *

# Load environment variables
load_dotenv()
# Initialize the knowledge graph connection
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
kg=None
vector_index=None

fusionbot_agent_instructions = """
你是《黑神话：悟空》这款游戏的AI攻略助手，根据问题和提供的网页内容为玩家生成详尽的同时包含文本和图像的游戏攻略。

在提供的网页内容中，有若干个页面，每个页面包含 Title 和若干个 Subtitle，其中每个 Subtitle 都有 Subtitle_page_url 和 content，content 中有文本和以 <img> 标签表示的图片。例如：
-------------
Title: 《黑神话悟空》xx指南
 SubTitle: ...
 Subtitle_page_url: ...
 Subtitle_content:
文本
<img src="...">
文本
<img src="...">
<img src="...">
文本
...
-------------
每个 <img> 都是其上面的文本内容的图像展示。

请按照如下步骤生成答案：
1. 判断哪些网页内容和问题相关，基于以下标准：
内容中是否包含与问题相关的关键词。
内容是否直接回答了用户的问题，或提供了相关背景信息。
是否存在明确的上下文逻辑关联。
2. 保持文本和图像内容按照原网页逻辑顺序排列，保留和上下文相关的的图像内容。
图像输出格式：答案中的图像的src和对应的page_url从提供的网页内容中获取，并按如下格式输出（图片不要缩进）：
[![图片说明](img src)](Subtitle_page_url)
例如:
[![这是xx图片](https://img1.gamersky.com/xxx.jpg)](https://www.gamersky.com/yyy.html)
3. 在文末列出网页的标题和链接。
4. 最后写一个与游戏相关的冷笑话，一定要够冷。
5. 如果没有找到相关的网页内容：
提供一个简短的回答，例如：“未能找到与用户问题相关的网页内容。”
不必强行输出图片或总结。

"""

fusionbot_llm = ChatOpenAI(name="fusionbot_kg_llm", model_name="gpt-4o", streaming=True)
fusionbot_agent = AgentX(name="fusionbot_kg_agent", llm=fusionbot_llm, instructions=fusionbot_agent_instructions)

class KnowledgeGraph:
    def __init__(self, uri, username, password, database="neo4j"):
        """
        Initialize the connection to Neo4j.
        """
        self.driver = GraphDatabase.driver(uri, auth=(username, password), database=database)
    
    def close(self):
        """
        Close the connection to Neo4j.
        """
        self.driver.close()
    
    def add_node(self, label, properties, unique_keys=['name']):
        """
        Add a node with a UUID. If the node already exists based on unique_keys, it will not be duplicated.
        
        :param label: The label (type) of the node.
        :param properties: The properties of the node (dictionary).
        :param unique_keys: List of property keys to use for uniqueness.
        :return: The UUID of the node.
        """
        # Ensure unique_keys are present in properties
        for key in unique_keys:
            if key not in properties:
                raise ValueError(f"Unique key '{key}' must be present in properties.")
        
        # Assign a UUID if not already present
        if 'uuid' not in properties:
            properties['uuid'] = str(uuid.uuid4())
        
        # Construct the MATCH part for MERGE based on unique_keys
        match_conditions = " AND ".join([f"n.{key} = ${key}" for key in unique_keys])
        
        # Prepare parameters for unique keys
        params = {key: properties[key] for key in unique_keys}
        
        # Determine additional properties to set (excluding unique_keys and 'uuid')
        additional_properties = {k: v for k, v in properties.items() if k not in unique_keys + ['uuid']}
        set_conditions = ", ".join([f"n.{key} = $properties.{key}" for key in additional_properties])
        
        # Complete Cypher query with conditional SET clause
        if set_conditions:
            query = f"""
            MERGE (n:{label} {{ {', '.join([f"{key}: ${key}" for key in unique_keys])} }})
            ON CREATE SET n.uuid = $uuid, {set_conditions}
            ON MATCH SET {set_conditions}
            RETURN n.uuid as uuid
            """
            params['uuid'] = properties['uuid']
            params['properties'] = additional_properties
        else:
            query = f"""
            MERGE (n:{label} {{ {', '.join([f"{key}: ${key}" for key in unique_keys])} }})
            ON CREATE SET n.uuid = $uuid
            RETURN n.uuid as uuid
            """
            params['uuid'] = properties['uuid']
        
        try:
            with self.driver.session() as session:
                result = session.run(query, **params)
                record = result.single()
                return record["uuid"] if record else None
        except Exception as e:
            print(f"Error adding node {label} with properties {properties}: {e}")
        return None
    
    def add_relationship(self, label1, prop1, relationship, label2, prop2, rel_properties=None, unique_keys1=['name'], unique_keys2=['name']):
        """
        Add two nodes and their relationship. First ensures nodes exist using MATCH. If not found, an error is logged.
        
        :param label1: The label of the first node.
        :param prop1: The properties of the first node (dictionary, used for matching).
        :param relationship: The type of the relationship.
        :param label2: The label of the second node.
        :param prop2: The properties of the second node (dictionary, used for matching).
        :param rel_properties: The properties of the relationship (dictionary, optional).
        :param unique_keys1: List of property keys to use for uniqueness for the first node.
        :param unique_keys2: List of property keys to use for uniqueness for the second node.
        """
        # Ensure unique_keys are present in properties
        for key in unique_keys1:
            if key not in prop1:
                raise ValueError(f"Unique key '{key}' must be present in prop1.")
        for key in unique_keys2:
            if key not in prop2:
                raise ValueError(f"Unique key '{key}' must be present in prop2.")
        
        # Prepare MATCH conditions for both nodes
        match1 = ", ".join([f"{key}: ${key}" for key in unique_keys1])
        params1 = {key: prop1[key] for key in unique_keys1}
        
        match2 = ", ".join([f"{key}: $prop2_{key}" for key in unique_keys2])
        params2 = {f"prop2_{key}": prop2[key] for key in unique_keys2}
        
        # Construct SET part for additional properties on the relationship
        if rel_properties:
            set_rel = ", ".join([f"r.{k} = $r_{k}" for k in rel_properties])
            params_rel = {f"r_{k}": v for k, v in rel_properties.items()}
            set_clause = f"SET {set_rel}"
        else:
            set_clause = ""
            params_rel = {}
        
        # Complete Cypher query with explicit MATCH and MERGE
        query = f"""
        MATCH (a:{label1} {{ {match1} }})
        MATCH (b:{label2} {{ {match2} }})
        MERGE (a)-[r:{relationship}]->(b)
        {set_clause}
        """
        
        # Combine all parameters
        params = {**params1, **params2, **params_rel}
        
        try:
            with self.driver.session() as session:
                session.run(query, **params)
        except Exception as e:
            print(f"Error creating relationship {relationship} between {prop1} and {prop2}: {e}")
    
    def delete_all(self):
        """
        Delete all nodes and relationships in the knowledge graph.
        """
        query = "MATCH (n) DETACH DELETE n"
        with self.driver.session() as session:
            session.run(query)
    
    def find_node(self, label, property_key, property_value):
        """
        Find a node with a specific label and property.
        
        :param label: The label of the node.
        :param property_key: The property key to match.
        :param property_value: The value of the property to match.
        :return: The node's UUID or None if not found.
        """
        query = f"""
        MATCH (n:{label} {{{property_key}: $value}})
        RETURN n.uuid as uuid
        LIMIT 1
        """
        with self.driver.session() as session:
            result = session.run(query, value=property_value)
            record = result.single()
            return record["uuid"] if record else None
        
    def get_node_properties_by_uuid(self, label, uuid):
        """
        Find a node by its UUID and get all its properties.

        :param label: The label of the node.
        :param uuid: The UUID of the node.
        :return: A dictionary of the node's properties, or None if not found.
        """
        query = f"""
        MATCH (n:{label} {{uuid: $uuid}})
        RETURN properties(n) AS node_properties
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, uuid=uuid)
                record = result.single()
                return record["node_properties"] if record else None
        except Exception as e:
            print(f"Error retrieving properties for node with UUID {uuid}: {e}")
            return None

    def get_related_nodes(self, label, uuid, relationship, direction="OUTGOING"):
        """
        Find the nodes related to the given node by a specific relationship.

        :param label: The label of the starting node.
        :param uuid: The UUID of the starting node.
        :param relationship: The type of the relationship to follow.
        :param direction: The direction of the relationship ("OUTGOING", "INCOMING", "BOTH").
        :return: A list of related nodes (as dictionaries of properties).
        """
        # Determine relationship direction
        if direction == "OUTGOING":
            rel_pattern = f"-[:{relationship}]->"
        elif direction == "INCOMING":
            rel_pattern = f"<-[:{relationship}]-"
        elif direction == "BOTH":
            rel_pattern = f"-[:{relationship}]-"
        else:
            raise ValueError("Invalid direction. Use 'OUTGOING', 'INCOMING', or 'BOTH'.")

        query = f"""
        MATCH (n:{label} {{uuid: $uuid}}){rel_pattern}(related)
        RETURN properties(related) AS related_properties
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, uuid=uuid)
                return [record["related_properties"] for record in result]
        except Exception as e:
            print(f"Error retrieving related nodes for node with UUID {uuid} via relationship {relationship}: {e}")
            return []

def init_kg_vectorindex(): 
    global kg, vector_index 
    kg = KnowledgeGraph(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
    # Initialize the vector index, takes 3m with $1.20, it will simply load it if existed.
    vector_index = Neo4jVector.from_existing_graph(
        OpenAIEmbeddings(model="text-embedding-3-large"),
        url=NEO4J_URI,
        username=NEO4J_USERNAME,
        password=NEO4J_PASSWORD,
        index_name='KG_Retrieve_Task',
        node_label="txt",
        text_node_properties=['content', 'page_url'],
        embedding_node_property='embedding',
        **{"search_type": "hybrid"}
    )

def revert_url(safe_url):
    reverted_url = safe_url.replace("_text_with_images.html","").replace("=", ":").replace("|", "/")
    return reverted_url

def convert_url(url):
    safe_url = url.replace(":", "=").replace("/", "|") + "_text_with_images.html"
    return safe_url

def determine_category(file_name):
    """
    Determine the category based on the file name.
    
    :param file_name: The name of the file.
    :return: The category as a string.
    """
    if "handbook" in file_name:
        return "攻略"
    elif "down" in file_name:
        return "下载"
    elif "news" in file_name or "tech" in file_name:
        return "新闻"
    else:
        return "其它"

def process_files_and_create_nodes(directory, kg):
    """
    Processes all .html files in the directory and creates nodes/relationships in the Knowledge Graph.
    
    :param directory: The directory containing .html files.
    :param kg: An instance of KnowledgeGraph.
    """
    try:
        # List all .html files in the directory
        html_files = [file_name for file_name in os.listdir(directory) if file_name.endswith(".html")]
        
        # Add a progress bar
        with tqdm(total=len(html_files), desc="Processing HTML Files", unit="file") as pbar:
            for file_name in html_files:
                file_path = os.path.join(directory, file_name)
                category = determine_category(file_name)

                page_url = file_name
                
                with open(file_path, "r", encoding="utf-8") as file:
                    file_content = file.read()
                    lines = file_content.splitlines()


                if len(lines) < 1:
                    pbar.update(1)
                    continue  # Skip empty files

                # Extract title from the first line
                title_line = lines[0].strip()
                if title_line.startswith("Title: "):
                    title = title_line.replace("Title: ", "").replace("-游民星空 GamerSky.com", "").split("_")[0]
                else:
                    title = title_line

                # Extract subtitle
                if len(lines) > 1:
                    second_line = lines[1].strip()
                    if second_line.startswith("第"):
                        subtitle = {"name": second_line, "page_url": page_url}
                    else:
                        subtitle = {"name": "第一页", "page_url": page_url}
                else:
                    subtitle = {"name": "第一页", "page_url": page_url}

                # Create Category node
                kg.add_node("Category", {"name": category}, unique_keys=['name'])

                # Create Title node and establish relationship
                kg.add_node("Title", {"name": title}, unique_keys=['name'])
                kg.add_relationship(
                    label1="Category",
                    prop1={"name": category},
                    relationship="HAS_TITLE",
                    label2="Title",
                    prop2={"name": title}
                )

                # Create Subtitle node and establish relationship
                kg.add_node("Subtitle", subtitle, unique_keys=['page_url'])
                kg.add_relationship(
                    label1="Title",
                    prop1={"name": title},
                    relationship="HAS_SUBTITLE",
                    label2="Subtitle",
                    prop2=subtitle,
                    rel_properties=None,
                    unique_keys1=["name"],
                    unique_keys2=["page_url"]
                )

                # Create txt node with the full content of the file
                txt_properties = {
                    "content": file_content,
                    "page_url": page_url  # Use page_url as the unique key
                }
                kg.add_node("txt", txt_properties, unique_keys=['page_url'])
        
                # Establish HAS_TXT relationship
                kg.add_relationship(
                    label1="Subtitle",
                    prop1={"page_url": page_url},
                    relationship="HAS_TXT",
                    label2="txt",
                    prop2=txt_properties,
                    rel_properties=None,
                    unique_keys1=["page_url"],
                    unique_keys2=["page_url"]
                )

                

                # Update the progress bar
                pbar.update(1)
    except Exception as e:
        print(f"Error: {e}")


def process_mmimg_items_with_progress(mmimg_json_path, kg):
    """
    Traverses all items in docs/mmimg.json, converts each item's URL to a safe URL (only before '?', replace ":" with "=", "/" with "|"),
    finds the matching Subtitle node in kg, aggregates content_before_image, image_description,
    and content_after_image into a single string, creates an img node with this content and src,
    and establishes a HAS_IMG relationship with the Subtitle node. Displays progress using a progress bar.
    
    :param mmimg_json_path: Path to the mmimg.json file.
    :param kg: An instance of KnowledgeGraph.
    """

    # Load mmimg.json data
    try:
        with open(mmimg_json_path, 'r', encoding='utf-8') as json_file:
            mmimg_data = json.load(json_file)
        print(f"Successfully loaded {mmimg_json_path}")
    except Exception as e:
        print(f"Error loading {mmimg_json_path}: {e}")
        return

    error_count = 0
    # Iterate over each item with a progress bar
    for item in tqdm(mmimg_data, desc="Processing mmimg.json items"):
        url = item.get('url', '')
        if not url:
            continue

        # Convert URL to safe_url: take the string before '?', replace ":" with "=", and "/" with "|"
        safe_url = url.split('?')[0].replace(":", "=").replace("/", "|")

        safe_url = safe_url + "_text_with_images.html"

        # Find the matching Subtitle node with page_url == safe_url
        subtitle_uuid = kg.find_node("Subtitle", "page_url", safe_url)
        if not subtitle_uuid:
            error_count +=1
            print("No matching Subtitle node found:" + safe_url + "error_count:" + str(error_count))
            
            continue  # No matching Subtitle node found

        # Aggregate content_before_image, image_description, and content_after_image
        content_before = item.get('content_before_image', '')
        image_description = item.get('image_description', '')
        content_after = item.get('content_after_image', '')
        aggregated_content = f"content_before_image: {content_before}\nimage_description: {image_description}\ncontent_after_image: {content_after}".strip()

        if not aggregated_content:
            continue  # Skip if aggregated content is empty

        # Create img node with aggregated_content and src
        img_properties = {
            "aggregated_content": aggregated_content,
            "src": item.get('src', ''),  # Add src attribute from the item
            "url": url  # original URL
        }
        kg.add_node("Img", img_properties, unique_keys=['src'])

        # Establish HAS_IMG relationship with Subtitle node
        kg.add_relationship(
            label1="Subtitle",
            prop1={"page_url": safe_url},
            relationship="HAS_IMG",
            label2="Img",
            prop2=img_properties,
            rel_properties=None,
            unique_keys1=["page_url"],
            unique_keys2=["src"]
        )


def create_constraints(kg):
    """
    Create unique constraints on the uuid property for each label.
    
    :param kg: An instance of KnowledgeGraph.
    """
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Category) REQUIRE c.uuid IS UNIQUE;",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (g:Game) REQUIRE g.uuid IS UNIQUE;",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Title) REQUIRE t.uuid IS UNIQUE;",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Subtitle) REQUIRE s.uuid IS UNIQUE;"
    ]
    with kg.driver.session() as session:
        for constraint in constraints:
            session.run(constraint)


def create_knowledge_graph():
    try:
        # Create unique constraints (run once)
        create_constraints(kg)
        
        # Optional: Clear the existing knowledge graph
        kg.delete_all()
        
        # Add Game node and its categories
        kg.add_node("Game", {"name": "黑神话悟空"}, unique_keys=['name'])
        for category in ["攻略", "新闻", "下载", "其它"]:
            kg.add_node("Category", {"name": category}, unique_keys=['name'])
            kg.add_relationship(
                label1="Game",
                prop1={"name": "黑神话悟空"},
                relationship="HAS_CATEGORY",
                label2="Category",
                prop2={"name": category}
            )
        
        # Process all files and create nodes/relationships
        process_files_and_create_nodes("docs/rawdata", kg)
        # Process mmimg.json and create img nodes with HAS_IMG relationships
        process_mmimg_items_with_progress("docs/mmimg.json", kg)
        
        print("Knowledge Graph construction completed.")
    finally:
        # Close the connection
        kg.close()


def agent_flow_kg(user_q):
    """
    The main flow to retrieve knowledge graph relations based on the user's query.

    Steps:
    1. Perform a similarity search in the vector index using the user's query.
    2. Retrieve related subtitle nodes connected to the matched content.
    3. Retrieve the title node connected to the subtitle nodes.
    4. Traverse all subtitle nodes linked to the title node and extract their content.
    5. Generate a formatted context string from the retrieved relationships.
    6. Use the FusionBot agent to generate a response based on the user's query and the retrieved context.

    :param user_q: The user's query string.
    :return: A response string containing the answer with images generated by the FusionBot agent.
    """
    # Log the start of similarity search in the vector index
    log_message("Starting similarity search in the vector index for the user's query.")
    shared_flow_state_str.value = "🔍 Performing similarity search..."  # Indicate progress of the search
    response = vector_index.similarity_search_with_relevance_scores(user_q, k=4)

    # Log after retrieving the similarity search results
    log_message("Similarity search completed. Processing retrieved documents.")
    shared_flow_state_str.value = "📄 Processing retrieved documents..."  # Indicate document processing

    output = []  # Prepare the output context
    output.append('-------------')
    # Process each retrieved document
    for document, score in response:
        uuid = document.metadata.get('uuid', 'No UUID found')

        # Retrieve subtitle nodes connected to the current document
        subtitles = kg.get_related_nodes('txt', uuid, 'HAS_TXT', 'INCOMING')

        # Retrieve title nodes connected to the first subtitle node
        titles = kg.get_related_nodes('Subtitle', subtitles[0].get('uuid'), 'HAS_SUBTITLE', 'INCOMING')

        
        output.append('Title: ' + titles[0].get('name'))

        # Retrieve all subtitle nodes related to the title node
        subtitles = kg.get_related_nodes('Title', titles[0].get('uuid'), 'HAS_SUBTITLE', 'OUTGOING')

        for subtitle in subtitles:
            output.append(' SubTitle: ' + subtitle.get('name'))

            # Retrieve the text nodes associated with the current subtitle
            subtitle_txt = kg.get_related_nodes('Subtitle', subtitle.get('uuid'), 'HAS_TXT', 'OUTGOING')
            output.append(' Subtitle_page_url: ' + revert_url(subtitle_txt[0].get('page_url')))
            output.append(' Subtitle_content: ' + subtitle_txt[0].get('content') + '\n')
        output.append('-------------')
        
    context_q = '\n'.join(output)

    # Log the completion of context generation
    log_message("Context for FusionBot generated. Preparing to send the query.")
    shared_flow_state_str.value = "🤖 Preparing query for FusionBot..."  # Indicate query preparation

    # Use the FusionBot agent to generate an answer with images
    answer_with_image = fusionbot_agent.stream_response(f"问题是：' {user_q} '\n网页内容是:\n\n{context_q}")

    # answer_with_image = "ssssss"
    # Log the completion of the FusionBot query
    log_message("FusionBot has completed the response generation.")
    # shared_flow_state_str.value = "✅ Response generation completed."  # Indicate completion

    return answer_with_image


# 全丹方收集指南
# Error: 'builtin_function_or_method' object has no attribute 'sleep'
 


# When running as a standalone script
if __name__ == "__main__":
    pass
    init_kg_vectorindex()
    # create_knowledge_graph()

# When imported as a module
if __name__ == "mmgamer_kgrag":
    pass
    init_kg_vectorindex()
    print(__name__)





## 
FYI = '''
MATCH p = (n)-[*]->(m)
WITH p LIMIT 1000
RETURN p
ORDER BY rand()
LIMIT 500
'''

