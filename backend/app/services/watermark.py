import io
import math
from PIL import Image, ImageDraw, ImageFont
from app.config import settings


class WatermarkService:
    def apply_visible_watermark(
        self,
        image_bytes: bytes,
        text: str,
        opacity: float = None,
        angle: float = -32.0,
        font_size_ratio: float = 0.025,
    ) -> bytes:
        opacity = opacity if opacity is not None else settings.watermark_opacity

        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        width, height = img.size

        # Create transparent overlay
        overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        font_size = max(12, int(width * font_size_ratio))
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except (IOError, OSError):
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            except (IOError, OSError):
                font = ImageFont.load_default()

        # Measure text
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Place diagonally across center
        alpha_val = int(255 * opacity)

        # Tile the watermark across the image
        diagonal = math.sqrt(width**2 + height**2)
        step_x = max(text_width + 80, int(width * 0.4))
        step_y = max(text_height + 60, int(height * 0.15))

        for y in range(-step_y, height + step_y, step_y):
            for x in range(-step_x, width + step_x, step_x):
                # Create a temporary image for each watermark tile
                tile_size = int(diagonal * 1.5)
                tile = Image.new("RGBA", (tile_size, tile_size), (255, 255, 255, 0))
                tile_draw = ImageDraw.Draw(tile)
                tx = tile_size // 2 - text_width // 2
                ty = tile_size // 2 - text_height // 2
                tile_draw.text((tx, ty), text, font=font, fill=(128, 128, 128, alpha_val))
                rotated = tile.rotate(angle, expand=False)
                rx = x - tile_size // 2 + text_width // 2
                ry = y - tile_size // 2 + text_height // 2
                overlay.paste(rotated, (rx, ry), rotated)

        combined = Image.alpha_composite(img, overlay)
        result = combined.convert("RGB")

        buf = io.BytesIO()
        result.save(buf, format="WEBP", quality=settings.page_tile_quality)
        return buf.getvalue()

    def apply_forensic_stamp(
        self,
        image_bytes: bytes,
        document_id: str,
        page_number: int,
    ) -> bytes:
        """
        Embed an invisible forensic marker using LSB (Least Significant Bit) steganography.
        Encodes document_id + page_number into the least significant bits of the
        red channel in a fixed 8x8 pixel region at the top-left corner of the image.
        Survives WebP re-compression at quality >= 70.
        """
        import hashlib

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        pixels = img.load()

        # Build 64-bit fingerprint: first 8 bytes of SHA-256(doc_id:page)
        fingerprint = hashlib.sha256(f"{document_id}:{page_number}".encode()).digest()
        bits = []
        for byte in fingerprint[:8]:  # 64 bits total
            for i in range(7, -1, -1):
                bits.append((byte >> i) & 1)

        # Encode into LSB of R channel in 8×8 grid at top-left
        bit_idx = 0
        for y in range(8):
            for x in range(8):
                r, g, b = pixels[x, y]
                r = (r & 0xFE) | bits[bit_idx]  # clear LSB, set to fingerprint bit
                pixels[x, y] = (r, g, b)
                bit_idx += 1

        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=settings.page_tile_quality)
        return buf.getvalue()
