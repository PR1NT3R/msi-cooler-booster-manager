#!/usr/bin/env python3
"""

"""

from pathlib import Path
import subprocess
import threading
import logging
import signal
import time
import sys
import os

# ===== CONFIGURATION =====
CPU_TEMP_THRESHOLD = 60  # Enable cooler boost when CPU temp is above X
GPU_TEMP_THRESHOLD = 60  # Enable cooler boost when GPU temp is above Y

DISABLE_COOLER_BOOST_ON_EXIT = False # If you want the script to disable cooler boost upon exit, not recommended

TEMP_OSCILLATION_FIX = 5  # Makes the script disable the cooler boost at TRESHOLD-THIS_VALUE
TIME_OSCILLATION_FIX = 60 # Makes the script disable the cooler boost if the cooler boost has been on for at least THIS_VALUE seconds

CHECK_INTERVAL = 3  # Time in seconds between temperature checks

MAIN_SCRIPT = "main.py" # Filename of the main script which should be in the current directory

LOG_LEVEL = logging.INFO  # Change to logging.DEBUG for more verbose output
# ========================

class ThermalMonitor:
    def __init__(self):
        self.running = False
        self.cooler_boost_enabled = False
        self.main_script_path = Path(os.getcwd()) / MAIN_SCRIPT
        self.setup_logging()
        self.last_coolerboost_enabled_at = 0
        
    def setup_logging(self):
        logging.basicConfig(
            level=LOG_LEVEL,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
        
    def check_main_script(self):
        if not self.main_script_path.exists():
            raise FileNotFoundError(
                f"Main script not found: {self.main_script_path}\n"
                f"Please ensure '{MAIN_SCRIPT}' is in the current directory: {os.getcwd()}"
            )

        if not os.access(self.main_script_path, os.R_OK):
            raise PermissionError(f"Cannot read {self.main_script_path}")
            
    def run_main_script(self, *args):
        try:
            cmd = [sys.executable, str(self.main_script_path)] + list(args)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                self.logger.error(f"Main script failed: {result.stderr}")
                return None
                
            return result.stdout.strip()
            
        except subprocess.TimeoutExpired:
            self.logger.error("Main script timed out")
            return None
        except Exception as e:
            self.logger.error(f"Error running main script: {e}")
            return None
    
    def get_temperature(self, temp_type):
        if temp_type == "cpu":
            output = self.run_main_script("--cpu-temp")
        elif temp_type == "gpu":
            output = self.run_main_script("--gpu-temp")
        else:
            return None
            
        if output is None:
            return None
            
        try:
            # Parse the cpu or gpu temp from the "XX.0°C" format
            temp_str = output.split(": ")[1]
            temp_value = float(temp_str.replace("°C", ""))
            return temp_value
        except (IndexError, ValueError) as e:
            self.logger.error(f"Failed to parse the temperature from: {output}")
            return None
    
    def set_cooler_boost(self, enable):
        state = "on" if enable else "off"
        output = self.run_main_script("--cooler-boost", state)
        
        if output is not None:
            self.cooler_boost_enabled = enable
            self.logger.info(f"Cooler boost {'enabled' if enable else 'disabled'}")
            return True
        else:
            self.logger.error(f"Failed to {'enable' if enable else 'disable'} cooler boost")
            return False

    
    def check_temperatures(self):
        cpu_temp = self.get_temperature("cpu")
        gpu_temp = self.get_temperature("gpu")
        
        if cpu_temp is None and gpu_temp is None:
            self.logger.error("Failed to read both CPU and GPU temperatures")
            return

        temp_info = []
        if cpu_temp is not None:
            temp_info.append(f"CPU: {cpu_temp}°C")
        if gpu_temp is not None:
            temp_info.append(f"GPU: {gpu_temp}°C")
        
        self.logger.debug(f"Temperatures - {', '.join(temp_info)}")
        
        # Deciding whenever to enable the cooler boost or not
        should_enable = False
        temp_reasons = []
        
        if cpu_temp is not None and cpu_temp > CPU_TEMP_THRESHOLD:
            should_enable = True
            temp_reasons.append(f"CPU {cpu_temp}°C > {CPU_TEMP_THRESHOLD}°C")
            
        if gpu_temp is not None and gpu_temp > GPU_TEMP_THRESHOLD:
            should_enable = True
            temp_reasons.append(f"GPU {gpu_temp}°C > {GPU_TEMP_THRESHOLD}°C")
        
        # Prevent oscillation
        if self.cooler_boost_enabled and not should_enable:
            cpu_safe = cpu_temp is None or cpu_temp < (CPU_TEMP_THRESHOLD - TEMP_OSCILLATION_FIX)
            gpu_safe = gpu_temp is None or gpu_temp < (GPU_TEMP_THRESHOLD - TEMP_OSCILLATION_FIX)
            
            if not (cpu_safe and gpu_safe):
                should_enable = True
                self.logger.debug("Keeping cooler boost enabled due to hysteresis")
        
        # Apply the cooler boost state
        if should_enable and not self.cooler_boost_enabled:
            self.logger.info(f"Enabling cooler boost: {', '.join(temp_reasons)}")
            self.set_cooler_boost(True)
            self.last_coolerboost_enabled_at = time.time()
            
        elif not should_enable and self.cooler_boost_enabled and time.time() - self.last_coolerboost_enabled_at > TIME_OSCILLATION_FIX:
            disable_reasons = []
            if cpu_temp is not None:
                disable_reasons.append(f"CPU {cpu_temp}°C")
            if gpu_temp is not None:
                disable_reasons.append(f"GPU {gpu_temp}°C")
            
            self.logger.info(f"Disabling cooler boost: temperatures normal ({', '.join(disable_reasons)})")
            self.set_cooler_boost(False)
    
    def monitor_loop(self):
        self.logger.info("Starting thermal monitoring...")
        self.logger.info(f"CPU threshold: {CPU_TEMP_THRESHOLD}°C, GPU threshold: {GPU_TEMP_THRESHOLD}°C")
        self.logger.info(f"Check interval: {CHECK_INTERVAL}s, Temp oscillation fix: {TEMP_OSCILLATION_FIX}°C Time oscillation fix: {TIME_OSCILLATION_FIX}s")
        
        while self.running:
            try:
                self.check_temperatures()
                time.sleep(CHECK_INTERVAL)
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(CHECK_INTERVAL)
    
    def start(self):
        if self.running:
            self.logger.warning("Monitor is already running")
            return
            
        try:
            self.check_main_script()
        except (FileNotFoundError, PermissionError) as e:
            self.logger.error(str(e))
            return False
            
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Thermal monitor started")
        return True
    
    def stop(self):
        if not self.running:
            return
            
        self.logger.info("Stopping the thermal monitor...")
        self.running = False
        
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=5)

        # Disable cooler boost on exit if it is set to do so
        if DISABLE_COOLER_BOOST_ON_EXIT:
            if self.cooler_boost_enabled:
                self.logger.info("Disabling cooler boost before exit")
                self.set_cooler_boost(False)
            
        self.logger.info("Thermal monitor stopped")
        sys.exit(0)


def signal_handler(signum, frame):
    # Handle the shutdown signals well-ish
    global monitor
    if monitor:
        monitor.stop()
    sys.exit(0)


def main():
    global monitor
    
    print("MSI Thermal Monitor Service")
    print(f"CPU Threshold: {CPU_TEMP_THRESHOLD}°C, GPU Threshold: {GPU_TEMP_THRESHOLD}°C")
    print(f"Check Interval: {CHECK_INTERVAL}s")
    print(f"Main script: {MAIN_SCRIPT} (in {os.getcwd()})")
    print("-" * 50)
    
    # Handle the shutdown signals well-ish
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    monitor = ThermalMonitor()
    
    if not monitor.start():
        return 1
    
    try:
        while monitor.running:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        monitor.stop()
    
    return 0


if __name__ == "__main__":
    monitor = None
    sys.exit(main())