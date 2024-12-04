import os
import sys
import time
import multiprocessing
from dotenv import load_dotenv, find_dotenv
from langchain_openai import ChatOpenAI, OpenAI
from tqdm import tqdm
from urllib.parse import urljoin
import urllib.request
from lxml import html, etree
import requests
import json
import shutil
import re
from io import BytesIO
import base64
from filelock import FileLock
import streamlit as st
import threading

from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq

from userlib.user_input import *
from userlib.user_logger import log_message
from userlib.agentx import *
from userlib.shared import *
from userlib.manualcheck import *

# Load environment variables
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


class WebScraper:
    """
    Class for web scraping tasks, including crawling, cleaning, and saving content.
    """

    def __init__(self, url):
        """
        Initialize the web scraper with the target URL.
        """
        self.url = url

    # Base64 encode the image
    def get_base64_encoded_image(self, image_url):
        """
        Fetches the image from the given URL and returns its Base64 encoded string.
        """
        return ''  # Temporarily returning an empty string for base64

    # Save content to file, for back up only, structured data is saved in JSON file.
    def save_content_to_file(self, content, filename):
        """
        Saves the provided content to a file.
        """
        with open(filename, "w", encoding="utf-8") as file:
            file.write(content)
        if log_verbose:  log_message(f"Content successfully saved to {filename}")

    def save_image_to_file(self, img_src):
        """
        Save the image from the provided URL to a specified directory with a safe filename.
        
        Parameters:
        img_src (str): The URL of the image to be saved.
        """
        # Clean the URL to make it filename-safe
        filename_safe_url = img_src.replace(":", "=").replace("/", "|")
        
        # Specify the save path
        save_directory = "quicksearch_cache/rawdata/img"
        os.makedirs(save_directory, exist_ok=True)

        # Define the filename
        filename = os.path.join(save_directory, f"{filename_safe_url}")
        
        # Download and save the image
        urllib.request.urlretrieve(img_src, filename)
        if log_verbose:  log_message(f"Image saved as: {filename}")


    # Save content to JSON file in a specified format
    def save_data_json_with_format(self, content, filename):
        """
        Saves the provided content to a JSON file with specified indentation format.
        Ensures the content is appended correctly to an existing JSON array.
        Uses file locking to prevent race conditions during concurrent access.
        """
        lock = FileLock(f"{filename}.lock")
        
        with lock:
            # Check if the file exists and load its content if it does
            if os.path.exists(filename):
                with open(filename, 'r', encoding="utf-8") as json_file:
                    try:
                        existing_data = json.load(json_file)
                    except json.JSONDecodeError:
                        existing_data = []
            else:
                existing_data = []

            # Append new content to the existing data
            existing_data.extend(content)

            # Save the updated data back to the file
            with open(filename, 'w', encoding="utf-8") as json_file:
                json.dump(existing_data, json_file, indent=4, ensure_ascii=False)

            log_message(f"JSON content successfully saved to {filename}")

    

    # Extract text and images from the part with class="Mid2L_con" and save to docs first, then JSON. n means how many lines of text was stored before and after each image.
    def extract_text_and_images(self, currenturl, tree, n=20):
        """
        Extracts text and images from the part of the webpage with class="Mid2L_con", 
        and splits into two parts: one with text only, and one with text + images.
        Saves content to files first in 'docs', then processes and saves image metadata to JSON files.
        """
        
        if tree is not None:

            # Extract the page title
            # title = tree.xpath('//title/text()') # regular title
            # if title:
            #     title_text = title[0].strip()
            # else:
            #     title_text = 'No Title'
            
            title_text = ''
            # Extract title with detailed data and author info, such as "2023-08-21 14:06:02 来源：游民星空 作者：LIN木木 编辑：LIN木木　浏览：17536"
            mid2L_tit_elements = tree.xpath('//div[@class="Mid2L_tit"]')
            if mid2L_tit_elements:
                title_text = mid2L_tit_elements[0].text_content()           
                # Remove leading and trailing whitespace and empty lines in the middle
                lines = [line.strip() for line in title_text.splitlines() if line.strip()] 
                title_text = "\n".join(lines)

            # Extract the part of the page with class="Mid2L_con"
            mid2l_con = tree.xpath('//div[@class="Mid2L_con"]')

            # Clean the URL to make it filename-safe
            filename_safe_url = currenturl.replace(":", "=").replace("/", "|")

            if mid2l_con is not None:
                text_content_list = [f"(Page_Url): {currenturl}"]
                text_with_images_list = [f"(Page_Url): {currenturl}"]
                text_content_list.append(f"Title: {title_text}")
                text_with_images_list.append(f"Title: {title_text}")
                
                txt_data_list = []
                stop_extraction = False

                # First pass: gather all text and image elements
                for element in mid2l_con[0].iter():
                    if stop_extraction:
                        break

                    # If it's a text node, extract the text and tail
                    if element.text and isinstance(element.tag, str):
                        text = element.text.strip()
                    else:
                        text = ""

                    # Also check the 'tail' for text outside the tag
                    if element.tail:
                        tail_text = element.tail.strip()
                    else:
                        tail_text = ""

                    # Combine text and tail_text
                    combined_text = text + " " + tail_text if text or tail_text else ""

                    # Append the combined text to the list if it's not empty and does not contain certain phrases
                    if combined_text:
                        # Check if the combined text starts with "本文由游民星空"
                        if combined_text.startswith("本文由游民星空"):
                            stop_extraction = True
                        else:
                            # Check if combined_text contains any of the unwanted phrases
                            unwanted_phrases = [
                                "更多相关内容请关注",
                                "责任编辑",
                                "友情提示：",
                                "本文是否解决了您的问题",
                                "已解决",
                                "未解决",
                                "黑神话：悟空专区",
                                "上一页",
                                "下一页"
                            ]
                            if not any(phrase in combined_text for phrase in unwanted_phrases):
                                text_content_list.append(combined_text)
                                text_with_images_list.append(combined_text)


                    # If it's an <img> tag
                    if element.tag == 'img' and not stop_extraction:
                        img_src = element.get('src')  # Fallback to the src of the <img> tag
                        img_data_src = element.get('data-src', img_src)  # Use data-src if available, otherwise fallback to src
                        img_alt = element.get('alt', '')
                        img_title = element.get('title', '')
                        img_width = element.get('width', '')
                        img_height = element.get('height', '')

                        # Convert relative paths to absolute URLs
                        img_src = urljoin(currenturl, img_data_src)

                        img_src=img_src.replace('_S.jpg', '.jpg')

                        # # Save the raw image to a file
                        # self.save_image_to_file(img_src)

                        # Check if the parent tag is <a>
                        parent = element.getparent()
                        if parent is not None and parent.tag == 'a' and not(parent.get('href').endswith('.jpg')):
                            href_url = parent.get('href')  # Use the href of the parent <a> tag
                        else:
                            href_url = currenturl  # Fallback to the src of the <img> tag

                        # Replace the placeholder with the actual image tag
                        img_tag = f'<img src="{img_src}" alt="{img_alt}" width="{img_width}" height="{img_height}" title="{img_title}" Page_Url="{href_url}">'
                        text_with_images_list.append(img_tag)

                # Convert text_content_list to a single string
                text_content_str = '\n'.join(text_content_list)
                text_with_images_list_str = '\n'.join(text_with_images_list)

                # Specify the save path
                save_directory = "quicksearch_cache/rawdata"
                os.makedirs(save_directory, exist_ok=True)


                # Save content to docs folder first
                text_only_filename = os.path.join("quicksearch_cache/rawdata/", f"{filename_safe_url}_text_only.txt")
                text_with_images_filename = os.path.join("quicksearch_cache/rawdata/", f"{filename_safe_url}_text_with_images.html")
                self.save_content_to_file(text_content_str, text_only_filename)
                self.save_content_to_file(text_with_images_list_str, text_with_images_filename)                
                log_message(f"Html and text files successfully saved for {filename_safe_url}")

                # # Get img data
                # img_data_list = []
                # for img_index, line in enumerate(text_with_images_list):
                #     if line.startswith("<img"):
                #         # Extract image attributes
                #         img_src = line.split('src="')[1].split('"')[0]
                #         img_alt = line.split('alt="')[1].split('"')[0]
                #         img_width = line.split('width="')[1].split('"')[0]
                #         img_height = line.split('height="')[1].split('"')[0]
                #         img_title = line.split('title="')[1].split('"')[0]
                        
                #         # Get Base64 encoded image content (currently returning empty string)
                #         img_base64 = self.get_base64_encoded_image(img_src)
                        
                #         # Get n lines before and after the image
                #         content_before_image = []
                #         content_after_image = []
                        
                #         # Extract n lines before the image, stop if another <img> tag is encountered
                #         for i in range(img_index-1, max(0, img_index-n)-1, -1):
                #             # if '<img' in text_with_images_list[i]:
                #             #     break
                #             content_before_image.append(text_with_images_list[i])
                #         content_before_image.reverse()
                        
                #         # Extract n lines after the image, stop if another <img> tag is encountered
                #         for i in range(img_index+1, min(len(text_with_images_list), img_index+1+n)):
                #             # if '<img' in text_with_images_list[i]:
                #             #     break
                #             content_after_image.append(text_with_images_list[i])
                        
                #         content_before_image_str = '\n'.join(content_before_image)
                #         content_after_image_str = '\n'.join(content_after_image)
                #         image_descrip_str = ''
                        
                #         # Add the image metadata to the img_data_list
                #         img_data_list.append({
                #             "page_title": title_text,  # To recognize this image with the page title.
                #             "src": img_src,
                #             "base64": img_base64,  # Temporarily set to an empty string
                #             "title": img_title,
                #             "alt": img_alt,
                #             "content_before_image": content_before_image_str,
                #             "image_description": image_descrip_str,
                #             "content_after_image": content_after_image_str,
                #             "url": currenturl,  # Current page url
                #             "type": "img"
                #         })


                # txt_data_list.append({
                #         "txt": text_content_str,
                #         "url": currenturl,
                #         "type": "text"
                #     })

                # # Save the entire text_content_str directly to mmtext.json
                # self.save_data_json_with_format(txt_data_list, "quicksearch_cache/mmtext.json")

                # # Save the image metadata to JSON as a list of objects
                # self.save_data_json_with_format(img_data_list, "quicksearch_cache/mmimg.json")

                return f"Content saved to files in docs and JSON files processed."
            else:
                return "No content found with class='Mid2L_con'."
        else:
            return "Failed to fetch content."

    # Load existing links from the JSON file
    def load_existing_links(self, filename):
        """
        Loads existing links from the specified JSON file.
        If the file doesn't exist, it returns an empty list.
        """
        if os.path.exists(filename):
            with open(filename, 'r', encoding="utf-8") as json_file:
                return json.load(json_file)
        return []
        

    # Global variable to track new links added across function calls
    new_link_count = 0
    
    def save_link_to_json(self, new_link, filename="quicksearch_cache/links.json"):
        """
        Saves the provided link to the specified JSON file.
        If the link contains .shtml?, it removes the string after .shtml.
        If the link already exists, it returns False.
        If the link is new and added, it returns True.
        Logs the added link along with the updated total count of new links.
        """
        
        # Check if the new_link contains '.shtml?'
        if ".shtml?" in new_link:
            new_link = new_link.split(".shtml?")[0] + ".shtml"
        links = self.load_existing_links(filename)
        
        if new_link not in links:
            links.append(new_link)
            self.new_link_count += 1  # Increment the global counter for a new link
            with open(filename, 'w', encoding="utf-8") as json_file:
                json.dump(links, json_file, indent=4, ensure_ascii=False)
            log_message(f"New link added to links.json: {new_link}. Total links: {self.new_link_count}")
            return True
        else:
            log_message(f"Link already in links.json: {new_link}")
            return False    



    # Global variable to track new URLs added across function calls
    new_url_count = 0

    # Save crawled URLs to the JSON file and count added URLs
    def save_crawled_url_to_json(self, new_url, filename="quicksearch_cache/crawled_urls.json"):
        """
        Saves the provided URL to the specified JSON file.
        If the URL already exists, it returns False.
        If the URL is new and added, it returns True.
        Logs the added URL along with the updated total count of new URLs.
        """
        # Ensure the directory exists
        directory = os.path.dirname(filename)
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Check if the file exists and load existing URLs
        if os.path.exists(filename):
            with open(filename, 'r', encoding="utf-8") as json_file:
                urls = json.load(json_file)
        else:
            urls = []

        log_message(f"-----------------------------------------------------------")

        # Check if the URL is new
        if new_url not in urls:
            urls.append(new_url)
            self.new_url_count += 1  # Increment the global counter for a new URL
            with open(filename, 'w', encoding="utf-8") as json_file:
                json.dump(urls, json_file, indent=4, ensure_ascii=False)
            log_message(f"New crawled URL added to crawled_urls.json: {new_url}. Total URLs: {self.new_url_count}")
            return True
        else:
            log_message(f"URL already in crawled_urls.json: {new_url}")
            return False

        

    # Check if the link exists in the JSON file
    def check_link_in_json(self, new_link, filename="quicksearch_cache/links.json"):
        """
        Checks if the provided link exists in the specified JSON file.
        If the link contains .shtml?, it removes the string after .shtml.
        Returns True if the link is found, otherwise False.
        """
        # Check if the new_link contains '.shtml?'
        if ".shtml?" in new_link:
            new_link = new_link.split(".shtml?")[0] + ".shtml"
        
        # Load existing links from the JSON file
        links = self.load_existing_links(filename)
        
        # Return True if the link is found, otherwise False
        if new_link in links:
            return True
        else:
            return False



    # Send request with retry mechanism
    def fetch_url_with_retries(self, url, max_retries=2):
        """
        Attempts to fetch content from the given URL, retrying up to max_retries times.
        If the request fails, it waits for 1 second before retrying.
        """
        retries = 0
        while retries < max_retries:
            try:
                response = requests.get(url, timeout=1)  # Set timeout to 3 seconds
                
                # If the status code is 200, the request was successful, return the content
                if response.status_code == 200:
                    log_message(f"Success on attempt {retries + 1} for {url}")
                    return response.content
                
                # If the status code is not 200, log the failure reason
                else:
                    log_message(f"Attempt {retries + 1} failed with status code {response.status_code}")
            
            except requests.RequestException as e:
                # Capture request exceptions like timeout or connection errors
                log_message(f"Attempt {retries + 1} failed with error: {e}")
            
            # Increment retry count
            retries += 1
            
            # Wait for 1 second before retrying
            time.sleep(1)

        # If max retries are exceeded, return None or handle the error accordingly
        log_message(f"Failed to fetch the URL after {max_retries} attempts.")
        return None

    # New function to crawl the webpage and its linked pages up to a given depth, this only fits the page in gamesky. 
    def crawl_and_extract(self, url, keyword, linkdepth=1):
        """
        Crawls the webpage starting from the given URL, and checks for links within the page.
        If a page contains the term specified in 'keyword' in either "Mid2L_con" class or in the title,
        or in the whole HTML content, it saves the link in 'links.json'.
        Crawls up to the given linkdepth (including the original URL).
        """
        def crawl_nest(url, current_depth, max_depth):

            # Check if the link has been crawled
            if self.save_crawled_url_to_json(url) == False:
                return


            # Check if the link exists in the JSON file and it is in the max depth, if yes, just return.
            if self.check_link_in_json(url) == True and current_depth == max_depth:
                log_message(f"Link found in links.json: {url} (Depth: {current_depth})")
                return
            
            # Fetch the page content
            html_content = self.fetch_url_with_retries(url)
            if not html_content:
                log_message(f"Failed to fetch content for {url} (Depth: {current_depth})")
                return
            
            # Parse the HTML using lxml
            tree = html.fromstring(html_content)

            # Check if class="Mid2L_con" or title contains the keyword
            mid2l_con_elements = tree.xpath('//div[@class="Mid2L_con"]')
            title_elements = tree.xpath('//title/text()')
            
            # Check if keyword exists in Mid2L_con or Title
            mid2l_con_text = mid2l_con_elements[0].text_content() if mid2l_con_elements else ""
            title_text = title_elements[0] if title_elements else ""
            
            links = []

            if mid2l_con_text:
                if keyword in mid2l_con_text or keyword in title_text:
                    if current_depth == 0: current_depth = 1   # 0 is for url without mid2l_con, so we set it to 1
                    log_message(f"Found '{keyword}' in Mid2L_con or Title at {url} (Depth: {current_depth})")
                    linkexist = self.save_link_to_json(url)  # Save the link to JSON
                    if linkexist == True:
                        self.extract_text_and_images(url, tree)
                    if current_depth < max_depth:
                        # Get all links on the page
                        alinks = tree.xpath('//div[@class="Mid2L_con"]//a[@href]/@href')
                        links = [urljoin(url, link) for link in alinks if link.startswith(('http', '/'))]
                        links = list(set(links))
                        # Remove unwanted link, links starting with 'javascript:', and those ending with '.jpg' or '.png'
                        unwanted_link = "" # "https://www.gamersky.com/z/bmwukong/"
                        filtered_links = [link for link in links if link != unwanted_link and not link.startswith('javascript:') and not link.endswith(('.jpg', '.png'))]
                        links = filtered_links
                        log_message(f"Found {len(links)} links on {url} (Depth: {current_depth}). Crawling deeper...")

            else:
                # If not found in Mid2L_con, check the full HTML content
                if keyword in title_text: 
                    # current_depth = 0   # use this to jump the page without Mid2L_con(overview page) if nest crawling needed. 
                    log_message(f"Found '{keyword}' in full HTML at {url} (Depth: {current_depth})")
                # if keyword in html_content.decode('utf-8', errors='ignore'):                
                    linkexist = self.save_link_to_json(url)  # Save the link to JSON
                    if linkexist == True:
                        pass
                        self.extract_text_and_images(url, tree)   # Don't extract if it is just an overview

                    if current_depth < max_depth:
                        # Get all links on the page
                        alinks = tree.xpath('//a[@href]/@href')
                        links = [urljoin(url, link) for link in alinks if link.startswith(('http', '/'))]
                        links = list(set(links))
                        # Remove unwanted link, links starting with 'javascript:', and those ending with '.jpg' or '.png'
                        unwanted_link = "" # "https://www.gamersky.com/z/bmwukong/"
                        filtered_links = [link for link in links if link != unwanted_link and not link.startswith('javascript:') and not link.endswith(('.jpg', '.png'))]
                        links = filtered_links
                        log_message(f"Found {len(links)} links on {url} (Depth: {current_depth}). Crawling deeper...")
                else:
                    log_message(f"No '{keyword}' found at {url} (Depth: {current_depth})")

            
            if current_depth < max_depth and links:
                current_depth = current_depth + 1
                # Recursively crawl the found links, with increased depth
                for link in tqdm(links, desc=f"Crawling depth {current_depth}/{max_depth}", leave=False, position=1, dynamic_ncols=True):
                    crawl_nest(link, current_depth, max_depth)

        crawl_nest(url, 1, linkdepth)



    def crawl(self):
        """
        Method to crawl web content from the specified URL, clean and save to disk.
        """
        try:
            # Placeholder for crawling implementation
            log_message(f"Starting crawl for URL: {self.url}")

            self.crawl_and_extract(self.url, game_keywords, 1) # Crawl the URL and its linked pages up to a depth
            log_message(f"⭐️1. Completed crawl and save data for URL: {self.url}")
        except Exception as e:
            log_message(f"Error crawling URL: {self.url}, Error: {e}")




