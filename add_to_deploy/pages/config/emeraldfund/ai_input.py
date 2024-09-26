import streamlit as st
from frontend.pages.config.emeraldfund.ai import create_signal_processor


def ai_input():
    st.write(
        "## Coming soon!\nSubscribe to my Patreon to get exclusive early access to my content including the AI Assistant! https://www.patreon.com/emerald_show"
    )
    # Create a text input field for the user to enter their prompt
    prompt_input = st.text_input(
        "Enter your prompt (Example: buy when SMA-20 crosses SMA-10):", value=""
    )

    # Create a button to run the AI assistant
    run_button = st.button("Run AI Assistant", disabled=True)

    # Create a placeholder to display the AI assistant's response
    response_placeholder = st.empty()

    # Run the AI assistant when the button is clicked
    if run_button:
        prompt = prompt_input.strip()
        if prompt:
            response = create_signal_processor(prompt)
            chunks = ""
            for chunk in response:
                chunks += chunk
                response_placeholder.markdown(f"```py\n{chunks}\n```")
        else:
            response_placeholder.write("Please enter a prompt.")
    return
