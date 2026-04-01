# Blender CLI TUI Renderer

A **terminal-based UI (TUI)** built with Textual for managing and executing Blender renders via the command line.

This tool provides an interactive interface to configure rendering parameters and execute Blender in background mode, while streaming logs and monitoring progress in real time.

---

## 🚀 Features

- Interactive TUI for Blender rendering
- Real-time log streaming from subprocess
- Background rendering using Blender CLI
- Configurable render settings:
  - Engine (Cycles / Eevee)
  - Samples
  - Resolution
  - Device (OPTIX / CUDA / CPU / METAL)
- GPU monitoring support (optional)
- Process control (start / stop render)
- Progress visualization

---

## 📦 Requirements

- Python 3.9+
- Blender (installed and available in `PATH`)
- Dependencies:

```bash
pip install textual
```

---

## ⚙️ Installation

```bash
git clone https://github.com/herlangga72/Python-CLI-Server-Rendering.git
cd Python-CLI-Server-Rendering
```

(Optional but recommended)

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## ▶️ Usage

Run the TUI:

```bash
python tui_main.py
```

---

## 🖥️ Interface Overview

The TUI is divided into several sections:

### 1. File Settings
- Input `.blend` file or URL
- Output directory

### 2. Render Settings
- Engine selection (`CYCLES` / `EEVEE`)
- Samples (integer input)
- Resolution (`WIDTHxHEIGHT`)

### 3. Device Settings
- GPU/CPU selection
- GPU monitoring toggle

### 4. Actions
- **Render**: Start rendering
- **Stop**: Terminate process
- **Progress Bar**: Shows active render state

### 5. Logs
- Real-time output from Blender process

---

## ⌨️ Keybindings

| Key | Action |
|-----|--------|
| `r` | Start render |
| `q` | Quit application |

---

## 🔧 How It Works

1. UI collects configuration
2. Configuration is converted into CLI arguments
3. A subprocess is spawned:

```bash
blender --background --python render_worker.py -- [args]
```

4. Output is streamed into the TUI log panel
5. A worker thread prevents UI blocking

---

## 📁 Core Components

```
tui_main.py          # TUI application (Textual)
render_worker.py     # Blender execution script (called by CLI)
```

---

## 🧠 Command Generation

The render command is dynamically built via:

```python
build_render_command(config)
```

Example output:

```bash
blender --background \
  --python render_worker.py -- \
  --input-file scene.blend \
  --output-path ./renders \
  --engine CYCLES \
  --samples 128 \
  --resolution 1920x1080 \
  --device OPTIX
```

---

## 📊 GPU Monitoring (Optional)

When enabled, additional flags are passed:

```bash
--gpu-monitoring \
--gpu-log-file ./gpu_utilization.log \
--gpu-log-interval 5
```

---

## ❗ Error Handling

- Detects missing Blender installation
- Prevents duplicate render execution
- Handles invalid inputs (e.g., samples fallback)
- Gracefully terminates subprocess

---

## 🧪 Development Notes

- Uses `subprocess.Popen` for non-blocking execution
- Uses Textual `@work(thread=True)` for async log streaming
- UI remains responsive during rendering

---

## 🔮 Possible Improvements

- Frame range UI inputs
- Scene selector
- Custom script injection
- Preset configurations
- Render queue system
- Remote rendering support

---

## 📄 License

MIT License

---

## 🤝 Contributing

Pull requests and improvements are accepted. Focus areas:

- UI enhancements (Textual)
- Performance improvements
- Better Blender integration
- Monitoring and observability
