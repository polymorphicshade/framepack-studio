import re
from dataclasses import dataclass
from typing import List, Optional


# The one definition of a timestamp section: [2s: text] or [0s-2s: text].
# The parser and the linter both use it, so they can never disagree about what
# counts as a valid timestamp.
TIMESTAMP_PATTERN = r'\[(\d+(?:\.\d+)?s)(?:-(\d+(?:\.\d+)?s))?\s*:\s*(.*?)\]'

# Anything in square brackets, valid timestamp or not.
ANY_BRACKET_PATTERN = r'\[[^\[\]]*\]'


@dataclass
class PromptSection:
    """Represents a section of the prompt with specific timing information"""
    prompt: str
    start_time: float = 0  # in seconds
    end_time: Optional[float] = None  # in seconds, None means until the end


def snap_to_section_boundaries(prompt_sections: List[PromptSection], latent_window_size: int, fps: int = 30) -> List[PromptSection]:
    """
    Adjust timestamps to align with model's internal section boundaries
    
    Args:
        prompt_sections: List of PromptSection objects
        latent_window_size: Size of the latent window used in the model
        fps: Frames per second (default: 30)
        
    Returns:
        List of PromptSection objects with aligned timestamps
    """
    section_duration = (latent_window_size * 4 - 3) / fps  # Duration of one section in seconds
    
    aligned_sections = []
    for section in prompt_sections:
        # Snap start time to nearest section boundary
        aligned_start = round(section.start_time / section_duration) * section_duration
        
        # Snap end time to nearest section boundary
        aligned_end = None
        if section.end_time is not None:
            aligned_end = round(section.end_time / section_duration) * section_duration
        
        # Ensure minimum section length
        if aligned_end is not None and aligned_end <= aligned_start:
            aligned_end = aligned_start + section_duration
            
        aligned_sections.append(PromptSection(
            prompt=section.prompt,
            start_time=aligned_start,
            end_time=aligned_end
        ))
    
    return aligned_sections


def parse_timestamped_prompt(prompt_text: str, total_duration: float, latent_window_size: int = 9, generation_type: str = "Original") -> List[PromptSection]:
    """
    Parse a prompt with timestamps in the format [0s-2s: text] or [3s: text]
    
    Args:
        prompt_text: The input prompt text with optional timestamp sections
        total_duration: Total duration of the video in seconds
        latent_window_size: Size of the latent window used in the model
        generation_type: Type of generation ("Original" or "F1")
        
    Returns:
        List of PromptSection objects with timestamps aligned to section boundaries
        and reversed to account for reverse generation (only for Original type)
    """
    # Default prompt for the entire duration if no timestamps are found
    if "[" not in prompt_text or "]" not in prompt_text:
        return [PromptSection(prompt=prompt_text.strip())]
    
    sections = []
    # Find all timestamp sections [time: text]
    timestamp_pattern = TIMESTAMP_PATTERN
    regular_text = prompt_text
    
    for match in re.finditer(timestamp_pattern, prompt_text):
        start_time_str = match.group(1)
        end_time_str = match.group(2)
        section_text = match.group(3).strip()
        
        # Convert time strings to seconds
        start_time = float(start_time_str.rstrip('s'))
        end_time = float(end_time_str.rstrip('s')) if end_time_str else None
        
        sections.append(PromptSection(
            prompt=section_text,
            start_time=start_time,
            end_time=end_time
        ))
        
        # Remove the processed section from regular_text
        regular_text = regular_text.replace(match.group(0), "")
    
    # If there's any text outside of timestamp sections, use it as a default for the entire duration
    regular_text = regular_text.strip()
    if regular_text:
        sections.append(PromptSection(
            prompt=regular_text,
            start_time=0,
            end_time=None
        ))
    
    # Sort sections by start time
    sections.sort(key=lambda x: x.start_time)
    
    # Fill in end times if not specified
    for i in range(len(sections) - 1):
        if sections[i].end_time is None:
            sections[i].end_time = sections[i+1].start_time
    
    # Set the last section's end time to the total duration if not specified
    if sections and sections[-1].end_time is None:
        sections[-1].end_time = total_duration
    
    # Snap timestamps to section boundaries
    sections = snap_to_section_boundaries(sections, latent_window_size)
    
    # Only reverse timestamps for Original generation type
    if generation_type in ("Original", "Original with Endframe", "Video"):
        # Now reverse the timestamps to account for reverse generation
        reversed_sections = []
        for section in sections:
            reversed_start = total_duration - section.end_time if section.end_time is not None else 0
            reversed_end = total_duration - section.start_time
            reversed_sections.append(PromptSection(
                prompt=section.prompt,
                start_time=reversed_start,
                end_time=reversed_end
            ))
        
        # Sort the reversed sections by start time
        reversed_sections.sort(key=lambda x: x.start_time)
        return reversed_sections
    
    return sections


