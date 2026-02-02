import bpy
import os
import sys
import urllib.request
import tempfile

class BlenderController:
    """
    Handles all direct interactions with the Blender scene (bpy module).
    """
    def __init__(self, config: dict, logger):
        self.config = config
        self.logger = logger
        self.temp_blend_file = None

    def _download_file(self, url: str) -> str:
        """Downloads a file from a URL to a temporary location."""
        self.logger.info(f"Downloading file from {url}...")
        try:
            with urllib.request.urlopen(url) as response, tempfile.NamedTemporaryFile(delete=False, suffix='.blend') as out_file:
                out_file.write(response.read())
                self.temp_blend_file = out_file.name
                self.logger.info(f"File downloaded to temporary location: {self.temp_blend_file}")
                return self.temp_blend_file
        except Exception as e:
            self.logger.error(f"Failed to download file: {e}")
            sys.exit(1)

    def _setup_scene(self):
        """Loads the .blend file and applies all render settings."""
        input_source = self.config.get('input', {}).get('source')
        if not input_source:
            self.logger.error("No input file specified.")
            sys.exit(1)

        file_path = input_source
        if input_source.startswith("https://"):
            file_path = self._download_file(input_source)
        
        if not os.path.exists(file_path):
            self.logger.error(f"Input file not found: {file_path}")
            sys.exit(1)
            
        self.logger.info(f"Loading Blender file: {file_path}")
        bpy.ops.wm.open_mainfile(filepath=file_path)

        # Set scene
        scene_name = self.config.get('render', {}).get('scene')
        if scene_name and scene_name in bpy.data.scenes:
            bpy.context.window.scene = bpy.data.scenes[scene_name]
            self.logger.info(f"Switched to scene: '{scene_name}'")
        elif scene_name:
            self.logger.error(f"Scene '{scene_name}' not found in the .blend file.")
            sys.exit(1)
        
        scene = bpy.context.scene

        # Apply render settings
        render_config = self.config.get('render', {})
        scene.render.engine = render_config.get('engine', 'CYCLES')
        scene.cycles.samples = render_config.get('samples', 128)
        
        res = render_config.get('resolution', [1920, 1080])
        scene.render.resolution_x, scene.render.resolution_y = res
        
        scene.frame_start = render_config.get('frame_start', 1)
        scene.frame_end = render_config.get('frame_end', 1)

        # Apply output settings
        output_config = self.config.get('output', {})
        output_path = output_config.get('path', './')
        if not os.path.exists(output_path):
            os.makedirs(output_path)
            self.logger.info(f"Created output directory: {output_path}")
        
        scene.render.filepath = os.path.join(output_path, "")
        scene.render.image_settings.file_format = output_config.get('format', 'PNG')
        scene.render.image_settings.color_depth = output_config.get('color_depth', '8')

        # Apply Cycles device settings
        device = self.config.get('cycles', {}).get('device', 'CPU')
        scene.cycles.device = device

        # Execute custom script
        script_path = render_config.get('custom_script')
        if script_path:
            if not os.path.exists(script_path):
                self.logger.error(f"Custom script not found: {script_path}")
                sys.exit(1)
            self.logger.info(f"Executing custom script: {script_path}")
            # WARNING: exec() is a security risk if the script source is untrusted.
            try:
                exec(compile(open(script_path).read(), script_path, 'exec'))
            except Exception as e:
                self.logger.error(f"Error executing custom script: {e}")
                sys.exit(1)

    def render(self):
        """Starts the render process."""
        self._setup_scene()
        scene = bpy.context.scene
        
        is_animation = scene.frame_start < scene.frame_end
        
        self.logger.info(
            f"Starting render: Engine={scene.render.engine}, "
            f"Samples={scene.cycles.samples}, "
            f"Frames={scene.frame_start}-{scene.frame_end}, "
            f"Device={scene.cycles.device}"
        )
        
        bpy.ops.render.render(animation=is_animation, write_still=True)
        
        self.logger.info("Render completed successfully.")

    def cleanup(self):
        """Cleans up temporary files."""
        if self.temp_blend_file and os.path.exists(self.temp_blend_file):
            os.remove(self.temp_blend_file)
            self.logger.info(f"Cleaned up temporary file: {self.temp_blend_file}")
