from flask import Flask, render_template, request, jsonify
from flask import Response, stream_with_context
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import markdown2

from mmgamer_quicksearch import *
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

extra_files = os.environ.get("FLASK_RUN_EXTRA_FILES")
print(f"Extra files to watch: {extra_files}")

# Load tokenizer and model
# tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-medium")
# model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-medium")

app = Flask(__name__)

@app.route("/")
def index():
    return render_template('chat.html')

@app.route("/get", methods=["GET", "POST"])
def chat():
    msg = request.form["msg"]
    input = msg
    return get_Chat_response(input)


@app.route("/stream", methods=["GET"])
def stream():
    msg = request.args.get("msg")
    return Response(stream_with_context(generate_response_stream(msg)), mimetype="text/event-stream")

def generate_response_stream(user_q):
    try:
        # Simulate streaming data generation
        # for chunk in llm_groq_agent(user_q):
        resp = llm_groq_agent(user_q)
        print(resp)
        for chunk in resp:
            # Replace each newline in the chunk with "\ndata:" to ensure proper SSE formatting
            formatted_chunk = chunk.replace("\n", "\ndata: ")
            yield f"data: {formatted_chunk}\n\n"
            time.sleep(0.002)
        yield "data: [END]\n\n"  # Signify the end of the stream
    except Exception as e:
        yield f"data: Error: {str(e)}\n\n"





def get_Chat_response(text):
    # # Let's chat for 5 lines
    # for step in range(5):
    #     # encode the new user input, add the eos_token and return a tensor in Pytorch
    #     new_user_input_ids = tokenizer.encode(str(text) + tokenizer.eos_token, return_tensors='pt')
    #     # append the new user input tokens to the chat history
    #     bot_input_ids = torch.cat([chat_history_ids, new_user_input_ids], dim=-1) if step > 0 else new_user_input_ids
    #     # generate a response while limiting the total chat history to 1000 tokens
    #     chat_history_ids = model.generate(bot_input_ids, max_length=1000, pad_token_id=tokenizer.eos_token_id)
    #     # return the last output tokens from bot
    #     return tokenizer.decode(chat_history_ids[:, bot_input_ids.shape[-1]:][0], skip_special_tokens=True)
    # return llm_groq_agent(text)
    # return "ddd"

    resp=llm_groq_agent(text)

    # chat_history = ""
    # resp=llm_chatbot_quick(text, chat_history)
    print(resp)
    for chunk in resp:
        print(chunk)
        yield chunk


# Define route to convert markdown to HTML
@app.route('/convert_markdown', methods=['POST'])
def convert_markdown():
    data = request.get_json()
    markdown_text = data.get("markdown", "")
    html_content = markdown2.markdown(markdown_text)
    # print("-------md")
    # print(markdown_text)
    # print("-------html")
    # print(html_content)
    return jsonify(html_content)


# New route to return "good night" for the button click
@app.route("/get_goodnight", methods=["POST"])
def get_good_night():
    return jsonify({"response": "good night!"})

if __name__ == '__main__':
    app.run(debug=True)













# from langchain.schema import AIMessage, HumanMessage, SystemMessage
# # Initialize Gemini AI Studio chat model
# llm = ChatAnthropic(model='claude-3-haiku-20240307', streaming=True)



# def stream_response(message, history):
#     print(f"Input: {message}. History: {history}\n")

#     history_langchain_format = []
#     history_langchain_format.append(SystemMessage(content=system_message))

#     for human, ai in history:
#         history_langchain_format.append(HumanMessage(content=human))
#         history_langchain_format.append(AIMessage(content=ai))

#     if message is not None:
#         history_langchain_format.append(HumanMessage(content=message))
#         partial_message = ""
#         for response in llm.stream(history_langchain_format):
#             partial_message += response.content
#             yield partial_message


# please make sure to properly style your response using Github Flavored Markdown. Use markdown syntax for things like headings, lists, colored text, code blocks, highlights etc. Make sure not to mention markdown or styling in your actual response"
#         }
#     ],