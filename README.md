<h1 align="center">FramePack Studio</h1>

[![Discord](https://img.shields.io/badge/Discord-%235865F2.svg?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/MtuM7gFJ3V)[![Patreon](https://img.shields.io/badge/Patreon-F96854?style=for-the-badge&logo=patreon&logoColor=white)](https://www.patreon.com/ColinU)

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/colinurbs/FramePack-Studio)

FramePack Studio is an AI video generation application based on FramePack that strives to provide everything you need to create high quality video projects.

![screencapture-127-0-0-1-7860-2025-06-12-19_50_37](https://github.com/user-attachments/assets/b86a8422-f4ce-452b-80eb-2ba91945f2ea)
![screencapture-127-0-0-1-7860-2025-06-12-19_52_33](https://github.com/user-attachments/assets/ebfb31ca-85b7-4354-87c6-aaab6d1c77b1)

## Current Features

- **F1, Original and Video Extension Generations**: Run all in a single queue
- **End Frame Control for 'Original' Model**: Provides greater control over generations
- **Upscaling and Post-processing**
- **Timestamped Prompts**: Define different prompts for specific time segments in your video
- **Prompt Blending**: Define the blending time between timestamped prompts
- **LoRA Support**: Works with most (all?) Hunyuan Video LoRAs
- **Queue System**: Process multiple generation jobs without blocking the interface. Import and export queues.
- **Metadata Saving/Import**: Prompt and seed are encoded into the output PNG, all other generation metadata is saved in a JSON file that can be imported later for similar generations.
- **Custom Presets**: Allow quick switching between named groups of parameters. A custom Startup Preset can also be set.
- **I2V and T2V**: Works with or without an input image to allow for more flexibility when working with standard Hunyuan Video LoRAs
- **Latent Image Options**: When using T2V you can generate based on a black, white, green screen, or pure noise image

## Prerequisites

- CUDA-compatible GPU with at least 8GB VRAM (16GB+ recommended)
- 16GB System Memory (32GB+ strongly recommended)
- 80GB+ of storage (including ~25GB for each model family: Original and F1)

## Documentation

For information on installation, configuration, and usage, please visit our [documentation site](https://docs.framepackstudio.com/).

## Installation

Please see [this guide](https://docs.framepackstudio.com/docs/get_started/) on our documentation site to get FP-Studio installed.

## HTTPS

The UI is served over plain HTTP by default. There are two ways to put it behind TLS.

### Direct HTTPS

Give the app a certificate and key and it serves HTTPS itself, no reverse proxy involved. Either pass them on the command line:

```bash
python studio.py --ssl-certfile certs/fullchain.pem --ssl-keyfile certs/privkey.pem
```

or set **SSL Certificate File** and **SSL Key File** in the Settings tab (stored as `ssl_certfile` / `ssl_keyfile` in `.framepack/settings.json`) and restart. Command line values win over the saved settings. Both a certificate and a key are required; if either is missing or the file does not exist, the app prints why and falls back to HTTP rather than refusing to start.

To mint a self-signed certificate for local use:

```bash
mkdir -p certs
openssl req -x509 -newkey rsa:2048 -sha256 -nodes -days 3650 \
  -keyout certs/privkey.pem -out certs/fullchain.pem \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
```

In Git Bash, prefix the command with `MSYS2_ARG_CONV_EXCL="*"` — it rewrites `/CN=localhost` into a Windows path otherwise. PowerShell and cmd need no such prefix.

Add every address you will actually type in the browser to `subjectAltName` — including the machine's LAN address, e.g. `IP:192.168.1.99` — or the browser will warn on every visit. Browsers warn once for a self-signed certificate regardless, until you accept it.

Certificate verification on startup is off by default (`ssl_verify` in the settings file), because self-signed certificates fail it. Pass `--ssl-verify` when you are using a CA-issued certificate and want it checked.

### Docker with an nginx front end

`docker-compose.https.yml` runs the same stack as `docker-compose.yml` plus an nginx sidecar that terminates TLS:

```bash
docker compose -f docker-compose.https.yml up -d
```

The UI is then at `https://localhost:8443`. A self-signed certificate is generated into `./certs` on first boot; drop a real `fullchain.pem` / `privkey.pem` in there to use a CA-issued one instead.

HTTPS is port 8443, not 7860 — in this stack 7860 is the app's own plain HTTP listener, published on `127.0.0.1` only, and nothing there speaks TLS. Copy `.env.https.example` to `.env` to change either port, or to put the host's LAN address in the certificate before first boot.

## Contributing 

We would love your help building FramePack Studio! To make collaboration effective, please adhere to the following:
- Keep Pull Requests Focused: Each Pull Request should address a single issue or add one specific feature. Please do not mix bug fixes, new features, and code refactoring in the same PR.
- Target the develop Branch: All Pull Requests must be opened against the develop branch. PRs opened against the main branch will be closed.
- Discuss Big Changes First: If you plan to work on a large feature or a significant refactor, please announce it first in the #contributors channel on our [Discord server](https://discord.com/invite/MtuM7gFJ3V). This helps us coordinate efforts and prevent duplicate work.


## Credits

Many thanks to [Lvmin Zhang](https://github.com/lllyasviel) for the absolutely amazing work on the original [FramePack](https://github.com/lllyasviel/FramePack) code!

Thanks to [Rickard Edén](https://github.com/neph1) for the LoRA code and their general contributions to this growing FramePack scene!

Thanks to [Zehong Ma](https://github.com/Zehong-Ma) for [MagCache](https://github.com/Zehong-Ma/MagCache): Fast Video Generation with Magnitude-Aware Cache!

Thanks to everyone who has joined the Discord, reported a bug, sumbitted a PR, or helped with testing!

    @article{zhang2025framepack,
        title={Packing Input Frame Contexts in Next-Frame Prediction Models for Video Generation},
        author={Lvmin Zhang and Maneesh Agrawala},
        journal={Arxiv},
        year={2025}
    }

    @misc{zhang2025packinginputframecontext,
        title={Packing Input Frame Context in Next-Frame Prediction Models for Video Generation},
        author={Lvmin Zhang and Maneesh Agrawala},
        year={2025},
        eprint={2504.12626},
        archivePrefix={arXiv},
        primaryClass={cs.CV},
        url={https://arxiv.org/abs/2504.12626}
    }