def fetch_links_with_keyword(user_q):
    """
    Fetches links from a search result page that contain the specified keyword.
    The function retrieves content from the search URL and looks for links in
    elements with class="Mid2_L". It collects only those URLs containing the
    user_q keyword, ensuring there are no duplicates.

    Parameters:
        user_q (str): The keyword to search for in the URLs.

    Returns:
        list: A list of URLs containing the user_q keyword.
    """
    # search_url = f"https://so.gamersky.com/?s=%E9%BB%91%E7%A5%9E%E8%AF%9D {user_q}"  # Direct search engine
    search_url = f"https://soso.gamersky.com/cse/search?q={user_q}&s=3068275339727451251&nsid=1&nsid=1"  # Vague search engine
    links = []

    try:
        # Fetch the content of the search URL
        response = requests.get(search_url, verify=False)
        if response.status_code != 200:
            log_message(f"Failed to fetch content for {search_url}")
            return []

        # Parse the HTML content using lxml
        tree = html.fromstring(response.content)

        # Find all elements with class="Mid2_L" and extract links
        # mid2l_elements = tree.xpath('//div[@class="Mid2_L"]//a[@href]/@href')  # Direct search engine
        mid2l_elements = tree.xpath('//div[@class="content-main"]//a[@href]/@href')  # Vague search engine

        if mid2l_elements:
            # log_message(mid2l_elements)
            # Filter links to include only those containing the user_q keyword
            for link in mid2l_elements:
                full_url = urljoin(search_url, link)
                if full_url not in links:
                    links.append(full_url)

            log_message(f"Found {len(links)} links containing '{user_q}' on {search_url}")
        else:
            log_message(f"No elements with class='Mid2_L' found on {search_url}")

    except Exception as e:
        log_message(f"Error fetching or parsing content from {search_url}: {e}")

    return links

