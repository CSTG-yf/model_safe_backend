# core/local_model_client.py

import openai
import threading
import time
import psutil
from typing import Tuple, Any, Dict

try:
    import pynvml

    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False
    print("警告: pynvml库未安装，将无法监控GPU。请运行 'pip install pynvml' 进行安装。")


class SystemMonitor(threading.Thread):
    """一个在后台监控系统资源的线程"""

    def __init__(self):
        super().__init__()
        self.daemon = True
        self._stop_event = threading.Event()

        self.gpu_handle = None
        if NVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            except pynvml.NVMLError as e:
                print(f"错误: 无法初始化NVIDIA监控库(NVML): {e}。将禁用GPU监控。")
                self.gpu_handle = None

        self.results = {
            "max_cpu_percent": 0.0,
            "max_mem_percent": 0.0,
            "max_gpu_percent": 0,
            "max_gpu_mem_used_mb": 0,
        }

    def run(self):
        """线程主循环，每0.1秒采集一次数据"""
        while not self._stop_event.is_set():
            # CPU和系统内存
            self.results["max_cpu_percent"] = max(self.results["max_cpu_percent"], psutil.cpu_percent(interval=None))
            self.results["max_mem_percent"] = max(self.results["max_mem_percent"], psutil.virtual_memory().percent)

            # GPU监控 (如果可用)
            if self.gpu_handle:
                try:
                    gpu_info = pynvml.nvmlDeviceGetUtilizationRates(self.gpu_handle)
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
                    self.results["max_gpu_percent"] = max(self.results["max_gpu_percent"], gpu_info.gpu)
                    self.results["max_gpu_mem_used_mb"] = max(self.results["max_gpu_mem_used_mb"],
                                                              mem_info.used / 1024 ** 2)
                except pynvml.NVMLError:
                    self.gpu_handle = None

            time.sleep(0.1)

    def stop(self):
        """
        停止监控线程并安全地关闭pynvml。
        """
        self._stop_event.set()
        if NVML_AVAILABLE:

            try:
                pynvml.nvmlShutdown()
            except pynvml.NVMLError:

                pass


class LocalModelClient:
    def __init__(self, model_name: str, api_base_url: str):
        self.model = model_name
        self.api_base_url = api_base_url
        self.client = openai.OpenAI(
            api_key="EMPTY",
            base_url=self.api_base_url,
        )

    def get_chat_response_with_metrics(self, system_prompt: str, prompt: str, **kwargs) -> Tuple[str, Any, Dict]:
        """
        调用本地模型并返回响应、用量和性能指标
        """
        monitor = SystemMonitor()
        monitor.start()

        response_content, usage, metrics = None, None, {}
        start_time, end_time = 0, 0

        try:
            start_time = time.time()
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                **kwargs
            )
            end_time = time.time()

            response_content = completion.choices[0].message.content
            usage = completion.usage

        finally:
            monitor.stop()
            monitor.join()

        metrics = monitor.results
        if start_time and end_time:
            metrics['response_time_sec'] = round(end_time - start_time, 2)

        metrics['max_gpu_mem_used_gb'] = round(metrics['max_gpu_mem_used_mb'] / 1024, 2)

        return response_content, usage, metrics