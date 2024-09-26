import os
# from guidance import models, gen

current_dir = os.path.dirname(__file__)
tokenizer_path = os.path.join(current_dir, "tokenizer")

model = None


def load_model():
    global model
    if model is None:
        model = models.LlamaCpp(
            "/Users/peter/Projects/FedeTest/EmeraldFundLLama.Q4_K_M.gguf",
            n_ctx=8192,
            n_gpu_layers=-1,
            echo=False,
        )


def create_signal_processor(features: str):
    load_model()
    start_header = f"<|start_header_id|>user<|end_header_id|>Create a SignalProcessor with the following features: {features}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
    source_start = "import pandas as pd\nimport numpy as np\nimport pandas_ta as ta\nclass SignalProcessor:\n"
    result = model.stream() + start_header + source_start
    result = result + gen(
        name="answer",
        stop_regex=r"( |\t)+return (\w+\n)",
        save_stop_text="return_part",
        max_tokens=1024,
    )
    last_taken = len(start_header)
    for chunk in result:
        if chunk.get("return_part") is not None:
            yield "\n" + chunk.get("return_part")
            break
        if len(chunk) > last_taken:
            yield str(chunk)[last_taken:]
            last_taken = len(str(chunk))


if __name__ == "__main__":
    # Test AI
    response = create_signal_processor("Buy when SMA-10 crosses SMA-50, sell otherwise")
    for r in response:
        print(r, end="")
