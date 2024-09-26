import requests
import time
from lxml import html, etree
from urllib.parse import urljoin
import os
from datetime import datetime
from tqdm import tqdm  # Progress bar
import json
from IPython.display import Markdown, display, Image
import re
from io import BytesIO
import base64


from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_chroma import Chroma
from langchain.schema.document import Document
from langchain_core.output_parsers import StrOutputParser
from IPython.display import Markdown, display
from dotenv import load_dotenv,find_dotenv
load_dotenv(find_dotenv()) 

vectorstore = None
def load_vectorstore():
    # Vectorstore, for retrieval
    embedding_model=OpenAIEmbeddings(model="text-embedding-3-large")

    vectorstore_path = "vectorstore/chromadb-mmgamerag"
    if os.path.exists(vectorstore_path):
        print(f"Loaded vectorstore from disk: {vectorstore_path}")
    else:
        # Initialize an empty vectorstore and persist to disk
        print(f"Initialized an empty vectorstore in {vectorstore_path}")

    global vectorstore
    vectorstore= Chroma(
                    embedding_function=embedding_model,
                    persist_directory=vectorstore_path,
                    ) 

# LLM invoked as a chatbot
def llm_chatbot(userprompt, chathistory):
    load_vectorstore() # Load the vectorstore for retrieval
    mmgamellm = ChatOpenAI(name="MMGameRag", model_name="gpt-4o-mini", temperature=0.6, streaming=True)

    def format_docs(docs_with_scores):
        """
        Formats the retrieved documents into a string with their content, URL, and score,
        and lists them in order with numbering.
        """
        formatted_docs = []
        
        # Iterate over the documents and their associated scores
        for i, (doc, score) in enumerate(docs_with_scores, 1):  # Enumerate to add numbering starting from 1
            imgsrc = doc.metadata.get('src', '')
            if imgsrc: # Image
                formatted_doc = (
                    f"{i}.\n"
                    f"Image Content:\n{doc.page_content}\n"  # Content of the document
                    f"Page Url: {doc.metadata.get('url', '')}\n"  # Assuming URL is stored in metadata
                    f"Image Src: {doc.metadata.get('src', '')}\n"  # Assuming URL is stored in metadata
                    f"Score: {score}\n"  # Similarity score for the document
                )
            else:  # Text
                formatted_doc = (
                    f"{i}.\n"
                    f"Text Content:\n{doc.page_content}\n"  # Content of the document
                    f"Page Url: {doc.metadata.get('url', '')}\n"  # Assuming URL is stored in metadata
                    f"Score: {score}\n"  # Similarity score for the document
                )
            formatted_docs.append(formatted_doc)  # Add formatted document to the list
        
        return "\n".join(formatted_docs)  # Join all formatted documents into a single string

    # Prompt for code generation
    prompt_template = """你是《黑神话：悟空》这款游戏的AI助手，根据Question和Context专门为玩家提供详尽的游戏攻略并以Markdown的格式输出.请注意：
    1. 在Image中找到与Question和Answer最相关的图像。每个Image都有Text before image，Image descriptioin和Text after image，可以用来判断这个Image应该被插入到与文本答案最匹配的上下文的哪个段落当中。格式如下：
        
        文本答案段落
        <a href="图像1的Url" target="_blank">
        <img src="图像1的Src">
        </a>
        文本答案段落
        <a href="图像2的Url" target="_blank">
        <img src="图像2的Src">
        </a>
        文本答案段落
        ...

    2. 在输出答案的最后，根据问题找到context中的最相关的几个参考文档，并列出Url链接，以供用户参考原始文档。

    Question: 
    {question}

    Context: 
    {context}

    Image:
    {image}

    Answer:
    """

    prompt_code = ChatPromptTemplate.from_template(prompt_template)

    chain = (
        prompt_code
        | mmgamellm
        | StrOutputParser()
    )

    gamer_question = userprompt
    context_retrieval = format_docs(vectorstore.similarity_search_with_score(query=gamer_question, k=5, filter={"type": "text"}))
    # print(context_retrieval + "\n------------------------\n")
    img_retrieval = format_docs(vectorstore.similarity_search_with_score(query=gamer_question, k=5, filter={"type": "img"}))
    # print(img_retrieval + "\n------------------------\n")
    result = chain.invoke({
        "question": gamer_question, 
        "context": context_retrieval,
        "image": img_retrieval
    })


    # display(Markdown(result))
    # display(Image(url="http://img1.gamersky.com/image2024/08/20240819_qy_372_15/image001_S.jpg"))
    
    return result

# Transfer image URL to base64, only for Gamerkey, because Streamlit can't display images from it.
def msg_imgurl_to_base64(msg):
    """
    This function processes the input message, finds <img> tags, extracts the src attribute, 
    checks whether the image is local or remote, and converts it to base64 format.
    After replacing all <img> tag src attributes with base64 encoded images, the function returns the updated message.
    """
    from PIL import Image
    msg_base64 = msg
    
    # Regular expression to find the src attribute within <img> tags
    img_tags = re.findall(r'<img src="([^"]+)"', msg)
    # print(img_tags)
    for src in img_tags:
        try:
            # Judge if the image is from http or local
            # if src.startswith("http"):  # Remote image
            #     response = requests.get(src)
            #     image_open = Image.open(BytesIO(response.content))
            # elif os.path.isfile(src):  # Local image
            #     image_open = Image.open(src)
            # else:
            #     continue  # Skip if src is neither a valid URL nor a local file

            # Use local image for quicker speed
            # Clean the URL to make it filename-safe
            filename_safe_url = src.replace(":", "=").replace("/", "|")
            filename_safe_url = 'docs/rawdata/img/' + filename_safe_url + '.jpg'
            image_open = Image.open(filename_safe_url)


            # Convert image to base64
            buffered = BytesIO()
            image_open.save(buffered, format="JPEG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()

            # Replace the original src with the base64 encoded image
            msg_base64 = msg_base64.replace(src, f"data:image/jpeg;base64,{img_base64}")
        
        except Exception as e:
            print(f"Error processing image {src}: {e}")
    

    # Output the updated message after all replacements
    return msg_base64