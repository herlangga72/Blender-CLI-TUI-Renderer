import threading
import subprocess
import time
import platform

class GpuMonitor(threading.Thread):
    """
    A thread to monitor GPU utilization and log it to a file.
    """
    def __init__(self, config: dict, logger):
        super().__init__(daemon=True)
        self.config = config.get('gpu_monitoring', {})
        self.logger = logger
        self._running = False
        self.log_file = self.config.get('log_file', 'gpu_utilization.log')
        self.interval = self.config.get('log_interval', 5)

    def run(self):
        self._running = True
        self.logger.info(f"Starting GPU monitoring, logging to {self.log_file} every {self.interval}s.")
        system = platform.system()
        
        with open(self.log_file, 'w') as f:
            f.write("Timestamp,GPU_Name,Utilization_GPU(%),Utilization_Memory(%),Memory_Used(MB),Memory_Total(MB),Temperature(C),Power_Draw(W)\n")

        while self._running:
            try:
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                log_entry = f"{timestamp},"

                if system == "Darwin": # Apple Silicon
                    # powermetrics is complex to parse cleanly. This is a simplified version.
                    # A more robust solution would parse the XML output.
                    cmd = ["powermetrics", "--samplers", "gpu_power", "-i", "1", "-n", "1"]
                    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                    log_entry += f"Apple_Silicon_GPU,{result.stdout.replace(',', ';').replace('\n', ' ')}\n"
                else: # NVIDIA
                    query = "--query-gpu=name,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,power.draw"
                    cmd = ["nvidia-smi", query, "--format=csv,noheader,nounits"]
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    log_entry += f"{result.stdout.strip()}\n"
                
                with open(self.log_file, 'a') as f:
                    f.write(log_entry)

            except FileNotFoundError:
                self.logger.warning(f"GPU monitoring command ('{cmd[0]}' if 'cmd' in locals() else 'nvidia-smi/powermetrics') not found. Disabling monitoring.")
                self.stop()
            except Exception as e:
                self.logger.error(f"An error occurred during GPU monitoring: {e}")
            
            time.sleep(self.interval)

    def stop(self):
        self._running = False
        self.join()
        self.logger.info("GPU monitoring stopped.")