def process_url(url):
    """
    Function to process a single URL: crawl, clean, and save.
    """
    scraper = WebScraper(url)
    scraper.crawl()

def build_kg_database():
    """
    Function to build a Knowledge Graph (KG) database.
    """
    try:
        log_message("Starting KG database build")
        # TODO: Add KG database build implementation
        log_message("Completed KG database build")
    except Exception as e:
        log_message(f"Error building KG database: {e}")

def build_vector_database():
    """
    Function to build a Vector database (optional).
    """
    try:
        log_message("Starting Vector database build")
        # TODO: Add Vector database build implementation
        log_message("Completed Vector database build")
    except Exception as e:
        log_message(f"Error building Vector database: {e}")



def llm_groq_agent(user_q):
    """
    Function to call the LLM with the given prompt.
    """
    try:
        # mmgamequickllm = ChatGroq(name="MMGameQuickRag_groq", model_name="llama-3.2-3b-preview", temperature=0.6, streaming=True)
        mmgamequickllm = ChatOpenAI(name="MMGameQuickRag", model_name="gpt-4o", temperature=0.6, streaming=True)
        
        prompt_quick = """

        Question: 
        {question}

        Answer:
        """

        prompt_game_quick = ChatPromptTemplate.from_template(prompt_quick)

        chain_game_text_image_together = (
            prompt_game_quick
            | mmgamequickllm
            | StrOutputParser()
        )


        # partial_message = ""
        # for response in chain_game_text_image_together.invoke({"question": user_q}):
        #     partial_message += response.content
        #     return response.content

        result_game_text_image = chain_game_text_image_together.invoke({
            "question": user_q
        })

        return result_game_text_image
    except Exception as e:
        log_message(f"Error processing prompt: {user_q}, Error: {e}")
        return None

