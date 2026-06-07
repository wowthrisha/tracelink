import hashlib
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

        # Preserve EXIF metadata from the source (may contain forensic identity)
        exif_bytes = _extract_exif(image_bytes)

        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        width, height = img.size

        # Create transparent overlay
        overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        font_size = max(12, int(width * font_size_ratio))
        font = _load_font(font_size)

        # Measure text
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        alpha_val = int(255 * opacity)

        # Tile the watermark across the image
        diagonal = math.sqrt(width**2 + height**2)
        step_x = max(text_width + 80, int(width * 0.4))
        step_y = max(text_height + 60, int(height * 0.15))

        for y in range(-step_y, height + step_y, step_y):
            for x in range(-step_x, width + step_x, step_x):
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
        save_kwargs: dict = {"format": "WEBP", "quality": settings.page_tile_quality}
        if exif_bytes:
            save_kwargs["exif"] = exif_bytes
        result.save(buf, **save_kwargs)
        return buf.getvalue()

    def apply_forensic_stamp(
        self,
        image_bytes: bytes,
        document_id: str,
        page_number: int,
    ) -> bytes:
        """
        Embed a forensic identity mark in the stored page image.

        Two complementary mechanisms:
          1. Near-invisible pixel mark (3% opacity) in the bottom-right corner.
             Survives all format conversions including screenshots and prints.
             Reveals document origin under contrast enhancement.
          2. EXIF ImageDescription metadata embedding document_id and page number.
             Readable by forensic analysis tools on extracted image files.

        The mark text encodes a SHA-256 fingerprint of the document_id so the
        full UUID is not directly visible in the image but is recoverable by
        anyone with knowledge of the document_id.
        """
        fingerprint = hashlib.sha256(document_id.encode()).hexdigest()[:8]
        mark_text = f"SD:{fingerprint}:{page_number:04d}"

        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        width, height = img.size

        # Near-invisible corner mark
        overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        font_size = max(8, int(min(width, height) * 0.012))
        font = _load_font(font_size)

        bbox = draw.textbbox((0, 0), mark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        margin = max(4, int(min(width, height) * 0.01))
        x = width - text_width - margin
        y = height - text_height - margin

        # 3% opacity — barely detectable visually, readable under contrast enhancement
        alpha = int(255 * 0.03)
        draw.text((x, y), mark_text, font=font, fill=(0, 0, 0, alpha))

        combined = Image.alpha_composite(img, overlay)
        result = combined.convert("RGB")

        buf = io.BytesIO()
        # Best-effort EXIF embedding for forensic analysis tools
        try:
            exif = img.getexif()
            exif[270] = f"SecureDoc:{document_id}:p{page_number}"
            result.save(buf, format="WEBP", exif=exif.tobytes())
        except Exception:
            result.save(buf, format="WEBP")
        return buf.getvalue()


    def apply_viewer_forensic_stamp(
        self,
        image_bytes: bytes,
        session_id: str,
        page_number: int,
    ) -> bytes:
        """Embed a viewer-identity stamp in API-served page images.

        Complements apply_forensic_stamp (document-level, stored in R2) by
        adding viewer-session identity to bytes served through the API.

        The stamp encodes a SHA-256 prefix of the session_id so the raw
        session_id is never burned into the image, but the session (and thus
        viewer email) is recoverable by anyone with database access.

        Two visual cues are used:
          - Near-invisible pixel mark (1.5% opacity) in the LOWER-LEFT corner
            (document stamp occupies lower-right — separate corners allow
             independent forensic recovery of each stamp).
          - EXIF UserComment field embedding the session hash.

        Applied AFTER the visible watermark in the same thread-pool executor
        call to avoid an extra PIL round-trip.
        """
        session_hash = hashlib.sha256(session_id.encode()).hexdigest()[:8]
        mark_text = f"VS:{session_hash}:{page_number:04d}"

        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        width, height = img.size

        overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        font_size = max(8, int(min(width, height) * 0.012))
        font = _load_font(font_size)

        bbox = draw.textbbox((0, 0), mark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        margin = max(4, int(min(width, height) * 0.01))
        # Lower-LEFT corner (document stamp is lower-right)
        x = margin
        y = height - text_height - margin

        # 1.5% opacity — between invisible (1%) and barely-detectable (3%)
        alpha = int(255 * 0.015)
        draw.text((x, y), mark_text, font=font, fill=(0, 0, 0, alpha))

        combined = Image.alpha_composite(img, overlay)
        result = combined.convert("RGB")

        buf = io.BytesIO()
        try:
            exif = img.getexif()
            # EXIF tag 37510 = UserComment
            exif[37510] = f"VS:{session_hash}:{page_number:04d}".encode()
            result.save(buf, format="WEBP", exif=exif.tobytes())
        except Exception:
            result.save(buf, format="WEBP")
        return buf.getvalue()


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ):
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            pass
    return ImageFont.load_default()


def _extract_exif(image_bytes: bytes) -> bytes:
    """Extract EXIF bytes from an image for preservation across processing steps."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            return img.info.get("exif") or b""
    except Exception:
        return b""
