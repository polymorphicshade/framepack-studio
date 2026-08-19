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
- **Continue From Last Frame**: Download the final frame of a finished video as a PNG, or load it straight into Start Frame to carry the generation on from where it ended
- **Timestamped Prompts**: Define different prompts for specific time segments in your video
- **Prompt Blending**: Define the blending time between timestamped prompts
- **LoRA Support**: Works with most (all?) Hunyuan Video LoRAs
- **Queue System**: Process multiple generation jobs without blocking the interface. Import and export queues. Set **Generations per queue submission** above 1 to enqueue several takes of the same inputs at once, each with its own random seed.
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

## Performance

Generation time is dominated by the transformer: `steps` x sections forward passes, plus the cost of streaming the model between CPU and GPU on cards that cannot hold it. The levers below are ordered by how much they typically matter.

**Install an attention library.** `diffusers_helper/models/hunyuan_video_packed.py` picks the fastest backend it can import, in the order SageAttention > Flash Attention > xFormers > PyTorch SDPA, and prints which one it chose at startup. Check that line before tuning anything else - if it says "No attention library found", you are on SDPA. SDPA already uses the flash kernel on Ampere and later, so the gain is useful rather than dramatic; SageAttention's INT8 attention is the one that pulls clearly ahead.

Nothing installs these automatically. On Windows, `install.bat` offers SageAttention and/or Flash Attention during setup and installs prebuilt wheels matched to the torch, CUDA and Python versions it just set up - re-run it and pick option 1 or 3 to add them to an existing install. They deliberately stay out of `requirements.txt`, because the right wheel depends on the exact torch/CUDA/Python/OS combination, and a generic `pip install` either fails to build or drags in a torch that replaces the CUDA build the installer pinned.

The Docker image installs SageAttention 1.0.6 itself, right after torch - it is pure Triton, so it needs no CUDA toolkit on the runtime base image. This only applies to an image you build yourself (`docker compose up -d --build`); a plain `up` pulls the published image, which has no attention library. Build with `--build-arg INSTALL_SAGEATTENTION=false` to skip it.

**Queue jobs on one model back to back.** A job reuses the transformer already in memory when it wants the same model as the job before it, so a run of generations on one model loads it once. Switching model type between jobs, or letting the idle unload run, means the next job reloads it.

**Keep more of the transformer resident.** The model is bf16 and larger than 24GB, so on a 24GB card it is streamed layer by layer every section. **GPU Memory Preservation** in the Settings tab is how much VRAM is left free when loading it - lower means more layers stay on the GPU and less is copied over PCIe each section. 6GB is the safe default; on a 24GB card with nothing else running, 4-5GB is usually still safe and measurably faster. Back it off if you hit OOM at your resolution. Note the offload that runs before VAE decoding frees to a fixed 8GB regardless of this setting, so it only affects the sampling phase.

**Leave caching on.** **MagCache** is the default caching strategy and already skips a good fraction of steps. Raising **MagCache Threshold** and **Max Consecutive Skips**, or lowering **Retention Ratio**, skips more steps for less fidelity - worth tuning per model, and the fastest single knob after attention.

**Skip intermediate videos on long generations.** **Intermediate video interval** in the Settings tab controls how often the in-progress clip is written. Each write re-encodes the whole video generated so far, so the total encode cost grows with the square of the section count, and with **Clean up video files** on every intermediate is deleted at the end anyway. 1 (the default) writes one per section; set it to 4 or 0 for long jobs, at the cost of live previews.

**Sharing the GPU with other apps.** **Unload models from VRAM when idle** in the Settings tab moves every model back to system RAM and releases the VRAM once the queue is empty, so another application can use the card while this one sits idle. It waits for the queue to drain rather than unloading between queued jobs, and the next job pays the reload cost at its start. **Free VRAM Now**, next to it, does the same thing on demand between jobs.

**Leave CFG Scale at 1.0.** Anything above 1.0 adds a second transformer pass per step - it doubles generation time. The distilled guidance scale is the one to adjust instead.

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
