import struct
import zlib

from backend.utils.domain_error import DomainError


SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png_chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)


def validate_png(data, max_pixels):
    """Accept bounded 8-bit RGB/RGBA PNG and remove ancillary metadata."""
    if not data.startswith(SIGNATURE):
        raise DomainError("Snapshot must be a PNG image.", 415)
    offset = len(SIGNATURE)
    header = None
    compressed = bytearray()
    state = "header"
    palette_seen = False
    ended = False
    try:
        while offset < len(data):
            if len(data) - offset < 12:
                raise ValueError()
            size = struct.unpack(">I", data[offset:offset + 4])[0]
            kind = data[offset + 4:offset + 8]
            end = offset + 12 + size
            if end > len(data) or any(not (65 <= c <= 90 or 97 <= c <= 122) for c in kind) or kind[2] & 32:
                raise ValueError()
            payload = data[offset + 8:end - 4]
            crc = struct.unpack(">I", data[end - 4:end])[0]
            if zlib.crc32(kind + payload) & 0xffffffff != crc:
                raise ValueError()
            if state == "header" and kind != b"IHDR":
                raise ValueError()
            if kind == b"IHDR":
                if header is not None or size != 13:
                    raise ValueError()
                width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
                if not width or not height or width * height > max_pixels:
                    raise DomainError("Snapshot dimensions exceed the configured limit.", 413)
                if depth != 8 or color not in (2, 6) or compression or filtering or interlace:
                    raise DomainError("Use an 8-bit, non-interlaced RGB or RGBA PNG.", 415)
                header = payload
                state = "before_data"
            elif kind == b"IDAT":
                if state not in ("before_data", "data"):
                    raise ValueError()
                compressed.extend(payload)
                state = "data"
            elif kind == b"IEND":
                if state not in ("data", "after_data") or size or end != len(data):
                    raise ValueError()
                ended = True
                break
            elif kind == b"PLTE":
                if state != "before_data" or palette_seen or not 0 < size <= 768 or size % 3:
                    raise ValueError()
                palette_seen = True
            else:
                if not kind[0] & 32 or kind in (b"acTL", b"fcTL", b"fdAT", b"tRNS"):
                    raise DomainError("Unsupported PNG chunk; send a static RGB/RGBA image.", 415)
                if state == "data":
                    state = "after_data"
            offset = end
        if not ended or not compressed:
            raise ValueError()
        stride = width * (3 if color == 2 else 4) + 1
        expected = stride * height
        inflater = zlib.decompressobj()
        pixels = inflater.decompress(bytes(compressed), expected + 1)
        if len(pixels) != expected or not inflater.eof or inflater.unused_data or inflater.unconsumed_tail:
            raise ValueError()
        if any(pixels[row * stride] > 4 for row in range(height)):
            raise ValueError()
    except (ValueError, zlib.error, struct.error):
        raise DomainError("Invalid or truncated PNG image.", 415)
    return SIGNATURE + png_chunk(b"IHDR", header) + png_chunk(b"IDAT", bytes(compressed)) + png_chunk(b"IEND", b"")