def get_section_boundaries(latent_window_size: int = 9, count: int = 10) -> str:
    """
    Calculate and format section boundaries for UI display
    
    Args:
        latent_window_size: Size of the latent window used in the model
        count: Number of boundaries to display
        
    Returns:
        Formatted string of section boundaries
    """
    section_duration = (latent_window_size * 4 - 3) / 30
    return ", ".join([f"{i*section_duration:.1f}s" for i in range(count)])


def get_quick_prompts() -> List[List[str]]:
    """
    Get a list of example timestamped prompts
    
    Returns:
        List of example prompts formatted for Gradio Dataset
    """
    prompts = [
        '[0s: The person waves hello] [2s: The person jumps up and down] [4s: The person does a spin]',
        '[0s: The person raises both arms slowly] [2s: The person claps hands enthusiastically]',
        '[0s: Person gives thumbs up] [1.1s: Person smiles and winks] [2.2s: Person shows two thumbs down]',
        '[0s: Person looks surprised] [1.1s: Person raises arms above head] [2.2s-3.3s: Person puts hands on hips]'
    ]
    return [[x] for x in prompts]


def lint_prompt(prompt_text: str, latent_window_size: int = 9, token_count_fn=None,
                token_limit: int = 256, fps: int = 30) -> List[str]:
    """
    Check a prompt for the ways this app silently ignores what was typed.

    Every problem here is one the pipeline handles without complaint, so the only
    symptom is a video that does not match the prompt. Returns a list of plain
    warning strings, empty when the prompt is fine.

    Args:
        prompt_text: The raw prompt as typed.
        latent_window_size: Used to work out the section grid timestamps snap to.
        token_count_fn: Optional callable returning the token count for a string.
                        Without it, the length check is skipped.
        token_limit: Tokens available to each section before truncation.
        fps: Frames per second the section grid is derived from.

    Returns:
        List of warnings, most serious first.
    """
    warnings: List[str] = []

    if not prompt_text or not prompt_text.strip():
        return warnings

    timestamp_matches = list(re.finditer(TIMESTAMP_PATTERN, prompt_text))

    # 1. Bracketed text that looks like an attempted timestamp but did not parse.
    #    The parser leaves it in the prompt verbatim, brackets and all.
    matched_spans = [m.group(0) for m in timestamp_matches]
    leftover_brackets = [
        b for b in re.findall(ANY_BRACKET_PATTERN, prompt_text) if b not in matched_spans
    ]
    looks_like_timestamp = re.compile(r'^\[\s*\d+(?:\.\d+)?\s*(?:-\s*\d+(?:\.\d+)?\s*)?[:s]')
    bad_timestamps = [b for b in leftover_brackets if looks_like_timestamp.match(b)]
    for bad in bad_timestamps:
        warnings.append(
            f"{bad} is not a valid timestamp, so it is being sent to the model as literal text. "
            f"Timestamps need the 's' on every number, e.g. [2s: text] or [0s-2s: text]."
        )

    # 2. Loose text alongside timestamps only covers the run-up to the first one,
    #    which is rarely what someone writing a style prefix expects.
    if timestamp_matches:
        leftover_text = prompt_text
        for m in timestamp_matches:
            leftover_text = leftover_text.replace(m.group(0), "")
        for b in leftover_brackets:
            leftover_text = leftover_text.replace(b, "")
        if leftover_text.strip():
            first_start = min(float(m.group(1).rstrip('s')) for m in timestamp_matches)
            warnings.append(
                f"Text outside the brackets is not applied to the whole video. "
                f"\"{leftover_text.strip()[:40]}\" only covers the part before {first_start:g}s. "
                f"To keep it throughout, repeat it inside each timestamped section."
            )

    # 3. Timestamps that do not land on a section boundary are silently snapped.
    section_duration = (latent_window_size * 4 - 3) / fps
    off_grid = []
    for m in timestamp_matches:
        for group in (1, 2):
            if m.group(group) is None:
                continue
            value = float(m.group(group).rstrip('s'))
            snapped = round(value / section_duration) * section_duration
            if abs(snapped - value) > 0.01:
                off_grid.append(f"{value:g}s becomes {snapped:.1f}s")
    if off_grid:
        warnings.append(
            f"Timestamps snap to the {section_duration:.1f}s section grid: " + ", ".join(off_grid) + "."
        )

    # 4. Each section is encoded on its own, so the token limit applies per
    #    section rather than to the prompt as a whole.
    if token_count_fn is not None:
        section_texts = [m.group(3).strip() for m in timestamp_matches] if timestamp_matches else [prompt_text.strip()]
        for text in section_texts:
            if not text:
                continue
            try:
                count = token_count_fn(text)
            except Exception:
                break
            if count > token_limit:
                warnings.append(
                    f"A section is {count} tokens long and will be truncated at about {token_limit}. "
                    f"Everything past that point is dropped: \"{text[:40]}...\""
                )
                break

    return warnings