def llm_agent(user_q):
    """
    Function to call the LLM with the given prompt.
    """
    try:
        mmgamequickllm = ChatOpenAI(name="MMGameQuickRag", model_name="gpt-4o-mini", temperature=0.6, streaming=True)
        prompt_quick = """你是《黑神话：悟空》这款游戏的AI攻略助手，根据Question、Context为玩家生成详尽的图文并茂的游戏攻略.你应该忠于原文的内容，并尽可能详细的给出答案。请注意以下规则：
        1. 在Context中有若干个页面，每个页面都包含有Page Url，Title，文本内容和以<img>标签表示的图片。例如：

        Page Url:
        Title:
        文本a
        Image1
        文本b
        Image2
        Image3
        文本c
        ...

        一般来说，Image1是文本a的内容的图像展示，Image2和Image3是与文本b的内容的图像展示。
        
        2. 在生成答案时，如果引用了某段原始文本的内容，应将与此原始文本相关的所有图像按原文的逻辑顺序插入到此段文本的后面。如果你生成的某段答案引用了多个原始文本段落的内容，则将这些文本相关的所有图像按照原文的逻辑顺序依次插入到文本的后面。
    
        image按如下md格式输出：           
        [![Alt Text](Image Src)](Page Url)
        
        3. 在 "Answer" 的末尾，请列出引用的所有页面的Page Url和Title以供用户参考原始文档。最后写出一句话总结。

        Question: 
        {question}

        Context: 
        {context}

        Answer:
        """

        prompt_game_quick = ChatPromptTemplate.from_template(prompt_quick)

        chain_game_text_image_together = (
            prompt_game_quick
            | mmgamequickllm
            | StrOutputParser()
        )


        context_q = get_context() # Get the context from the HTML files
        result_game_text_image = chain_game_text_image_together.invoke({
            "question": user_q, 
            "context": context_q
        })
        return result_game_text_image
    except Exception as e:
        log_message(f"Error processing prompt: {user_q}, Error: {e}")
        return None

