"""
ADL trace API 测试: GET /api/trace、GET /api/trace/stream 及响应结构.
"""
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.apis.routes import trace


def _make_app() -> FastAPI:
    """仅挂载 trace 路由的测试用 app，避免依赖 database/session。"""
    app = FastAPI()
    app.include_router(trace.router, prefix="/api")
    return app


class TestTraceAPI(unittest.TestCase):
    """GET /api/trace 与 GET /api/trace/stream 的接口测试。"""

    def setUp(self):
        self.app = _make_app()
        self.client = TestClient(self.app)

    def test_get_trace_returns_200(self):
        """GET /api/trace 返回 200."""
        resp = self.client.get("/api/trace")
        self.assertEqual(resp.status_code, 200)

    def test_get_trace_adl_version_and_steps(self):
        """响应为 ADL v1，且 steps 为数组（前端校验条件）。"""
        resp = self.client.get("/api/trace")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("adlVersion"), 1)
        self.assertIsInstance(data.get("steps"), list)
        self.assertGreaterEqual(len(data["steps"]), 1)

    def test_get_trace_steps_have_snapshot_and_events(self):
        """每个 step 包含 snapshot 与 events."""
        resp = self.client.get("/api/trace")
        data = resp.json()
        for i, step in enumerate(data["steps"]):
            self.assertIn("snapshot", step, msg=f"step[{i}]")
            self.assertIn("events", step, msg=f"step[{i}]")
            self.assertIsInstance(step["events"], list)

    def test_get_trace_snapshot_has_pc_registers_flags(self):
        """snapshot 含 pc、lineCounter、registers、flags."""
        resp = self.client.get("/api/trace")
        data = resp.json()
        snap = data["steps"][0]["snapshot"]
        self.assertIn("pc", snap)
        self.assertIn("lineCounter", snap)
        self.assertIn("registers", snap)
        self.assertIn("flags", snap)
        self.assertIn("N", snap["flags"])
        self.assertIn("Z", snap["flags"])

    def test_get_trace_overlay_arrow_has_from_key(self):
        """OverlayArrow 事件在 JSON 中序列化为 \"from\" 而非 \"from_\"（前端依赖）."""
        resp = self.client.get("/api/trace")
        data = resp.json()
        found = False
        for step in data["steps"]:
            for ev in step["events"]:
                if ev.get("type") == "OverlayArrow":
                    self.assertIn("from", ev, msg="OverlayArrow 应包含 'from' 键")
                    self.assertIn("to", ev)
                    found = True
        self.assertTrue(found, "示例 trace 应至少包含一个 OverlayArrow 事件")

    def test_get_trace_optional_code_and_initial_state(self):
        """示例响应可含 code、initialState（有则校验结构）."""
        resp = self.client.get("/api/trace")
        data = resp.json()
        if "code" in data and data["code"] is not None:
            self.assertIsInstance(data["code"], list)
            for line in data["code"]:
                self.assertIn("text", line)
        if "initialState" in data and data["initialState"] is not None:
            init = data["initialState"]
            self.assertIn("registers", init)
            self.assertIn("flags", init)

    def test_get_trace_stream_returns_501(self):
        """GET /api/trace/stream 当前返回 501 Not Implemented."""
        resp = self.client.get("/api/trace/stream")
        self.assertEqual(resp.status_code, 501)
        data = resp.json()
        self.assertIn("detail", data)


if __name__ == "__main__":
    unittest.main()
