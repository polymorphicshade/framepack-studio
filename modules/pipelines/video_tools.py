import os
import torch
import numpy as np
import traceback
from PIL import Image

from diffusers_helper.utils import save_bcthw_as_mp4, bcthw_to_uint8

@torch.no_grad()
def combine_videos_sequentially_from_tensors(processed_input_frames_np,
                                             generated_frames_pt,
                                             output_path,
                                             target_fps,
                                             crf_value):
    """
    Combines processed input frames (NumPy) with generated frames (PyTorch Tensor) sequentially
    and saves the result as an MP4 video using save_bcthw_as_mp4.

    Args:
        processed_input_frames_np: NumPy array of processed input frames (T_in, H, W_in, C), uint8.
        generated_frames_pt: PyTorch tensor of generated frames (B_gen, C_gen, T_gen, H, W_gen).
                             uint8 [0,255], as history_pixels now arrives from worker.py,
                             or float32 [-1,1] - either is accepted.
        output_path: Path to save the combined video.
        target_fps: FPS for the output combined video.
        crf_value: CRF value for video encoding.

    Returns:
        Path to the combined video, or None if an error occurs.
    """
    try:
        # 1. Convert both sides to BCTHW uint8 [0,255] - the input frames already
        # are uint8, so matching them avoids inflating a long clip to float32 just
        # to concatenate it. (Casting the old float [-1,1] form straight to uint8
        # would clamp every negative value to 0, so convert, don't cast.)
        generated_frames_pt = bcthw_to_uint8(generated_frames_pt)

        # processed_input_frames_np shape: (T_in, H, W_in, C)
        input_frames_pt = torch.from_numpy(processed_input_frames_np) # (T,H,W,C) uint8
        input_frames_pt = input_frames_pt.permute(3, 0, 1, 2) # (C,T,H,W)
        input_frames_pt = input_frames_pt.unsqueeze(0) # (1,C,T,H,W) -> BCTHW

        # Ensure both sides match for concatenation
        input_frames_pt = input_frames_pt.to(device=generated_frames_pt.device, dtype=generated_frames_pt.dtype)

        # 2. Dimension Check (Heights and Widths should match)
        #    They should match, since the input frames should have been processed to match the generation resolution.
        #    But sanity check to ensure no mismatch occurs when the code is refactored.
        if input_frames_pt.shape[3:] != generated_frames_pt.shape[3:]: # Compare (H,W)
            print(f"Warning: Dimension mismatch for sequential combination! Input: {input_frames_pt.shape[3:]}, Generated: {generated_frames_pt.shape[3:]}.")
            print("Attempting to proceed, but this might lead to errors or unexpected video output.")
            # Potentially add resizing logic here if necessary, but for now, assume they match

        # 3. Concatenate Tensors along the time dimension (dim=2 for BCTHW)
        combined_video_pt = torch.cat([input_frames_pt, generated_frames_pt], dim=2)

        # 4. Save
        save_bcthw_as_mp4(combined_video_pt, output_path, fps=target_fps, crf=crf_value)
        print(f"Sequentially combined video (from tensors) saved to {output_path}")
        return output_path
    except Exception as e:
        print(f"Error in combine_videos_sequentially_from_tensors: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def _read_last_frame_rgb(video_path):
    """
    Returns the final frame of a video as an (H, W, 3) uint8 RGB array, or None.

    Tries decord first (it seeks straight to the last frame and is already used to
    read input videos), then OpenCV, then a sequential imageio read as a last
    resort. Each reader is tried in turn because a codec one of them chokes on is
    usually fine for another.
    """
    try:
        import decord
    except ImportError:
        decord = None
    if decord is not None:
        try:
            vr = decord.VideoReader(video_path)
            if len(vr) > 0:
                return vr[len(vr) - 1].asnumpy()
        except Exception:
            print(f"decord could not read the last frame of {video_path}")
            traceback.print_exc()

    try:
        import cv2
    except ImportError:
        cv2 = None
    if cv2 is not None:
        cap = cv2.VideoCapture(video_path)
        try:
            frame = None
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if frame_count > 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count - 1)
                ok, bgr = cap.read()
                if ok:
                    frame = bgr
            if frame is None:
                # Seeking to the end fails on some encodes; read through instead.
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                while True:
                    ok, bgr = cap.read()
                    if not ok:
                        break
                    frame = bgr
            if frame is not None:
                return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        except Exception:
            print(f"OpenCV could not read the last frame of {video_path}")
            traceback.print_exc()
        finally:
            cap.release()

    try:
        import imageio
    except ImportError:
        imageio = None
    if imageio is not None:
        try:
            last = None
            reader = imageio.get_reader(video_path)
            try:
                for frame in reader:
                    last = frame
            finally:
                reader.close()
            if last is not None:
                return np.asarray(last)
        except Exception:
            print(f"imageio could not read the last frame of {video_path}")
            traceback.print_exc()

    return None


def save_last_frame_as_png(video_path, output_dir, filename=None):
    """
    Writes the final frame of a video out as a PNG and returns the path to it.

    The frame is the natural seed for continuing a generation, so it is saved
    losslessly. Returns None if the video cannot be read.
    """
    if not video_path or not os.path.isfile(video_path):
        return None

    frame = _read_last_frame_rgb(video_path)
    if frame is None:
        return None

    frame = np.asarray(frame)
    if frame.ndim == 2:  # grayscale
        frame = np.stack([frame] * 3, axis=-1)
    elif frame.ndim == 3 and frame.shape[2] == 4:  # drop alpha
        frame = frame[:, :, :3]

    if frame.dtype != np.uint8:
        frame = np.clip(frame, 0, 255).astype(np.uint8)

    os.makedirs(output_dir, exist_ok=True)
    if not filename:
        filename = f"{os.path.splitext(os.path.basename(video_path))[0]}_last_frame.png"
    output_path = os.path.join(output_dir, filename)

    Image.fromarray(frame).save(output_path)
    return output_path
