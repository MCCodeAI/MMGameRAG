import time
import gradio as gr
import random

# 定义逐字输出的函数
def slow_echo(message, history):
    """
    Slowly echoes each character of the message with a delay
    """
    for i in range(len(message)):
        time.sleep(0.05)
        yield "You typed: " + message[: i + 1]

# 定义显示输入框值的函数
def display_input_text(input_text):
    """
    Displays the input text in the output label
    """
    return f"You entered: {input_text}"

# JavaScript 脚本，用于将数据传递到指定的输入框并触发 Gradio 组件更新
shortcut_js = """
<script>
    function shortcuts(event) {
        // Verify the message origin for security
        if (event.origin !== "http://127.0.0.1:5500") return;

        // Display the received data in the console
        const data = event.data;
        console.log("Received data from vis:", data);

</script>
"""

def random_response(message, history):
    return random.choice(["Yes", "No"])

# 使用 Blocks 组合 ChatInterface，并添加 JavaScript
with gr.Blocks(js=shortcut_js) as demo:
    # gr.HTML(shortcut_js)  # 插入自定义 JavaScript
    gr.Markdown("## Chat with Random Response Bot")  # ChatInterface 标题
    chat_interface = gr.ChatInterface(slow_echo, type="messages")  # ChatInterface

# 启动应用
if __name__ == "__main__":
    demo.launch()
