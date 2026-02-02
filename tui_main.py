# tui_main.py
import os
import sys
import subprocess
import threading
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button, ProgressBar, Input, Select, Log, Switch, Label
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.binding import Binding
from textual import work

# --- Helper to build the command for the subprocess ---
def build_render_command(config: dict, blender_executable="blender") -> list:
    """Converts the UI's config dict into a list of CLI arguments for render_worker.py."""
    script_path = os.path.join(os.path.dirname(__file__), "render_worker.py")
    
    cmd = [
        blender_executable,
        "--background",
        "--python", script_path,
        "--"
    ]

    render = config.get('render', {})
    cycles = config.get('cycles', {})
    output = config.get('output', {})
    monitoring = config.get('gpu_monitoring', {})

    cmd.extend([
        "--input-file", config.get('input', {}).get('source', ''),
        "--output-path", output.get('path', ''),
        "--engine", render.get('engine', 'CYCLES'),
        "--samples", str(render.get('samples', 128)),
        "--resolution", f"{render.get('resolution', [1920,1080])[0]}x{render.get('resolution', [1920,1080])[1]}",
        "--format", output.get('format', 'PNG'),
        "--device", cycles.get('device', 'OPTIX'),
        "--frame-start", str(render.get('frame_start', 1)),
        "--frame-end", str(render.get('frame_end', 1)),
        "--log-level", config.get('logging', {}).get('level', 'INFO'),
    ])

    if monitoring.get('enabled'):
        cmd.extend([
            "--gpu-monitoring",
            "--gpu-log-file", monitoring.get('log_file', './gpu_utilization.log'),
            "--gpu-log-interval", str(monitoring.get('log_interval', 5))
        ])
    
    if render.get('scene'):
        cmd.extend(["--scene", render['scene']])

    if render.get('custom_script'):
        cmd.extend(["--custom-script", render['custom_script']])

    return cmd


class BlenderTUI(App):
    """A Textual TUI for controlling Blender renders."""
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "render", "Render"),
    ]

    render_process = None
    log_reader_thread = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="main-container"):
            with Horizontal(id="config-pane"):
                with Vertical(id="file-settings"):
                    yield Label("Input File (.blend or URL):")
                    yield Input(placeholder="/path/to/file.blend", id="input-file")
                    yield Label("Output Directory:")
                    yield Input(value="./renders", id="output-path")
                with Vertical(id="render-settings"):
                    yield Label("Render Engine:")
                    yield Select(((e, e) for e in ["CYCLES", "EEVEE"]), value="CYCLES", id="engine-select")
                    yield Label("Samples:")
                    # CHANGE: Use Input with type="integer" instead of IntInput
                    yield Input(value="128", type="integer", id="samples-input")
                    yield Label("Resolution (WxH):")
                    yield Input(value="1920x1080", id="resolution-input")
                with Vertical(id="device-settings"):
                    yield Label("Cycles Device:")
                    yield Select(((d, d) for d in ["OPTIX", "CUDA", "METAL", "CPU"]), value="OPTIX", id="device-select")
                    yield Label("Enable GPU Monitoring:")
                    yield Switch(value=True, id="gpu-monitor-switch")
            with Horizontal(id="action-pane"):
                yield Button("Render", id="render-button", variant="success")
                yield Button("Stop", id="stop-button", variant="error", disabled=True)
                yield ProgressBar(id="progress-bar", show_eta=False)
            with VerticalScroll(id="log-pane"):
                yield Log(id="log-output")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#log-output", Log).write_line("Blender CLI Renderer TUI Ready. Press 'r' to render.")
        self.check_blender_installation()

    def check_blender_installation(self):
        try:
            subprocess.run(["blender", "--version"], capture_output=True, check=True, text=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            self.query_one("#log-output", Log).write_line("[bold red]ERROR: 'blender' command not found.[/]")
            self.query_one("#log-output", Log).write_line("Please ensure Blender is installed and in your system's PATH.")
            self.query_one("#render-button", Button).disabled = True

    def get_ui_config(self) -> dict:
        # CHANGE: Cast the value from the Input widget back to an integer
        samples_value = self.query_one("#samples-input", Input).value
        try:
            samples = int(samples_value)
        except ValueError:
            samples = 128 # Fallback value

        return {
            "input": {"source": self.query_one("#input-file", Input).value},
            "output": {"path": self.query_one("#output-path", Input).value, "format": "PNG"},
            "render": {
                "engine": self.query_one("#engine-select", Select).value,
                "samples": samples,
                "resolution": [int(p) for p in self.query_one("#resolution-input", Input).value.split('x')],
                "frame_start": 1, # Could be added to UI
                "frame_end": 1,   # Could be added to UI
            },
            "cycles": {"device": self.query_one("#device-select", Select).value},
            "gpu_monitoring": {
                "enabled": self.query_one("#gpu-monitor-switch", Switch).value,
                "log_file": "./gpu_utilization.log",
                "log_interval": 5,
            },
            "logging": {"level": "INFO"}
        }

    @work(thread=True)
    def read_process_output(self, process: subprocess.Popen):
        """A worker thread to read subprocess output without blocking the UI."""
        log_widget = self.query_one("#log-output", Log)
        # Use readline for real-time output
        for line in iter(process.stdout.readline, b''):
            if not line:
                break
            log_widget.write_line(line.decode('utf-8').strip())
        process.stdout.close()
        return_code = process.wait()
        self.call_from_thread(self.on_render_finished, return_code)

    def action_render(self) -> None:
        if self.render_process and self.render_process.poll() is None:
            self.query_one("#log-output", Log).write_line("[yellow]Render is already in progress.[/]")
            return

        config = self.get_ui_config()
        if not config['input']['source']:
            self.query_one("#log-output", Log).write_line("[bold red]ERROR: Input file is required.[/]")
            return

        cmd = build_render_command(config)
        self.query_one("#log-output", Log).write_line(f"[bold]Executing:[/] {' '.join(cmd)}")
        
        try:
            # Use Popen to run in the background
            self.render_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, encoding='utf-8')
            self.read_process_output(self.render_process) # Start the reader thread
            
            self.query_one("#render-button", Button).disabled = True
            self.query_one("#stop-button", Button).disabled = False
            self.query_one("#progress-bar", ProgressBar).start()

        except FileNotFoundError:
            self.query_one("#log-output", Log).write_line("[bold red]ERROR: 'blender' command not found. Is Blender in your PATH?[/]")
        except Exception as e:
            self.query_one("#log-output", Log).write_line(f"[bold red]ERROR: Failed to start render process: {e}[/]")

    def on_render_finished(self, return_code: int):
        self.query_one("#progress-bar", ProgressBar).stop()
        self.query_one("#render-button", Button).disabled = False
        self.query_one("#stop-button", Button).disabled = True

        if return_code == 0:
            self.query_one("#log-output", Log).write_line("[bold green]Render completed successfully![/]")
        else:
            self.query_one("#log-output", Log).write_line(f"[bold red]Render failed with exit code {return_code}.[/]")
        
        self.render_process = None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "render-button":
            self.action_render()
        elif event.button.id == "stop-button":
            if self.render_process:
                self.render_process.terminate()
                self.query_one("#log-output", Log).write_line("[yellow]Render process terminated by user.[/]")
                self.on_render_finished(-1) # Signal failure/stop

if __name__ == "__main__":
    app = BlenderTUI()
    app.run()