def get_context(directory="quicksearch_cache/rawdata"):
    """
    Searches for all HTML files in the specified directory, reads their content,
    adds a sequence number and a newline to each file's content, and concatenates
    them into a single string assigned to the variable context_q.

    Parameters:
        directory (str): The directory to search for HTML files. Defaults to "quicksearch_cache/rawdata".

    Returns:
        str: The concatenated content from all HTML files with added sequence numbers and newlines.
    """
    context_q = ""
    file_index = 1

    # Iterate over all files in the specified directory
    for filename in os.listdir(directory):
        # Check if the file has an HTML extension
        if filename.endswith(".html"):
            file_path = os.path.join(directory, filename)
            try:
                # Open and read the content of the HTML file
                with open(file_path, 'r', encoding="utf-8") as file:
                    file_content = file.read()
                    # Append the file content with the sequence number and a newline
                    context_q += f"\n\n网页{file_index}: \n{file_content}\n"
                    file_index += 1
            except Exception as e:
                # Log or handle any exceptions during file reading
                log_message(f"Error reading file {filename}: {e}")

    return context_q

# @st.cache_data
def llm_chatbot_quick(user_q, chathistory=""):
    """
    Function to query the LLM with user prompts.
    """
    try:
        # Parallel processing of web scraping

        log_message("Starting getting the related page links")
        search_links = fetch_links_with_keyword(user_q)
        log_message(search_links)

        with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
            list(tqdm(pool.imap(process_url, search_links), total=len(search_links)))
        log_message("Completed web scraping process")    

        # user_q = "告诉我第一回-苍狼林的攻略"
        log_message(f"⭐️2. Sending prompt to LLM: {user_q}")
        response = llm_agent(user_q)

        if response:
            log_message(f"⭐️3. LLM response received: \n {response[:20]}")
            return response
        else:
            log_message("No response received from LLM")
            return "No response received from LLM"
    except Exception as e:
        log_message(f"Error querying LLM: {e}")
    

