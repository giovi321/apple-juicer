"""The photo thumbnail helper downscales images to JPEG and rejects non-images."""

from __future__ import annotations


def test_thumbnail_jpeg_downscales(tmp_path):
    from PIL import Image

    from api.routes.artifacts_photos import _thumbnail_jpeg

    src = tmp_path / "big.png"
    Image.new("RGB", (1000, 800), (10, 120, 200)).save(src)

    data = _thumbnail_jpeg(src, 240)
    assert data is not None
    assert data[:3] == b"\xff\xd8\xff"  # JPEG magic

    from io import BytesIO

    thumb = Image.open(BytesIO(data))
    assert max(thumb.size) <= 240


def test_thumbnail_jpeg_rejects_non_image(tmp_path):
    from api.routes.artifacts_photos import _thumbnail_jpeg

    src = tmp_path / "notimage.bin"
    src.write_bytes(b"this is not an image")
    assert _thumbnail_jpeg(src, 240) is None
