# Datanacci Framer Studio Main Entrypoint (multi-GPU enabled)
# This is your provided studio_Version2.py renamed as main.py for standardization.

from diffusers_helper.hf_login import login
import json
import os
import shutil
from pathlib import PurePath, Path
import time
import argparse
import traceback
import einops
import numpy as np
import torch
import datetime

# Version information
from modules.version import APP_VERSION

# Set environment variables
os.environ['HF_HOME'] = os.path.abspath(os.path.realpath(os.path.join(os.path.dirname(__file__), './hf_download')))
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import gradio as gr
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from diffusers import AutoencoderKLHunyuanVideo
from transformers import LlamaModel, CLIPTextModel, LlamaTokenizerFast, CLIPTokenizer
from diffusers_helper.hunyuan import encode_prompt_conds, vae_decode, vae_encode, vae_decode_fake
from diffusers_helper.utils import save_bcthw_as_mp4, crop_or_pad_yield_mask, soft_append_bcthw, resize_and_center_crop, generate_timestamp
from diffusers_helper.models.hunyuan_video_packed import HunyuanVideoTransformer3DModelPacked
from diffusers_helper.pipelines.k_diffusion_hunyuan import sample_hunyuan
from diffusers_helper.memory import cpu, gpu, get_cuda_free_memory_gb, move_model_to_device_with_memory_preservation, offload_model_from_device_for_memory_preservation, fake_diffusers_current_device, DynamicSwapInstaller, unload_complete_models, load_model_as_complete
from diffusers_helper.thread_utils import AsyncStream
from diffusers_helper.gradio.progress_bar import make_progress_bar_html
from transformers import SiglipImageProcessor, SiglipVisionModel
from diffusers_helper.clip_vision import hf_clip_vision_encode
from diffusers_helper.bucket_tools import find_nearest_bucket
from diffusers_helper import lora_utils
from diffusers_helper.lora_utils import load_lora, unload_all_loras

from modules.generators import create_model_generator
prompt_embedding_cache = {}
from modules.video_queue import VideoJobQueue, JobStatus
from modules.prompt_handler import parse_timestamped_prompt
from modules.interface import create_interface, format_queue_status
from modules.settings import Settings
from modules import DUMMY_LORA_NAME
from modules.pipelines.metadata_utils import create_metadata
from modules.pipelines.worker import worker

