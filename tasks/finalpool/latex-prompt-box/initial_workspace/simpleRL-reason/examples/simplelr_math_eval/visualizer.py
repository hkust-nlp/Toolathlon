import gradio as gr
import json
import os
from difflib import Differ
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--data_dir", type=str, default="")
parser.add_argument("--run_name", type=str, default="verl-grpo-fix-ray_temp1.0_Qwen2.5-32B_simplelr_math_35")
parser.add_argument("--checkpoint_prefix", type=str, default="global_step_")
parser.add_argument("--temperature", type=str, default="0.0")
args = parser.parse_args()

# Configuration
DATA_DIR = args.data_dir
DATA_DIR = os.path.join(DATA_DIR, args.run_name) if "/" in args.run_name else os.path.join(DATA_DIR, args.run_name, "eval_results")
CHECKPOINT_PREFIX = args.checkpoint_prefix
TEMPERATURE = args.temperature

def get_available_datasets():
    """Find all unique dataset names across all checkpoints"""
    datasets = set()
    for checkpoint in os.listdir(DATA_DIR):
        if checkpoint.startswith(CHECKPOINT_PREFIX):
            checkpoint_path = os.path.join(DATA_DIR, checkpoint)
            if os.path.isdir(checkpoint_path):
                datasets.update(d for d in os.listdir(checkpoint_path))
    return sorted(datasets)

def get_checkpoints():
    """Get sorted list of checkpoints based on step number"""
    checkpoints = []
    for dir_name in os.listdir(DATA_DIR):
        if dir_name.startswith(CHECKPOINT_PREFIX):
            try:
                step = int(dir_name.split("_")[-1])
                checkpoints.append((step, dir_name))
            except ValueError:
                continue
    checkpoints.sort(key=lambda x: x[0])
    return [c[1] for c in checkpoints]

def load_responses(checkpoint, dataset):
    """Load responses for a specific checkpoint and dataset"""
    checkpoint_path = os.path.join(DATA_DIR, checkpoint, dataset)
    responses = []
    
    # Find first JSONL file in the directory
    jsonl_files = [f for f in os.listdir(checkpoint_path) if f.endswith(".jsonl") and f"_t{TEMPERATURE}" in f]
    if not jsonl_files:
        return []
    
    with open(os.path.join(checkpoint_path, jsonl_files[0])) as f:
        for line in f:
            data = json.loads(line)
            responses.append({
                "idx": data["idx"],
                "input": data["question"],
                "pred": data["code"][0],  # Assuming single prediction per example
                "score": data["score"][0],
                "stop_reason": data["finish_reason"][0]  # Add stop reason
            })
    
    # Sort by index to ensure alignment between checkpoints
    responses.sort(key=lambda x: x["idx"])
    return responses

def generate_diff(old_text, new_text):
    """Generate HTML diff between two prediction texts"""
    d = Differ()
    diff = list(d.compare(str(old_text).splitlines(), str(new_text).splitlines()))
    
    html = []
    for line in diff:
        if line.startswith('+ '):
            html.append(f'<span style="color: green; background-color: #e6ffe6;">{line[2:]}</span><br>')
        elif line.startswith('- '):
            html.append(f'<span style="color: red; background-color: #ffe6e6;">{line[2:]}</span><br>')
        elif line.startswith('? '):
            continue
        else:
            html.append(f"{line[2:]}<br>")
    return "".join(html)

def update_responses(dataset, checkpoint_a, checkpoint_b, index):
    """Update displayed responses based on selections"""
    responses_a = load_responses(checkpoint_a, dataset)
    responses_b = load_responses(checkpoint_b, dataset)
    
    if not responses_a or not responses_b:
        return [gr.update()]*6 + [gr.Slider(maximum=0)]  # Updated number of returns
    
    index = min(index, len(responses_a)-1, len(responses_b)-1)
    example_a = responses_a[index]
    example_b = responses_b[index]
    
    diff_html = generate_diff(example_a["pred"], example_b["pred"])
    
    # Create info strings for both responses
    info_a = f"Stop Reason: {example_a['stop_reason']} | Correctness: {example_a['score']}"
    info_b = f"Stop Reason: {example_b['stop_reason']} | Correctness: {example_b['score']}"
    
    return [
        example_a["input"],
        example_a["pred"],
        example_b["pred"],
        info_a,
        info_b,
        diff_html,
        gr.Slider(maximum=len(responses_a)-1)
    ]

with gr.Blocks(title="Model Checkpoint Comparator") as demo:
    gr.Markdown("# 🔄 Model Checkpoint Response Comparator")
    gr.Markdown(f"The prediction results of {DATA_DIR}")
    gr.Markdown("""
    1. Select a dataset from the dropdown.
    2. Select two checkpoints from the dropdowns.
    3. Adjust the example index slider to view different examples.
    4. The input question, predictions, and differences will be displayed.
    """)
    
    with gr.Row():
        dataset_dropdown = gr.Dropdown(
            label="Select Dataset",
            choices=get_available_datasets(),
            interactive=True
        )
        
    with gr.Row():
        checkpoint_a = gr.Dropdown(
            label="Earlier Checkpoint",
            choices=get_checkpoints(),
            interactive=True
        )
        checkpoint_b = gr.Dropdown(
            label="Later Checkpoint",
            choices=get_checkpoints(),
            interactive=True
        )
    
    example_slider = gr.Slider(
        minimum=0,
        maximum=0,
        step=1,
        label="Example Index",
        interactive=True
    )
    
    input_text = gr.Textbox(label="Input Question", interactive=False)
    
    with gr.Row():
        pred_a = gr.Textbox(label="Earlier Checkpoint Prediction", interactive=False)
        pred_b = gr.Textbox(label="Later Checkpoint Prediction", interactive=False)
    
    with gr.Row():
        info_a = gr.Textbox(label="Earlier Checkpoint Info", interactive=False)
        info_b = gr.Textbox(label="Later Checkpoint Info", interactive=False)
    
    diff_display = gr.HTML(label="Prediction Differences")
    
    # Event handlers
    for component in [dataset_dropdown, checkpoint_a, checkpoint_b]:
        component.change(
            update_responses,
            inputs=[dataset_dropdown, checkpoint_a, checkpoint_b, example_slider],
            outputs=[input_text, pred_a, pred_b, info_a, info_b, diff_display, example_slider]
        )
    
    example_slider.change(
        update_responses,
        inputs=[dataset_dropdown, checkpoint_a, checkpoint_b, example_slider],
        outputs=[input_text, pred_a, pred_b, info_a, info_b, diff_display]
    )

if __name__ == "__main__":
    demo.launch(share=True,
                debug=False)