# Transfer image URL to base64, only for Gamerkey, because Streamlit can't display images from it.
def msg_imgurl_to_base64_quick(msg):
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
            filename_safe_url = 'quicksearch_cache/rawdata/img/' + filename_safe_url
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


def extract_content_with_delimiter(raw_text, delimiter):
    """
    Extracts content between specified delimiters from the input text.

    :param text: The input text to process.
    :param delimiter: The delimiter for extracting content (e.g., "```").
    :return: Extracted content or a message if no content is found.
    """
    import re
    pattern = re.escape(delimiter) + r'(.*?)' + re.escape(delimiter)
    matches = re.findall(pattern, raw_text, re.DOTALL)
    if matches:
        return "\n".join(matches)
    return f"No content found between delimiter '{delimiter}'."

def fetch_page_title(url):
    """
    Fetches the title of the given webpage URL.

    :param url: The URL of the webpage.
    :return: The title of the webpage or an error message.
    """
    try:
        # Fetch the HTML content of the webpage
        response = requests.get(url, timeout=1)  # Set a timeout to avoid hanging
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the HTML content
        tree = html.fromstring(response.content)

        # Extract the title using XPath
        title = tree.xpath('//title/text()')
        if title:
            return title[0].strip()  # Return the stripped title
        else:
            return "No title found"

    except requests.RequestException as e:
        return f"Request failed: {e}"
    except Exception as e:
        return f"Error processing URL: {e}"



