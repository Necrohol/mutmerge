import os
import time
from PIL import Image, ImageDraw, ImageFont

# 1. Define ASCII characters ordered by darkness (from light to dark)
ASCII_CHARS = [' ', '.', ':', '-', '=', '+', '*', '#', '%', '@']

# Function to clear terminal (cross-platform)
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# Function to convert image to ASCII art
def image_to_ascii(image, char_set=ASCII_CHARS, output_width=100):
    # Resize image to fit desired output width while maintaining aspect ratio
    width, height = image.size
    aspect_ratio = height / width
    output_height = int(output_width * aspect_ratio * 0.55) # Adjust for character aspect ratio

    image = image.resize((output_width, output_height)).convert('L') # Convert to grayscale

    pixels = image.getdata()
    ascii_str = ""
    for pixel_value in pixels:
        # Map pixel brightness to ASCII character
        index = int((pixel_value / 255) * (len(char_set) - 1))
        ascii_str += char_set[index]

    # Add newlines to format as a picture
    ascii_rows = [ascii_str[i:i + output_width] for i in range(0, len(ascii_str), output_width)]
    return "\n".join(ascii_rows)

# Function to convert ASCII art to a Pillow image
def ascii_to_image(ascii_art_str, font_size=10, char_width=6, char_height=10):
    lines = ascii_art_str.split('\n')
    width = max(len(line) for line in lines) * char_width
    height = len(lines) * char_height
    
    img = Image.new('L', (width, height), color=255) # White background
    d = ImageDraw.Draw(img)
    try:
        # You might need to specify a font that supports various ASCII characters
        font = ImageFont.truetype("arial.ttf", font_size) 
    except IOError:
        font = ImageFont.load_default()

    for i, line in enumerate(lines):
        d.text((0, i * char_height), line, fill=0, font=font) # Black text
    return img

# --- Main Morphing Logic Placeholder ---
# This is where the core morphing algorithm would go.
# For simplicity, let's just define two hardcoded ASCII art frames.
# In a real scenario, these might come from image_to_ascii conversions.

human_ascii_art = r"""
     O
    /|\
    / \
"""

six_arm_human_ascii_art = r"""
    \ O /
    --|--
   / | \
  / / \ \
"""

def simple_ascii_morph(start_art, end_art, steps=10):
    start_lines = start_art.strip().split('\n')
    end_lines = end_art.strip().split('\n')

    max_height = max(len(start_lines), len(end_lines))
    max_width = max(len(line) for line in start_lines + end_lines)

    # Pad shorter lines/art with spaces
    padded_start = [line.ljust(max_width) for line in start_lines]
    padded_end = [line.ljust(max_width) for line in end_lines]
    while len(padded_start) < max_height:
        padded_start.append(' ' * max_width)
    while len(padded_end) < max_height:
        padded_end.append(' ' * max_width)

    frames = []
    for step in range(steps + 1):
        current_frame_lines = []
        for r in range(max_height):
            current_line = []
            for c in range(max_width):
                char_start = padded_start[r][c]
                char_end = padded_end[r][c]

                # Simple character interpolation:
                # For a more advanced morph, you'd map characters to a "density" value
                # and interpolate the density, then map back to a character.
                # Or, as discussed, use image-based morphing.
                if step < steps / 2:
                    # Transition from start to end
                    current_line.append(char_start if step % 2 == 0 else char_end) # Very basic toggle
                else:
                    # Transition from end to start (could be more gradual)
                    current_line.append(char_end if step % 2 == 0 else char_start)

                # For a real morph, you'd try to figure out a "path" for each character
                # or rely on pixel-based interpolation.
                # This is a very simplistic "flicker" effect.
            current_frame_lines.append("".join(current_line))
        frames.append("\n".join(current_frame_lines))
    return frames

# --- The more robust image-based morphing would replace simple_ascii_morph ---
# Let's simulate by just having a few predefined states for the example.
# In a real application, you'd generate these morphing frames.

# Pre-defined frames for demonstration purposes
frame1 = r"""
     O
    /|\
    / \
"""

frame2 = r"""
    \ O /
    --|--
   / | \
  / / \ \
"""

frame3 = r"""
    / O \
    --|--
   \ | /
    \ / \
"""

# Simulate morphing by displaying a sequence of frames
morph_frames = [frame1, frame2, frame1, frame3, frame2, frame3, frame1] 

# Add a welcome message before the animation
print("Welcome to mutmerge, a mutating USE=myflags emerge -bavgk wapper /etc...")
time.sleep(2) # Pause for a moment

for i, frame in enumerate(morph_frames):
    clear_screen()
    print(f"Frame {i+1}/{len(morph_frames)}")
    print(frame)
    time.sleep(0.5) # Adjust speed of animation

#print("\nAnimation complete!")