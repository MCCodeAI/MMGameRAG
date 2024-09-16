# Muliti-modal RAG system for game strategies, starting with Black myth - Wukong. 
import re
import time

from bs4 import BeautifulSoup
from langchain_community.document_loaders import RecursiveUrlLoader



def bs4_extractor(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    return re.sub(r"\n\n+", "\n\n", soup.text).strip()


loader = RecursiveUrlLoader(
    "https://www.gamersky.com/handbook/76947/",
    # max_depth=2,
    # use_async=False,
    # extractor=bs4_extractor,
    # metadata_extractor=None,
    # exclude_dirs=(),
    # timeout=10,
    # check_response_status=True,
    # continue_on_failure=True,
    # prevent_outside=True,
    # base_url=None,
    # ...
)

def extract_images_with_separate_context(html: str, upper_len: int = 200, lower_len: int = 200) -> list:
    """
    Extracts image URLs and the text before and after each image tag from the HTML.
    
    Args:
        - html: The input HTML string.
        - upper_len: The number of characters to extract before the image tag (upper context).
        - lower_len: The number of characters to extract after the image tag (lower context).
    
    Returns:
        A list of dictionaries containing the image URL and its corresponding upper and lower context text.
    """
    soup = BeautifulSoup(html, 'lxml')  # Parse the HTML
    images_with_context = []  # List to store image URLs and context

    # Find all <img> tags in the HTML
    for img in soup.find_all('img'):
        img_url = img.get('src')  # Get the 'src' attribute (image URL)
        if img_url:
            # Convert the entire HTML to a string for position tracking
            html_str = str(soup)
            # Find the position of the <img> tag in the HTML string
            img_pos = html_str.find(str(img))
            
            # Extract upper context (text before the image)
            start_pos = max(0, img_pos - upper_len)  # Ensure no out-of-bound index
            upper_text = html_str[start_pos:img_pos].strip()
            
            # Extract lower context (text after the image)
            end_pos = min(len(html_str), img_pos + len(str(img)) + lower_len)
            lower_text = html_str[img_pos + len(str(img)):end_pos].strip()

            # Debugging print to check if lower_text has content before cleaning
            print(f"Raw lower_text after <img> tag at position {img_pos}: {lower_text}")

            # Clean up the upper and lower context to remove any remaining HTML tags
            upper_soup = BeautifulSoup(upper_text, 'lxml')
            cleaned_upper_text = upper_soup.get_text().strip()
            
            lower_soup = BeautifulSoup(lower_text, 'lxml')
            cleaned_lower_text = lower_soup.get_text().strip()

            # Debugging print to check cleaned lower context
            print(f"Cleaned lower_text for image URL {img_url}: {cleaned_lower_text}")

            # Append the image URL along with its upper and lower context
            images_with_context.append({
                'image_url': img_url,
                'upper_context': cleaned_upper_text,
                'lower_context': cleaned_lower_text
            })
    
    return images_with_context


# Load the HTML content from the RecursiveUrlLoader
docs = loader.load()
# time.sleep(1)
html_content = docs[0].page_content

# Extract image data with upper and lower context
image_data = extract_images_with_separate_context(html_content, upper_len=1000, lower_len=1000)

# Print the extracted image data
print(image_data)
