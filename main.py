import sys
import os
import argparse
import platform
import shutil

# Ensure this script is run within Blender's Python environment
try:
    import bpy
except ImportError:
    print("Error: This script must be run within Blender's Python environment.")
    print("Usage: blender --background --python /path/to/main.py -- [your args]")
    sys.exit(1)

from config_manager import ConfigManager
from logger import setup_logger
from gpu_detector import select_device
from blender_controller import BlenderController
from gpu_monitor import GpuMonitor

def parse_resolution(res_string):
    """Parses a 'WxH' string into a tuple of integers."""
    try:
        w, h = map(int, res_string.split('x'))
        return [w, h]
    except ValueError:
        raise argparse.ArgumentTypeError("Resolution must be in WxH format, e.g., 1920x1080")

def main():
    parser = argparse.ArgumentParser(description="A production-ready Blender CLI rendering tool.", add_help=False)
    
    # --- Core I/O ---
    parser.add_argument('input_file', nargs='?', help="Path or HTTPS URL to the .blend file.")
    parser.add_argument('-o', '--output-path', default="./renders", help="Directory to save rendered images.")
    parser.add_argument('-c', '--config', help="Path to a YAML configuration file.")

    # --- Render Settings ---
    parser.add_argument('-e', '--engine', choices=['CYCLES', 'EEVEE'], default='CYCLES', help="Render engine.")
    parser.add_argument('-s', '--samples', type=int, default=128, help="Number of render samples for Cycles.")
    parser.add_argument('-r', '--resolution', type=parse_resolution, default=[1920, 1080], help="Output resolution (e.g., 1920x1080).")
    parser.add_argument('-f', '--format', default='PNG', choices=['PNG', 'JPEG', 'EXR'], help="Output image format.")
    parser.add_argument('--scene', help="Name of the scene to render.")
    parser.add_argument('--custom-script', help="Path to a Python script to execute before rendering.")
    
    # --- Device Settings ---
    parser.add_argument('-d', '--device', choices=['CPU', 'CUDA', 'OPTIX', 'METAL'], default='OPTIX', help="Cycles compute device.")

    # --- System & Monitoring ---
    parser.add_argument('--shutdown', action='store_true', help="Shut down the system after a successful render.")
    parser.add_argument('--gpu-monitoring', action='store_true', help="Enable GPU utilization logging.")
    parser.add_argument('--gpu-log-file', default="./gpu_utilization.log", help="File to write GPU logs to.")
    parser.add_argument('--gpu-log-interval', type=int, default=5, help="Interval in seconds for GPU logging.")
    
    # --- Logging ---
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help="Set the logging level.")
    parser.add_argument('--log-file', help="File to write application logs to. Defaults to stdout.")

    # Use parse_known_args to separate Blender's args from our script's args
    # Blender's own args are before the '--', ours are after.
    # sys.argv will be like: ['blender', '--background', '--python', 'main.py', '--', '-e', 'CYCLES', ...]
    # So our arguments start at sys.argv.index('--') + 1
    try:
        separator_index = sys.argv.index('--')
        script_args = sys.argv[separator_index + 1:]
    except ValueError:
        script_args = []

    args = parser.parse_args(script_args)

    # --- Orchestration ---
    config_manager = ConfigManager(args)
    config = config_manager.get()
    
    logger = setup_logger("BlenderRenderTool", **config.get('logging', {}))
    logger.info("Application started.")
    logger.debug(f"Final merged configuration: {config}")

    # Pre-flight checks
    if not config.get('input', {}).get('source'):
        logger.error("No input file specified. Please provide an input file path or URL.")
        sys.exit(1)

    # Select device and update config
    final_device = select_device(config, logger)
    config['cycles']['device'] = final_device

    # Initialize controllers
    blender_controller = BlenderController(config, logger)
    gpu_monitor = GpuMonitor(config, logger)

    try:
        if config.get('gpu_monitoring', {}).get('enabled'):
            gpu_monitor.start()
        
        blender_controller.render()
        
        if config.get('system', {}).get('shutdown_after_render'):
            logger.warning("Shutting down system in 60 seconds...")
            if platform.system() == "Windows":
                os.system("shutdown /s /t 60")
            else: # Linux and macOS
                os.system("sudo shutdown -h +1")

    except Exception as e:
        logger.error(f"A critical error occurred: {e}", exc_info=True)
        sys.exit(2)
    finally:
        if gpu_monitor.is_alive():
            gpu_monitor.stop()
        blender_controller.cleanup()
        logger.info("Application finished.")
    
    sys.exit(0)

if __name__ == "__main__":
    main()
