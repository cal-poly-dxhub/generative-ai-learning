"""Custom production tools for the art swarm.

Every tool produces a PNG as its primary output so the art_director can review
it with image_reader. Source files (.txt, .svg, .bmp) are saved alongside.
"""

import base64
import glob
import json
import math
import os
import random
import re
import textwrap
import boto3
from PIL import Image, ImageDraw, ImageFont
from strands import tool

SWARM_DIR = os.path.dirname(os.path.dirname(__file__))
DRAFTS_DIR = os.path.join(SWARM_DIR, "drafts")
OUTPUT_DIR = os.path.join(SWARM_DIR, "output")

STABLE_DIFFUSION_MODEL_ID = "stability.sd3-5-large-v1:0"


def _create_filename(prompt: str) -> str:
    words = re.sub(r"[^a-z0-9\s]", "", prompt.lower()).split()[:6]
    return "_".join(words) if words else "image"


@tool
def generate_draft_image(prompt: str, output_dir: str = "", negative_prompt: str = "") -> str:
    """Generate an image using Stable Diffusion on Bedrock and save it as a draft.

    Unlike the built-in generate_image (which always saves to ./output/), this tool
    saves to the specified directory — defaulting to ./drafts/ for canvas use.

    Args:
        prompt: Detailed description of the image to generate.
        output_dir: Directory to save the image. Defaults to ./drafts/.
        negative_prompt: What to avoid in the image.

    Returns:
        File path of the saved PNG image.
    """
    out = _ensure_dir(output_dir or DRAFTS_DIR)

    client = boto3.client("bedrock-runtime", region_name="us-west-2")
    body = {
        "prompt": prompt,
        "output_format": "png",
        "mode": "text-to-image",
        "seed": random.randint(0, 2**32 - 1),
    }
    if negative_prompt:
        body["negative_prompt"] = negative_prompt

    try:
        response = client.invoke_model(
            modelId=STABLE_DIFFUSION_MODEL_ID,
            body=json.dumps(body),
        )
        result = json.loads(response["body"].read())
        image_data = base64.b64decode(result["images"][0])

        filename = _create_filename(prompt)
        png_path = os.path.join(out, f"{filename}.png")
        i = 1
        while os.path.exists(png_path):
            png_path = os.path.join(out, f"{filename}_{i}.png")
            i += 1

        with open(png_path, "wb") as f:
            f.write(image_data)

        return f"Draft image saved to {png_path}"

    except Exception as e:
        img = Image.new("RGB", (512, 512), "#2D1B69")
        draw = ImageDraw.Draw(img)
        font = _get_monospace_font(14)
        draw.text((20, 20), f"[Draft placeholder — SD unavailable]\n\n{prompt[:300]}", fill="white", font=font)
        png_path = os.path.join(out, f"{_create_filename(prompt)}.png")
        img.save(png_path)
        return f"Draft placeholder saved to {png_path} (Stable Diffusion error: {e})"