## Agent Start############################################################
websense_agent_instructions = f"根据用户问题和网页标题，如果有相同的关键字，则返回True，否则返回False。"
websense_llm = ChatOpenAI(name="websense_llm", model_name="gpt-4o-mini", streaming=True)
websense_agent = AgentX(name="websense_agent",llm=websense_llm, instructions=websense_agent_instructions)
datafetch_llm = ChatOpenAI(name="datafetch_llm", model_name="gpt-4o-mini", streaming=True)
datafetch_agent = AgentX(name="datafetch_agent", llm=datafetch_llm)

# Update the websense_agent instructions with the user question and the current link title
fusionbot_agent_instructions = """你是《黑神话：悟空》这款游戏的AI攻略助手，根据用户问题和提供的网页内容为玩家生成详尽的图文并茂的游戏攻略.
    请注意以下规则：
    1. 在网页内容中有若干个页面，每个页面都包含有Page Url，Title，文本内容和以<img>标签表示的图片。例如：

    (Page_Url):
    Title:
    文本a
    Image1
    文本b
    Image2
    Image3
    文本c
    ...

    一般来说，Image1是文本a的内容的图像展示，Image2和Image3是与文本b的内容的图像展示。
    
    2. image要按如下md格式输出：

    [![Alt Text](Image Src)](Page_Url)

    例如，[![图片说明](https://www.xyz.com/img1.jpg)](https://www.xyz.com)

    3. 攻略的结构应该按照 

    - 详细描述最相关的1-2个网页内容（尽可能完整的保留原网页的文本内容和其展示的image，将image按其原文的逻辑顺序插入到文本中间）
    - 总结和列出提供的所有网页的内容点，并分别给出网页的链接和title
    - 最后写出一句话总结。
    """


