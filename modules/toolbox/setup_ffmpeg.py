import os
import sys
import requests
import tarfile
import zipfile
import shutil
from tqdm import tqdm

# This runs at import time (see modules/toolbox_app.py), so it sits between the
# user and a usable app. One attempt, short timeouts, and a clean give-up: a
# mirror that is unreachable or wedged costs seconds, not minutes, and the app
# still starts without the toolbox's bundled FFmpeg.
CONNECT_TIMEOUT_SECONDS = 10
# Applies between chunks rather than to the whole transfer, so a slow but
# progressing download still completes while a stalled one aborts.
READ_TIMEOUT_SECONDS = 30

# GitHub release assets, served from a CDN. The "latest" tag is rolling, so
# these URLs stay live as the builds are refreshed. The gpl variant carries
# libx264 and libvpx-vp9, both of which the toolbox encodes with.
DOWNLOAD_SOURCES = {
    "windows": (
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
        "ffmpeg-n8.1-latest-win64-gpl-8.1.zip"
    ),
    "linux": (
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
        "ffmpeg-n8.1-latest-linux64-gpl-8.1.tar.xz"
    ),
}


def find_binary(search_root, binary_name):
    """Locate a binary anywhere under search_root, or return None.

    Archive layouts differ between builds and change between versions - some put
    the binaries in a bin/ subdirectory, some at the top level - so search for
    them instead of hardcoding a path that a new release would break.
    """
    for dirpath, _dirnames, filenames in os.walk(search_root):
        if binary_name in filenames:
            return os.path.join(dirpath, binary_name)
    return None


def setup_ffmpeg():
    """Download and set up a cross-platform, full build of FFmpeg and FFprobe."""
    # Get the directory of the current script, which is now inside 'modules/toolbox/'
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # The 'bin' directory is created directly inside this script's directory.
    bin_dir = os.path.join(script_dir, 'bin')
    os.makedirs(bin_dir, exist_ok=True)

    # --- Platform-specific configuration ---
    if sys.platform == "win32":
        platform = "windows"
        ffmpeg_name = 'ffmpeg.exe'
        ffprobe_name = 'ffprobe.exe'
        archive_name = 'ffmpeg.zip'
    elif sys.platform.startswith("linux"):
        platform = "linux"
        ffmpeg_name = 'ffmpeg'
        ffprobe_name = 'ffprobe'
        archive_name = 'ffmpeg.tar.xz'
    else:
        print(f"Unsupported platform: {sys.platform}")
        print("Please download FFmpeg manually and place ffmpeg/ffprobe in the 'bin' directory.")
        return

    download_url = DOWNLOAD_SOURCES[platform]

    ffmpeg_path = os.path.join(bin_dir, ffmpeg_name)
    ffprobe_path = os.path.join(bin_dir, ffprobe_name)

    if os.path.exists(ffmpeg_path) and os.path.exists(ffprobe_path):
        print(f"FFmpeg is already set up in: {bin_dir}")
        return

    archive_path = os.path.join(bin_dir, archive_name)
    temp_extract_dir = os.path.join(bin_dir, 'temp_ffmpeg_extract')

    try:
        print(f"FFmpeg not found. Downloading and setting up for {platform}...")
        download_ffmpeg(download_url, archive_path)

        print("Download complete. Installing...")
        os.makedirs(temp_extract_dir, exist_ok=True)

        if archive_name.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as archive:
                archive.extractall(path=temp_extract_dir)
        elif archive_name.endswith('.tar.xz'):
            with tarfile.open(archive_path, 'r:xz') as archive:
                try:
                    archive.extractall(path=temp_extract_dir, filter='data')
                except TypeError:
                    # Python 3.10 has no extraction filters.
                    archive.extractall(path=temp_extract_dir)

        source_ffmpeg_path = find_binary(temp_extract_dir, ffmpeg_name)
        source_ffprobe_path = find_binary(temp_extract_dir, ffprobe_name)

        if not source_ffmpeg_path or not source_ffprobe_path:
            raise FileNotFoundError(
                f"Could not find {ffmpeg_name} and {ffprobe_name} anywhere in the downloaded archive."
            )

        shutil.copy(source_ffmpeg_path, ffmpeg_path)
        shutil.copy(source_ffprobe_path, ffprobe_path)

        if platform == "linux":
            os.chmod(ffmpeg_path, 0o755)
            os.chmod(ffprobe_path, 0o755)

        print(f"FFmpeg setup complete. Binaries are in: {bin_dir}")

    except Exception as e:
        # Deliberately not retried: this blocks app startup, and the toolbox is
        # the only feature that needs these binaries.
        print(f"\nCould not set up FFmpeg: {e}")
        print("Continuing without the bundled FFmpeg - the post-processing toolbox will be limited.")
        print(f"To fix it, download FFmpeg manually and put {ffmpeg_name} and {ffprobe_name} in: {bin_dir}")
        print(f"Tried: {download_url}")
    finally:
        # Clean up
        if os.path.exists(archive_path):
            os.remove(archive_path)
        if os.path.exists(temp_extract_dir):
            shutil.rmtree(temp_extract_dir, ignore_errors=True)


def download_ffmpeg(url, destination):
    """Download a file with progress bar. One attempt, then give up."""
    response = requests.get(
        url,
        stream=True,
        timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
    )
    response.raise_for_status()  # Raise an exception for bad status codes
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024

    # The calling function now handles the initial "Downloading..." message.
    # This keeps the download function focused on its single responsibility.
    with open(destination, 'wb') as file, tqdm(
            desc=os.path.basename(destination), # Use basename for a cleaner progress bar
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
        for data in response.iter_content(block_size):
            size = file.write(data)
            bar.update(size)
