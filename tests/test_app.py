import io
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image  # noqa: E402

import app as app_module  # noqa: E402


def png_bytes(color=(255, 0, 0), size=(20, 20)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    buf.seek(0)
    return buf


class QrImageTest(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()

    def test_healthz(self):
        res = self.client.get("/healthz")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["status"], "ok")

    def test_index_ok(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_api_qr_png(self):
        res = self.client.get("/api/qr?text=https://example.com")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "image/png")
        self.assertTrue(res.data.startswith(b"\x89PNG"))

    def test_api_qr_empty(self):
        res = self.client.get("/api/qr")
        self.assertEqual(res.status_code, 400)

    def test_qr_page(self):
        res = self.client.post("/qr", data={"text": "hello"})
        body = res.get_data(as_text=True)
        self.assertIn("data:image/png;base64,", body)

    def test_convert_png_to_jpeg(self):
        res = self.client.post(
            "/convert",
            data={"file": (png_bytes(), "test.png"), "target": "jpeg"},
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "image/jpeg")
        self.assertTrue(res.data.startswith(b"\xff\xd8"))

    def test_convert_jpeg_to_png(self):
        buf = io.BytesIO()
        Image.new("RGB", (10, 10), (0, 0, 255)).save(buf, format="JPEG")
        buf.seek(0)
        res = self.client.post(
            "/convert",
            data={"file": (buf, "test.jpg"), "target": "png"},
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data.startswith(b"\x89PNG"))

    def test_convert_invalid_file(self):
        res = self.client.post(
            "/convert",
            data={"file": (io.BytesIO(b"not an image"), "x.png"), "target": "png"},
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 400)

    def test_convert_too_large(self):
        big = io.BytesIO(b"\x89PNG" + b"0" * (app_module.MAX_UPLOAD + 1))
        res = self.client.post(
            "/convert",
            data={"file": (big, "big.png"), "target": "png"},
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 400)


if __name__ == "__main__":
    unittest.main()
