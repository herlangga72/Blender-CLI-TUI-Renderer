# render_worker.py
# This script is intended to be run by Blender: blender --background --python render_worker.py -- [args]

import sys
import os
import argparse
import platform

# This script MUST be run by Blender
try:
    import bpy
except ImportError:
    print("CRITICAL: This script can only be run from within Blender's Python environment.")
    sys.exit(1)

# --- Backend Modules ---
from config_manager import ConfigManager
from logger import setup_logger
from gpu_detector import select_device
from blender_controller import BlenderController
from gpu_monitor import GpuMonitor
from main import parse_resolution # Re-use helper

def main():
    # This script expects arguments after a '--' separator
    try:
        separator_index = sys.argv.index('--')
        script_args = sys.argv[separator_index + 1:]
    except ValueError:
        script_args = []

    # Define the arguments this worker script accepts
    parser = argparse.ArgumentParser(description="Blender Render Worker Script")
    parser.add_argument('--input-file', required=True, help="Path or HTTPS URL to the .blend file.")
    parser.add_argument('--output-path', default="./renders", help="Directory to save rendered images.")
    parser.add_argument('--engine', choices=['CYCLES', 'EEVEE'], default='CYCLES')
    parser.add_argument('--samples', type=int, default=128)
    parser.add_argument('--resolution', type=parse_resolution, default=[1920, 1080])
    parser.add_argument('--format', default='PNG', choices=['PNG', 'JPEG', 'EXR'])
    parser.add_argument('--scene', help="Name of the scene to render.")
    parser.add_argument('--device', choices=['CPU', 'CUDA', 'OPTIX', 'METAL'], default='OPTIX')
    parser.add_argument('--frame-start', type=int, default=1)
    parser.add_argument('--frame-end', type=int, default=1)
    parser.add_argument('--custom-script', help="Path to a Python script to execute before rendering.")
    parser.add_argument('--gpu-monitoring', action='store_true')
    parser.add_argument('--gpu-log-file', default="./gpu_utilization.log")
    parser.add_argument('--gpu-log-interval', type=int, default=5)
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args(script_args)
    
    # --- Orchestration ---
    # The ConfigManager is less critical here since we get a flat args object,
    # but we can adapt it to create a consistent dictionary.
    config = {
        'input': {'source': args.input_file},
        'output': {'path': args.output_path, 'format': args.format, 'color_depth': '8'},
        'render': {
            'engine': args.engine, 'samples': args.samples, 'resolution': args.resolution,
            'frame_start': args.frame_start, 'frame_end': args.frame_end, 'scene': args.scene,
            'custom_script': args.custom_script
        },
        'cycles': {'device': args.device},
        'system': {'shutdown_after_render': False}, # TUI handles shutdown logic
        'gpu_monitoring': {
            'enabled': args.gpu_monitoring, 'log_file': args.gpu_log_file,
            'log_interval': args.gpu_log_interval
        },
        'logging': {'level': args.log_level, 'file': None} # Log to stdout for subprocess
    }

    logger = setup_logger("BlenderRenderWorker", **config.get('logging', {}))
    logger.info("Render Worker started.")
    logger.debug(f"Configuration: {config}")

    # Pre-flight checks
    if not config.get('input', {}).get('source'):
        logger.error("No input file specified.")
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
        
    except Exception as e:
        logger.error(f"A critical error occurred: {e}", exc_info=True)
        sys.exit(2)
    finally:
        if gpu_monitor.is_alive():
            gpu_monitor.stop()
        blender_controller.cleanup()
        logger.info("Render Worker finished.")
    
    sys.exit(0)

if __name__ == "__main__":
    main()
