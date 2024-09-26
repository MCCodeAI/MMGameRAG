import panel as pn
from langchain.llms import OpenAI
from panel.io.state import state

# Initialize Panel
pn.extension()

# Initialize LLM with OpenAI and temperature setting
llm = OpenAI(temperature=0)

# Define callback function with error handling
def callback(contents, instance):
    try:
        # Safely handle the callback with Panel's LangChain integration
        callback_handler = pn.chat.langchain.PanelCallbackHandler(instance)
        # return llm.predict(contents, callbacks=[callback_handler])
        return contents
    except RecursionError as e:
        # Catch recursion errors to avoid infinite loops
        return f"Error: {str(e)}"



# Set up the ChatInterface using the callback function
pn.chat.ChatInterface(callback=callback).servable()