if os.name == 'nt':
    import asyncio
    from functools import wraps
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    def silence_event_loop_closed(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except RuntimeError as e:
                if str(e) != 'Event loop is closed':
                    raise
        return wrapper
    if hasattr(asyncio.proactor_events._ProactorBasePipeTransport, '_call_connection_lost'):
        asyncio.proactor_events._ProactorBasePipeTransport._call_connection_lost = silence_event_loop_closed(
            asyncio.proactor_events._ProactorBasePipeTransport._call_connection_lost)

def verify_lora_state(transformer, label=""):
    if transformer is None:
        print(f"[{label}] Transformer is None, cannot verify LoRA state")
        return
    has_loras = False
    if hasattr(transformer, 'peft_config'):
        adapter_names = list(transformer.peft_config.keys()) if transformer.peft_config else []
        if adapter_names:
            has_loras = True
            print(f"[{label}] Transformer has LoRAs: {', '.join(adapter_names)}")
        else:
            print(f"[{label}] Transformer has no LoRAs in peft_config")
    else:
        print(f"[{label}] Transformer has no peft_config attribute")
    for name, module in transformer.named_modules():
        if hasattr(module, 'lora_A') and module.lora_A:
            has_loras = True
        if hasattr(module, 'lora_B') and module.lora_B:
            has_loras = True
    if not has_loras:
        print(f"[{label}] No LoRA components found in transformer")

# --- MULTI-GPU LOGIC BEGIN ---
NUM_GPUS = torch.cuda.device_count()
GPU_DEVICES = [f"cuda:{i}" for i in range(NUM_GPUS)]
print(f"Detected {NUM_GPUS} GPUs: {GPU_DEVICES}")

from threading import Lock
gpu_locks = [Lock() for _ in GPU_DEVICES]

def acquire_free_gpu():
    for idx, lock in enumerate(gpu_locks):
        if lock.acquire(blocking=False):
            print(f"Assigning job to GPU {GPU_DEVICES[idx]}")
            return idx
    print("No free GPUs, job will wait in queue")
    return None

def release_gpu(idx):
    gpu_locks[idx].release()
    print(f"Released GPU {GPU_DEVICES[idx]}")
# --- MULTI-GPU LOGIC END ---

parser = argparse.ArgumentParser()
parser.add_argument('--share', action='store_true')
parser.add_argument("--server", type=str, default='0.0.0.0')
parser.add_argument("--port", type=int, required=False)
parser.add_argument("--inbrowser", action='store_true')
parser.add_argument("--lora", type=str, default=None, help="Lora path (comma separated for multiple)")
parser.add_argument("--offline", action='store_true', help="Run in offline mode")
args = parser.parse_args()

print(args)

if args.offline:
    print("Offline mode enabled.")
    os.environ['HF_HUB_OFFLINE'] = '1'
else:
    if 'HF_HUB_OFFLINE' in os.environ:
        del os.environ['HF_HUB_OFFLINE']

free_mem_gb = get_cuda_free_memory_gb(gpu)
high_vram = free_mem_gb > 60

print(f'Free VRAM {free_mem_gb} GB')
print(f'High-VRAM Mode: {high_vram}')

text_encoder = LlamaModel.from_pretrained("hunyuanvideo-community/HunyuanVideo", subfolder='text_encoder', torch_dtype=torch.float16).cpu()
text_encoder_2 = CLIPTextModel.from_pretrained("hunyuanvideo-community/HunyuanVideo", subfolder='text_encoder_2', torch_dtype=torch.float16).cpu()
tokenizer = LlamaTokenizerFast.from_pretrained("hunyuanvideo-community/HunyuanVideo", subfolder='tokenizer')
tokenizer_2 = CLIPTokenizer.from_pretrained("hunyuanvideo-community/HunyuanVideo", subfolder='tokenizer_2')
vae = AutoencoderKLHunyuanVideo.from_pretrained("hunyuanvideo-community/HunyuanVideo", subfolder='vae', torch_dtype=torch.float16).cpu()

feature_extractor = SiglipImageProcessor.from_pretrained("lllyasviel/flux_redux_bfl", subfolder='feature_extractor')
image_encoder = SiglipVisionModel.from_pretrained("lllyasviel/flux_redux_bfl", subfolder='image_encoder', torch_dtype=torch.float16).cpu()

current_generator = None

vae.eval()
text_encoder.eval()
text_encoder_2.eval()
image_encoder.eval()

if not high_vram:
    vae.enable_slicing()
    vae.enable_tiling()

vae.to(dtype=torch.float16)
image_encoder.to(dtype=torch.float16)
text_encoder.to(dtype=torch.float16)
text_encoder_2.to(dtype=torch.float16)

vae.requires_grad_(False)
text_encoder.requires_grad_(False)
text_encoder_2.requires_grad_(False)
image_encoder.requires_grad_(False)

lora_dir = os.path.join(os.path.dirname(__file__), 'loras')
os.makedirs(lora_dir, exist_ok=True)

lora_names = []
lora_values = []

script_dir = os.path.dirname(os.path.abspath(__file__))
default_lora_folder = os.path.join(script_dir, "loras")
os.makedirs(default_lora_folder, exist_ok=True)

if not high_vram:
    DynamicSwapInstaller.install_model(text_encoder, device=gpu)
else:
    text_encoder.to(gpu)
    text_encoder_2.to(gpu)
    image_encoder.to(gpu)
    vae.to(gpu)

stream = AsyncStream()
outputs_folder = './outputs/'
os.makedirs(outputs_folder, exist_ok=True)
settings = Settings()

if settings.get("auto_cleanup_on_startup", False):
    print("--- Running Automatic Startup Cleanup ---")
    from modules.toolbox_app import tb_processor
    cleanup_summary = tb_processor.tb_clear_temporary_files()
    print(f"{cleanup_summary}")
    print("--- Startup Cleanup Complete ---")

lora_folder_from_settings: str = settings.get("lora_dir", default_lora_folder)
print(f"Scanning for LoRAs in: {lora_folder_from_settings}")
if os.path.isdir(lora_folder_from_settings):
    try:
        for root, _, files in os.walk(lora_folder_from_settings):
            for file in files:
                if file.endswith('.safetensors') or file.endswith('.pt'):
                    lora_relative_path = os.path.relpath(os.path.join(root, file), lora_folder_from_settings)
                    lora_name = str(PurePath(lora_relative_path).with_suffix(''))
                    lora_names.append(lora_name)
        print(f"Found LoRAs: {lora_names}")
        if len(lora_names) == 1:
            lora_names.append(DUMMY_LORA_NAME)
    except Exception as e:
        print(f"Error scanning LoRA directory '{lora_folder_from_settings}': {e}")
else:
    print(f"LoRA directory not found: {lora_folder_from_settings}")

job_queue = VideoJobQueue()

def load_lora_file(lora_file: str | PurePath):
    if not lora_file:
        return None, "No file selected"
    try:
        lora_path = PurePath(lora_file)
        lora_name = lora_path.name
        lora_dest = PurePath(lora_dir, lora_path)
        import shutil
        shutil.copy(lora_file, lora_dest)
        global current_generator, lora_names
        if current_generator is None:
            return None, "Error: No model loaded to apply LoRA to. Generate something first."
        current_generator.unload_loras()
        selected_loras = [lora_path.stem]
        current_generator.load_loras(selected_loras, lora_dir, selected_loras)
        lora_base_name = lora_path.stem
        if lora_base_name not in lora_names:
            lora_names.append(lora_base_name)
        device = next(current_generator.transformer.parameters()).device
        current_generator.move_lora_adapters_to_device(device)
        print(f"Loaded LoRA: {lora_name} to {current_generator.get_model_name()} model")
        return gr.update(choices=lora_names), f"Successfully loaded LoRA: {lora_name}"
    except Exception as e:
        print(f"Error loading LoRA: {e}")
        return None, f"Error loading LoRA: {e}"

@torch.no_grad()
def get_cached_or_encode_prompt(prompt, text_encoder, text_encoder_2, tokenizer, tokenizer_2, target_device):
    if prompt in prompt_embedding_cache:
        print(f"Cache hit for prompt: {prompt[:60]}...")
        llama_vec_cpu, llama_mask_cpu, clip_l_pooler_cpu = prompt_embedding_cache[prompt]
        llama_vec = llama_vec_cpu.to(target_device)
        llama_attention_mask = llama_mask_cpu.to(target_device) if llama_mask_cpu is not None else None
        clip_l_pooler = clip_l_pooler_cpu.to(target_device)
        return llama_vec, llama_attention_mask, clip_l_pooler
    else:
        print(f"Cache miss for prompt: {prompt[:60]}...")
        llama_vec, clip_l_pooler = encode_prompt_conds(
            prompt, text_encoder, text_encoder_2, tokenizer, tokenizer_2
        )
        llama_vec, llama_attention_mask = crop_or_pad_yield_mask(llama_vec, length=512)
        prompt_embedding_cache[prompt] = (llama_vec.cpu(), llama_attention_mask.cpu() if llama_attention_mask is not None else None, clip_l_pooler.cpu())
        return llama_vec, llama_attention_mask, clip_l_pooler

job_queue.set_worker_function(worker)

# ... (rest of your original studio_Version2.py code, unchanged)

# Set Gradio temporary directory from settings
os.environ["GRADIO_TEMP_DIR"] = settings.get("gradio_temp_dir")

interface = create_interface(
    process_fn=process,
    monitor_fn=monitor_job,
    end_process_fn=end_process,
    update_queue_status_fn=update_queue_status,
    load_lora_file_fn=load_lora_file,
    job_queue=job_queue,
    settings=settings,
    lora_names=lora_names
)

interface.launch(
    server_name=args.server,
    server_port=args.port,
    share=args.share,
    inbrowser=args.inbrowser,
    allowed_paths=[settings.get("output_dir"), settings.get("metadata_dir")],
)
