from dotenv import load_dotenv,find_dotenv
from langchain_openai import ChatOpenAI 
import multiprocessing
import time
import sys
import os

load_dotenv(find_dotenv()) 

# Import all functions and variables from logger
from userlib.user_logger import *

def call_openai_api(prompt):
    """
    Function to call OpenAI API with the given prompt
    """
    try:
        # Record the start time
        start_time = time.time()
        log_message(f"API start_time: {start_time:.2f} seconds.")

        # Initialize the OpenAI model
        llm = ChatOpenAI(name="only4maxstest", model="gpt-4o-mini")

        # Call the API with the prompt
        response = llm.invoke(prompt)

        # Record the end time
        end_time = time.time()

        # Calculate the elapsed time
        elapsed_time = end_time - start_time
        log_message(f"API call for prompt '{prompt}' took {elapsed_time:.2f} seconds.")

        return response
    except Exception as e:
        # Handle exceptions and log errors
        log_message(f"Error processing prompt: {prompt}, Error: {e}")
        return None

def scrawl_webpages(page_url):
    """
    Function to process multiple prompts using multiprocessing
    """
    # Create a pool of processes, limiting to cpu_count() - 1
    with multiprocessing.Pool(processes=max(1, multiprocessing.cpu_count() - 1)) as pool:
        # Map the function to the list of prompts
        results = pool.map(call_openai_api, prompts)
    
    return results

if __name__ == "__main__":
    log_message(f"<----------------")


    # Call the process_prompts function with a rate limit
    responses = []
    for i in range(0, len(prompts), 4):  # Process 2 prompts at a time
        batch = prompts[i:i + 4]
        responses.extend(process_prompts(batch))


    # Print the responses
    for i, response in enumerate(responses):
        log_message(f"Response {i+1}: {response}")

    log_message(f"---------------->")
