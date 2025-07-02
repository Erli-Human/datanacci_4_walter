 import os
import torch
import gradio as gr
from multiprocessing import Process, Manager
from modules.interface import create_interface, format_queue_status
from modules.settings import Settings
from modules.pipelines.worker import worker
from modules.video_queue import VideoJobQueue

settings = Settings()

def get_gpu_statistics():
    stats = []
    n_gpus = torch.cuda.device_count()
    for i in range(n_gpus):
        device = f"cuda:{i}"
        props = torch.cuda.get_device_properties(i)
        total_mem = props.total_memory / 1024**3
        reserved = torch.cuda.memory_reserved(i) / 1024**3
        allocated = torch.cuda.memory_allocated(i) / 1024**3
        free = total_mem - reserved
        temp = "-"
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            temp = f"{pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)}°C"
        except Exception:
            temp = "-"
        stats.append({
            "gpu": device,
            "allocated": f"{allocated:.1f} GB",
            "reserved": f"{reserved:.1f} GB",
            "free": f"{free:.1f} GB",
            "total": f"{total_mem:.1f} GB",
            "temp": temp
        })
    return stats

def get_ram_string():
    try:
        import psutil
        mem = psutil.virtual_memory()
        return f"{mem.used / 1024**3:.1f} GB / {mem.total / 1024**3:.1f} GB"
    except ImportError:
        return "psutil not installed"

def format_gpu_statistics_html():
    stats = get_gpu_statistics()
    html = (
        "<b>GPU Statistics:</b><br>"
        "<table style='width:100%; border-collapse:collapse;'>"
        "<tr>"
        "<th>GPU</th>"
        "<th>Allocated</th>"
        "<th>Reserved</th>"
        "<th>Free</th>"
        "<th>Total</th>"
        "<th>Temp</th>"
        "</tr>"
    )
    for idx, s in enumerate(stats):
        html += (
            f"<tr>"
            f"<td>{s['gpu']}</td>"
            f"<td>{s['allocated']}</td>"
            f"<td>{s['reserved']}</td>"
            f"<td>{s['free']}</td>"
            f"<td>{s['total']}</td>"
            f"<td>{s['temp']}</td>"
            f"</tr>"
        )
        if idx == 0:
            html += (
                f"<tr><td></td><td colspan='2'><b>RAM:</b></td><td colspan='3'>{get_ram_string()}</td></tr>"
                f"<tr><td></td><td colspan='2'><b>VRAM:</b></td><td colspan='3'>{s['total']}</td></tr>"
                f"<tr><td></td><td colspan='2'><b>Temperature:</b></td><td colspan='3'>{s['temp']}</td></tr>"
            )
    html += "</table>"
    return html

def update_queue_status(job_queue):
    jobs = job_queue.get_all_jobs()
    queue_html = format_queue_status(jobs)
    gpu_html = format_gpu_statistics_html()
    return f"{gpu_html}<br><br><b>Job Queue:</b><br>{queue_html}"

def monitor_job(job_queue, *args, **kwargs):
    return update_queue_status(job_queue)

def end_process(job_queue, *args, **kwargs):
    return update_queue_status(job_queue)

# Multi-GPU queue worker logic
def queue_worker_loop(gpu_id, job_queue):
    import time
    torch.cuda.set_device(gpu_id)
    while True:
        job = job_queue.get_next_job()
        if job is None:
            time.sleep(0.1)
            continue
        try:
            if isinstance(job, dict):
                try:
                    worker(**job, gpu_id=gpu_id)
                except TypeError:
                    worker(**job)
            else:
                try:
                    worker(job, gpu_id=gpu_id)
                except TypeError:
                    worker(job)
        except Exception as e:
            print(f"Worker on GPU {gpu_id} failed: {e}")

def start_workers(num_gpus, job_queue):
    processes = []
    for gpu_id in range(num_gpus):
        proc = Process(target=queue_worker_loop, args=(gpu_id, job_queue), daemon=True)
        proc.start()
        processes.append(proc)
    return processes

if __name__ == "__main__":
    gradio_tmp = settings.get("gradio_temp_dir")
    if gradio_tmp:
        os.environ["GRADIO_TEMP_DIR"] = gradio_tmp

    with Manager() as manager:
        jobs_list = manager.list()
        job_queue = VideoJobQueue(jobs_list)
        num_gpus = torch.cuda.device_count()
        if num_gpus < 4:
            raise RuntimeError("At least 4 GPUs (RTX 4500) are required for this application.")
        workers = start_workers(4, job_queue)

        def process_fn(*args, **kwargs):
            job = kwargs
            job_queue.add_job(job)
            return {
                "status": "submitted",
                "message": "Job submitted to queue and will be processed by available GPU."
            }

        interface = create_interface(
            process_fn=process_fn,
            monitor_fn=lambda *a, **k: monitor_job(job_queue, *a, **k),
            end_process_fn=lambda *a, **k: end_process(job_queue, *a, **k),
            update_queue_status_fn=lambda: update_queue_status(job_queue),
            load_lora_file_fn=None,
            job_queue=job_queue,
            settings=settings,
            lora_names=[],
        )

        with gr.Blocks() as app:
            gr.HTML(
                '''
                <div style="margin-bottom: 10px;">
                    <a href="https://datanacci.carrd.co" target="_blank" style="text-decoration:none;">
                        <img src="https://raw.githubusercontent.com/Erli-Human/assets/main/datanacci-banner.png" alt="Datanacci" style="height:40px;vertical-align:middle;margin-right:10px;">
                        <span style="font-size:1.2em;vertical-align:middle;color:#0070f3;font-weight:bold;">Check out Datanacci!</span>
                    </a>
                </div>
                '''
            )
            status_html = gr.HTML(value=update_queue_status(job_queue), elem_id="gpu-status")
            refresh_btn = gr.Button("Refresh GPU/Queue Status")
            refresh_btn.click(fn=lambda: update_queue_status(job_queue), outputs=status_html)
            gr.Markdown("---")
            interface.render()

        app.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            inbrowser=False,
            allowed_paths=[settings.get("output_dir"), settings.get("metadata_dir")],
        )

        import atexit
        try:
            import pynvml
            atexit.register(pynvml.nvmlShutdown)
        except Exception:
            pass