fusionbot_llm = ChatOpenAI(name="fusionbot_llm", model_name="gpt-4o", streaming=True)
fusionbot_agent = AgentX(name="fusionbot_agent", llm=fusionbot_llm, instructions=fusionbot_agent_instructions)



def agent_flow(user_q):
    """
    Main agent flow function. Fetches search links, evaluates their relevance, 
    and processes the relevant links based on the user query.
    """
    log_message("Get related page links...")
    shared_flow_state_str.value = "⭐️Getting related page links..."  # Updata flow state in the flask and then UI
    
    # Fetch links containing the user query keyword
    search_links = fetch_links_with_keyword(user_q)
    log_message(f"Fetched links: {search_links}")

    shared_flow_state_str.value = "⭐️Analyzing related pages with WebSense agent..."  # Updata flow state in the flask and then UI
    # Iterate through each link and fetch its title
    relevant_links = []
    for link in search_links:
        # Fetch the page title
        title = fetch_page_title(link)
        if not title or "Request failed" in title or "Error processing" in title:
            log_message(f"Failed to fetch title for link: {link}")
            continue  # Skip this link if title fetch fails

        # Use the agent to evaluate relevance
        is_relevant = websense_agent.generate_response(f"问题是 {user_q}, 网页标题是 {title}")
        if is_relevant.strip().lower() == "true":
            log_message(f"{websense_agent.name}: Relevant link found: {link} (Title: {title})")
            relevant_links.append(link)
        else:
            log_message(f"{websense_agent.name}: Irrelevant link skipped: {link} (Title: {title})")

    log_message(f"Relevant links: {relevant_links}")

    shared_flow_state_str.value = "⭐️Processing related page..."  # Updata flow state in the flask and then UI

    # Check if the directory exists
    if os.path.exists("quicksearch_cache"):
        # Remove all files in the directory
        shutil.rmtree("quicksearch_cache")
        # Recreate the empty directory
        os.makedirs("quicksearch_cache")
        os.makedirs("quicksearch_cache/rawdata")

    # mc(y)

    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        list(tqdm(pool.imap(process_url, relevant_links), total=len(relevant_links)))
    log_message("Completed web scraping process")    


    shared_flow_state_str.value = "⭐️Considering the answer with FusionBot agent..."  # Updata flow state in the flask and then UI

    context_q = get_context() # Get the context from the HTML files
    
    # Get the answer with images from the FusionBot agent
    answer_with_image = fusionbot_agent.stream_response(f"用户问题是 {user_q} ， 网页内容是\n {context_q}")

    return answer_with_image
     

## Agent End###############################################################




def main():
    """
    Main function to coordinate the web scraping, database building, and LLM querying processes.
    """

    pass

    
if __name__ == "__main__":
    try:
        # main()
        # fetch_links_with_keyword('金池')
        pass
        
    except KeyboardInterrupt:
        log_message("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        log_message(f"Unexpected error in main execution: {e}")
        sys.exit(1)
