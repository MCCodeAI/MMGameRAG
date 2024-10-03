
import streamlit as st
import time
import random

from mmgamerag import *



with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password")
    "[Get an OpenAI API key](https://platform.openai.com/account/api-keys)"
    "[View the source code](https://github.com/MCCodeAI/MMGameRAG)"
    "[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/streamlit/llm-examples?quickstart=1)"
    
    if st.button("Clear Chat"):
        # Clear relevant session state variables here
        if 'messages' in st.session_state:
            del st.session_state['messages']
        st.success("Chat cleared!")



st.title("MMGameRAG🐒🐵🙈🙉🙊🦍🦧⭐️🍌")
st.caption("🚀 Multimodal Retrieval-Augmented Generation System for Game Walkthroughs")
if "messages" not in st.session_state: # Initialize the chat, only run once
    # st.session_state["messages"] = [
    #     {"role": "system", "content": f"你是一个优秀的助手，帮助用户了解黑神话。"},
    #     {"role": "assistant", "content": "How can I help you for Black Myth?"}
    #     ]
    st.session_state["messages"] = [
        ("system", "我是一个图文并茂的多模态游戏攻略高手，帮助用户了解《黑神话悟空》。"),
        ("assistant", "How can I help you for Black Myth?")
        ]
    


for role, content in st.session_state["messages"]:  # Show all except the latest message
    st.chat_message(role).markdown(content, unsafe_allow_html=True)

if prompt := st.chat_input():
    # if not openai_api_key:
    #     st.info("Please add your OpenAI API key to continue.")
    #     st.stop()

    # client = OpenAI(api_key=openai_api_key)
    # st.session_state.messages.append({"role": "user", "content": prompt})
    # st.chat_message("user").write(prompt)
    # response = client.chat.completions.create(model="gpt-4o-mini", messages=st.session_state.messages)
    # msg = response.choices[0].message.content
    # st.session_state.messages.append({"role": "assistant", "content": msg})
    # st.chat_message("assistant").write(msg)

    
    # client = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    st.session_state["messages"].append(("user", prompt))
    st.chat_message("user").write(prompt, unsafe_allow_html=True)


    # # 创建占位符
    # placeholder = st.empty()

    # # 进行倒计时
    # for seconds_remaining in range(10, 0, -1):
    #     placeholder.markdown(f"**Countdown: {seconds_remaining} seconds remaining**", unsafe_allow_html=True)
    #     time.sleep(1)

    # # 倒计时结束后的消息
    # placeholder.markdown("**Countdown complete!**", unsafe_allow_html=True)
    
    # 创建一个占位符

    placeholder = st.empty()
    gif_index = random.randint(0, 1)  # 随机选择从0到1的整数
    gif_path = f"monkeying{gif_index}.gif"  # 生成对应的GIF文件路径
    # 在占位符中显示文字
    # placeholder.text("攻略搜索中...")
    placeholder.image(f"docs/uidata/{gif_path}", caption="攻略搜索中...")


    # # 等待2秒
    # time.sleep(0.5)

    

    # response = client(st.session_state["messages"])

    response = llm_chatbot(prompt,st.session_state["messages"])
    print('\n---------\n')
    print(response + '\n---------\n')
    msg = response
    msg_base64 = msg_imgurl_to_base64(msg)

    # print('\n-----msg_base64----\n')
    # print(msg_base64 + '\n---------\n')

    # st.chat_message("assistant").write_stream(llm_chatbot(prompt,st.session_state["messages"])) 

    st.chat_message("assistant").write(msg_base64, unsafe_allow_html=True) 
    # 清空占位符
    placeholder.empty()

    st.session_state["messages"].append(("assistant", msg_base64))
    


   


 
