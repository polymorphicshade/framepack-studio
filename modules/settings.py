import json
from pathlib import Path
from typing import Dict, Any, Optional
import os

class Settings:
    def __init__(self):
        # Get the project root directory (where settings.py is located)
        project_root = Path(__file__).parent.parent
        
        self.settings_file = project_root / ".framepack" / "settings.json"
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Set default paths relative to project root
        self.default_settings = {
            "save_metadata": True,
            "gpu_memory_preservation": 6,
            "output_dir": str(project_root / "outputs"),
            "metadata_dir": str(project_root / "outputs"),
            "lora_dir": str(project_root / "loras"),
            "gradio_temp_dir": str(project_root / "temp"),
            "input_files_dir": str(project_root / "input_files"),  # New setting for input files
            "auto_save_settings": True,
            "gradio_theme": "default",
            "mp4_crf": 16,
            "clean_up_videos": True,
            "override_system_prompt": False,
            "auto_cleanup_on_startup": False, # ADDED: New setting for startup cleanup
            "latents_display_top": False, # NEW: Control latents preview position (False = right column, True = top of interface)
            "system_prompt_template": "{\"template\": \"<|start_header_id|>system<|end_header_id|>\\n\\nDescribe the video by detailing the following aspects: 1. The main content and theme of the video.2. The color, shape, size, texture, quantity, text, and spatial relationships of the objects.3. Actions, events, behaviors temporal relationships, physical movement changes of the objects.4. background environment, light, style and atmosphere.5. camera angles, movements, and transitions used in the video:<|eot_id|><|start_header_id|>user<|end_header_id|>\\n\\n{}<|eot_id|>\", \"crop_start\": 95}",
            "startup_model_type": "None",
            "startup_preset_name": None,
            "ssl_certfile": None,  # Path to an SSL certificate file for HTTPS. None = HTTP only.
            "ssl_keyfile": None,   # Path to the matching SSL private key. Both are required for HTTPS.
            "ssl_keyfile_password": None,  # Password for the key file, if it is encrypted.
            "ssl_verify": False,   # Gradio verifies the cert on startup; self-signed certs need this off.
            "enhancer_prompt_template": """You are a creative assistant for a text-to-video generator. Your task is to take a user's prompt and make it more descriptive, vivid, and detailed. Focus on visual elements. Do not change the core action, but embellish it.

User prompt: "{text_to_enhance}"

Enhanced prompt:"""
        }
        self.settings = self.load_settings()

    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file or return defaults"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                    # Merge with defaults to ensure all settings exist
                    settings = self.default_settings.copy()
                    settings.update(loaded_settings)
                    return settings
            except Exception as e:
                print(f"Error loading settings: {e}")
                return self.default_settings.copy()
        return self.default_settings.copy()

    def save_settings(self, **kwargs):
        """Save settings to file. Accepts keyword arguments for any settings to update."""
        # Update self.settings with any provided keyword arguments
        self.settings.update(kwargs)
        # Ensure all default fields are present
        for k, v in self.default_settings.items():
            self.settings.setdefault(k, v)

        # Ensure directories exist for relevant fields
        for dir_key in ["output_dir", "metadata_dir", "lora_dir", "gradio_temp_dir"]:
            dir_path = self.settings.get(dir_key)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

        # Save to file
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f, indent=4)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value"""
        self.settings[key] = value
        if self.settings.get("auto_save_settings", True):
            self.save_settings()

    def update(self, settings: Dict[str, Any]) -> None:
        """Update multiple settings at once"""
        self.settings.update(settings)
        if self.settings.get("auto_save_settings", True):
            self.save_settings()


def resolve_ssl_config(
    settings: "Settings",
    certfile: Optional[str] = None,
    keyfile: Optional[str] = None,
    keyfile_password: Optional[str] = None,
    ssl_verify: Optional[bool] = None,
) -> Dict[str, Any]:
    """Returns the SSL kwargs for Gradio's launch() when HTTPS is configured.

    Command line values win over the saved settings. Returns an empty dict when
    HTTPS is not configured or the files are missing, so the app falls back to
    plain HTTP instead of refusing to start.
    """
    certfile = certfile or settings.get("ssl_certfile")
    keyfile = keyfile or settings.get("ssl_keyfile")

    if not certfile and not keyfile:
        return {}

    if not certfile or not keyfile:
        print("SSL: both a certificate and a key are required - falling back to HTTP")
        return {}

    certpath = Path(str(certfile)).expanduser()
    keypath = Path(str(keyfile)).expanduser()

    if not certpath.is_file():
        print(f"SSL: certificate file not found: {certpath} - falling back to HTTP")
        return {}
    if not keypath.is_file():
        print(f"SSL: key file not found: {keypath} - falling back to HTTP")
        return {}

    if ssl_verify is None:
        ssl_verify = bool(settings.get("ssl_verify", False))
    if keyfile_password is None:
        keyfile_password = settings.get("ssl_keyfile_password") or None

    ssl_kwargs: Dict[str, Any] = {
        "ssl_certfile": str(certpath),
        "ssl_keyfile": str(keypath),
        "ssl_verify": ssl_verify,
    }
    if keyfile_password:
        ssl_kwargs["ssl_keyfile_password"] = keyfile_password

    return ssl_kwargs