def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def _get_monospace_font(size=14):
    for font_name in [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Courier.dfont",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    ]:
        if os.path.exists(font_name):
            try:
                return ImageFont.truetype(font_name, size)
            except Exception:
                continue
    return ImageFont.load_default()


@tool
def generate_ascii_png(
    description: str,
    width: int = 80,
    style: str = "block",
    output_dir: str = "",
    filename: str = "",
) -> str:
    """Generate ASCII art and render it as a PNG image.

    Creates ASCII art from a description, saves raw text (.txt), then renders
    the text onto a dark background using a monospace font and saves as PNG.

    Args:
        description: What to create as ASCII art — be specific about shapes and layout.
        width: Character width of the output (default 80).
        style: 'block' uses block chars, 'gradient' uses density chars, 'text' uses pyfiglet large text.
        output_dir: Directory to save to. Defaults to ./drafts/.
        filename: Base name for output files (without extension). Defaults to 'ascii_art'.

    Returns:
        File paths of the PNG and TXT outputs.
    """
    out = _ensure_dir(output_dir or DRAFTS_DIR)
    base = filename or "ascii_art"
    height = width // 2

    if style == "text":
        try:
            import pyfiglet
            words = description.split()[:4]
            text = " ".join(words)
            ascii_text = pyfiglet.figlet_format(text, font="banner3", width=width)
        except ImportError:
            ascii_text = _generate_block_art(description, width, height)
    elif style == "gradient":
        ascii_text = _generate_gradient_art(description, width, height)
    else:
        ascii_text = _generate_block_art(description, width, height)

    txt_path = os.path.join(out, f"{base}.txt")
    with open(txt_path, "w") as f:
        f.write(ascii_text)

    png_path = os.path.join(out, f"{base}.png")
    _render_text_to_png(ascii_text, png_path)

    return f"PNG: {png_path} | Source: {txt_path}"


def _generate_block_art(description, width, height):
    chars = "  ░░▒▒▓▓██"
    random.seed(hash(description) % 2**32)
    lines = []
    for y in range(height):
        line = ""
        for x in range(width):
            cx, cy = width / 2, height / 2
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            max_dist = math.sqrt(cx**2 + cy**2)
            norm = dist / max_dist
            noise = random.random() * 0.3
            idx = min(int((norm + noise) * len(chars)), len(chars) - 1)
            line += chars[idx]
        lines.append(line)
    return "\n".join(lines)


def _generate_gradient_art(description, width, height):
    chars = " .:-=+*#%@"
    random.seed(hash(description) % 2**32)
    lines = []
    for y in range(height):
        line = ""
        for x in range(width):
            wave = math.sin(x * 0.1 + y * 0.05) * 0.5 + 0.5
            noise = random.random() * 0.2
            idx = min(int((wave + noise) * len(chars)), len(chars) - 1)
            line += chars[idx]
        lines.append(line)
    return "\n".join(lines)


def _render_text_to_png(text, path, font_size=12, bg_color="#1a1a2e", fg_color="#e0e0e0"):
    font = _get_monospace_font(font_size)
    lines = text.split("\n")
    bbox = font.getbbox("M")
    char_w = bbox[2] - bbox[0]
    char_h = int((bbox[3] - bbox[1]) * 1.3)

    max_line_len = max(len(l) for l in lines) if lines else 1
    img_w = char_w * max_line_len + 40
    img_h = char_h * len(lines) + 40

    img = Image.new("RGB", (img_w, img_h), bg_color)
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        draw.text((20, 20 + i * char_h), line, fill=fg_color, font=font)
    img.save(path)


@tool
def generate_svg_png(
    svg_code: str,
    output_dir: str = "",
    width: int = 800,
    height: int = 600,
    filename: str = "",
) -> str:
    """Save SVG code and render a PNG version for visual review.

    Takes raw SVG markup, saves the .svg source file, then renders to PNG
    using Pillow as a fallback (draws basic shapes from the SVG).

    Args:
        svg_code: Complete SVG markup string (must start with <svg).
        output_dir: Directory to save to. Defaults to ./drafts/.
        width: PNG render width in pixels.
        height: PNG render height in pixels.
        filename: Base name for output files (without extension). Defaults to 'vector_art'.

    Returns:
        File paths of the PNG and SVG outputs.
    """
    out = _ensure_dir(output_dir or DRAFTS_DIR)
    base = filename or "vector_art"

    svg_path = os.path.join(out, f"{base}.svg")
    with open(svg_path, "w") as f:
        f.write(svg_code)

    png_path = os.path.join(out, f"{base}.png")

    try:
        import cairosvg
        cairosvg.svg2png(bytestring=svg_code.encode(), write_to=png_path,
                         output_width=width, output_height=height)
    except ImportError:
        img = Image.new("RGB", (width, height), "#ffffff")
        draw = ImageDraw.Draw(img)
        font = _get_monospace_font(14)
        wrapped = textwrap.fill(f"[SVG saved — install cairosvg for PNG render]\n\n{svg_code[:500]}", 80)
        draw.text((20, 20), wrapped, fill="#333333", font=font)
        draw.rectangle([5, 5, width - 5, height - 5], outline="#cccccc", width=2)
        img.save(png_path)

    return f"PNG: {png_path} | Source: {svg_path}"


@tool
def generate_bitmap(
    description: str,
    width: int = 64,
    height: int = 64,
    colors: int = 16,
    output_dir: str = "",
    filename: str = "",
) -> str:
    """Generate pixel art as BMP with a PNG copy for review.

    Creates pixel art at low resolution with a limited color palette
    for a deliberately pixelated retro aesthetic.

    Args:
        description: What to render as pixel art — describe shapes and colors.
        width: Pixel width (keep small: 32-128 for pixel art look).
        height: Pixel height.
        colors: Number of colors in palette (8, 16, or 32).
        output_dir: Directory to save to. Defaults to ./drafts/.
        filename: Base name for output files (without extension). Defaults to 'pixel_art'.

    Returns:
        File paths of the PNG and BMP outputs.
    """
    out = _ensure_dir(output_dir or DRAFTS_DIR)
    base = filename or "pixel_art"
    random.seed(hash(description) % 2**32)

    palettes = {
        8: ["#1a1c2c", "#5d275d", "#b13e53", "#ef7d57",
            "#ffcd75", "#a7f070", "#38b764", "#29366f"],
        16: ["#1a1c2c", "#5d275d", "#b13e53", "#ef7d57",
             "#ffcd75", "#a7f070", "#38b764", "#29366f",
             "#3b5dc9", "#41a6f6", "#73eff7", "#f4f4f4",
             "#94b0c2", "#566c86", "#333c57", "#000000"],
        32: ["#1a1c2c", "#5d275d", "#b13e53", "#ef7d57",
             "#ffcd75", "#a7f070", "#38b764", "#29366f",
             "#3b5dc9", "#41a6f6", "#73eff7", "#f4f4f4",
             "#94b0c2", "#566c86", "#333c57", "#000000",
             "#ff004d", "#ffa300", "#ffec27", "#00e436",
             "#29adff", "#83769c", "#ff77a8", "#ffccaa",
             "#ab5236", "#008751", "#5f574f", "#c2c3c7",
             "#7e2553", "#ff8426", "#1d2b53", "#fff1e8"],
    }
    pal = palettes.get(min(colors, 32), palettes[16])

    img = Image.new("RGB", (width, height))
    for y in range(height):
        for x in range(width):
            cx, cy = width / 2, height / 2
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            max_dist = math.sqrt(cx**2 + cy**2)
            norm = dist / max_dist
            noise = random.random() * 0.3
            idx = min(int((norm + noise) * len(pal)), len(pal) - 1)
            img.putpixel((x, y), _hex_to_rgb(pal[idx]))

    scale = max(4, 512 // max(width, height))
    img_scaled = img.resize((width * scale, height * scale), Image.NEAREST)

    bmp_path = os.path.join(out, f"{base}.bmp")
    png_path = os.path.join(out, f"{base}.png")
    img_scaled.save(bmp_path, "BMP")
    img_scaled.save(png_path, "PNG")

    return f"PNG: {png_path} | Source: {bmp_path}"


def _hex_to_rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


@tool
def list_artwork_files(directory: str = "") -> str:
    """List all artwork files in the specified directory.

    Args:
        directory: Directory to scan. Defaults to ./output/.

    Returns:
        JSON manifest of all files with paths, sizes, and formats.
    """
    scan_dir = directory or OUTPUT_DIR
    if not os.path.isdir(scan_dir):
        return f"Directory not found: {scan_dir}"

    manifest = []
    for f in sorted(os.listdir(scan_dir)):
        filepath = os.path.join(scan_dir, f)
        if os.path.isfile(filepath):
            manifest.append({
                "filename": f,
                "path": filepath,
                "size_bytes": os.path.getsize(filepath),
                "format": os.path.splitext(f)[1].lstrip("."),
            })
    return json.dumps(manifest, indent=2) if manifest else "No files found."
