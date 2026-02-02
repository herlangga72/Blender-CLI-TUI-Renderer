import bpy
import platform

def select_device(config: dict, logger):
    """
    Detects available GPUs and selects the best one based on the config.
    Falls back to CPU if the requested device is unavailable.
    """
    system = platform.system()
    requested_device = config.get('cycles', {}).get('device', 'CPU').upper()
    final_device = 'CPU'

    if system == "Darwin": # macOS
        if requested_device == 'METAL' and bpy.app.build_options.cycles:
            logger.info("METAL backend requested and available.")
            final_device = 'METAL'
        elif requested_device != 'CPU':
            logger.warning(f"Requested device '{requested_device}' is not available on macOS. Falling back to CPU.")
    else: # Windows, Linux
        cycles_options = bpy.app.build_options.cycles
        if requested_device == 'OPTIX' and cycles_options.optix:
            logger.info("OPTIX backend requested and available.")
            final_device = 'OPTIX'
        elif requested_device == 'CUDA' and cycles_options.cuda:
            logger.info("CUDA backend requested and available.")
            final_device = 'CUDA'
        elif requested_device != 'CPU':
            logger.warning(f"Requested device '{requested_device}' is not available. Falling back to CPU.")
            
    logger.info(f"Final render device selected: {final_device}")
    return final_device
