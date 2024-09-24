
import streamlit as st

from langchain_openai import ChatOpenAI
# from langchain_community.chat_models import ChatOpenAI

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


st.title("💬 MMGameRAG")
st.caption("🚀 Multimodal Retrieval-Augmented Generation System for Game Walkthroughs")
if "messages" not in st.session_state: # Initialize the chat, only run once
    # st.session_state["messages"] = [
    #     {"role": "system", "content": f"你是一个优秀的助手，帮助用户了解黑神话。"},
    #     {"role": "assistant", "content": "How can I help you for Black Myth?"}
    #     ]
    st.session_state["messages"] = [
        ("system", "我是一个图文并茂的多模态游戏攻略高手，帮助用户了解黑神话悟空。"),
        ("assistant", "How can I help you for Black Myth?")
        ]
    


for role, content in st.session_state["messages"]:
    st.chat_message(role).write(content)

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
    st.chat_message("user").write(prompt)

    # response = client(st.session_state["messages"])
    # response = llm_chatbot(prompt,st.session_state["messages"])
    # print('\n---------\n')
    # print(response + '\n---------\n')
    # msg = response
    # st.session_state["messages"].append(("assistant", msg))
    # st.markdown(msg, unsafe_allow_html=True)
    # st.chat_message("assistant").write(msg)

    # image_url = "https://img1.gamersky.com/image2024/08/20240819_qy_372_15/image011_S.jpg"
    # msg = f'<img src="{image_url}">'
    # st.chat_message("assistant").write(msg, unsafe_allow_html=True)

    # # image_url = "https://img1.gamersky.com/upimg/pic/2024/09/22/small_202409220914312718.webp"
    # image_url = "https://img1.gamersky.com/image2024/08/20240819_qy_372_15/image011_S.jpg"
    # st.chat_message("assistant").markdown(f"![Image]({image_url})")

    # image_url = "https://img1.gamersky.com/image2024/08/20240819_qy_372_15/image011_S.jpg"
    # st.image(image_url, caption="GamerSky Image")

    # cors_proxy_url = "https://cors-anywhere.herokuapp.com/"
    # image_url = f"{cors_proxy_url}https://img1.gamersky.com/image2024/08/20240819_qy_372_15/image011_S.jpg"
    # st.image(image_url)

    # display(Markdown(msg))
    # st.chat_message("assistant").markdown(msg, unsafe_allow_html=True)

    # image_url = "file://docs/rawdata/img/image011_S.jpg"
    # st.markdown(f"![Image]({image_url})", unsafe_allow_html=True)

    from PIL import Image
    # 本地图片路径
    image_path = "docs/rawdata/img/image011_S.jpg"  # 替换为你的本地图片路径

    # 加载并显示本地图像
    image = Image.open(image_path)
    st.image(image, caption="Local Image", use_column_width=True)

    # import streamlit as st
    # import base64

    # # 本地图片路径
    # # image_path = "docs/rawdata/img/image011_S.jpg"  # 替换为你的本地图片路径

    # # 将图像转换为 base64 编码
    # with open(image_url, "rb") as image_file:
    #     encoded_image = base64.b64encode(image_file.read()).decode()

    # # 使用 Markdown 显示本地图像
    # st.markdown(f'<img src="data:image/jpeg;base64,{encoded_image}" alt="Image" style="width:100%;">', unsafe_allow_html=True)

    # import base64
    # import urllib.request

    # # 输入图片的 URL
    # image_url = "https://img1.gamersky.com/image2024/08/20240819_qy_372_15/image011_S.jpg"

    # # 从 URL 获取图像并转换为 Base64
    # with urllib.request.urlopen(image_url) as response:
    #     image_data = response.read()
    #     image_base64 = base64.b64encode(image_data).decode()

    # # 构造 HTML img 标签
    # img_tag = f'<img src="data:image/jpeg;base64,{image_base64}" alt="Image">'
    # st.markdown(img_tag, unsafe_allow_html=True)



    # import streamlit as st

    # # 输入图片的 URL
    # image_url = "https://img1.gamersky.com/image2024/08/20240819_qy_372_15/image011_S.jpg"

    # # 使用 st.image 显示图像
    # st.image(image_url, caption="Image from URL", use_column_width=True)