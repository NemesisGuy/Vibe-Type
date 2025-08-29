# core/performance_monitor.py

import psutil

def get_performance_metrics():
    """Returns a dictionary with current performance metrics."""
    # Get CPU usage. non_blocking allows it to return immediately.
    cpu_percent = psutil.cpu_percent(interval=None)
    
    # Get memory usage
    memory_info = psutil.virtual_memory()
    ram_percent = memory_info.percent
    
    # GPU usage is more complex and often requires specific libraries
    # (e.g., pynvml for NVIDIA). For now, we'll return a placeholder.
    gpu_percent = "N/A"

    return {
        "cpu_usage": f"{cpu_percent:.1f}%",
        "ram_usage": f"{ram_percent:.1f}%",
        "gpu_usage": gpu_percent
    }
