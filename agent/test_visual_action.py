import asyncio
import httpx
from agent.visual_action import explain_creative_visuals


class FakeClient:
    def __init__(self, status, body):
        self.status, self.body, self.seen = status, body, {}

    def _client(self):
        def handler(request: httpx.Request):
            self.seen["ctype"] = request.headers.get("content-type", "")
            return httpx.Response(self.status, json=self.body)
        return httpx.AsyncClient(base_url="http://test", transport=httpx.MockTransport(handler),
                                 headers={"Content-Type": "application/json"})


def run(client, data=b"x"):
    return asyncio.run(explain_creative_visuals(client, data, "a.png", "image/png"))


def test_findings_are_explained_and_upload_is_multipart():
    fc = FakeClient(201, {"extraction": {"visual": {
        "processed": True, "checks_run": ["visual_colour"], "skipped": ["visual_typography: fonts can only be read from PDFs"],
        "errors": [], "findings": [{"category": "visual_colour", "status": "fail", "matched_text": "Off-palette colour",
                                    "explanation": "Too far from brand blue.", "suggested_fix": "Use the brand palette."}]}}})
    out = run(fc)
    assert fc.seen["ctype"].startswith("multipart/form-data")
    assert "Problem (brand colour)" in out and "Not checked" in out


def test_unprocessed_is_never_a_pass():
    out = run(FakeClient(201, {"extraction": {"visual": {"processed": False, "errors": ["could not open file"]}}}))
    assert "not a pass" in out and "No issues" not in out


def test_backend_error_is_never_a_pass():
    assert "not a pass" in run(FakeClient(500, {"detail": "boom"}))


def test_empty_findings_not_fully_compliant():
    out = run(FakeClient(201, {"extraction": {"visual": {"processed": True, "checks_run": ["visual_colour"],
                                                         "findings": [], "skipped": [], "errors": []}}}))
    assert "does not mean the creative is fully compliant" in out


def test_no_file():
    assert "No file" in run(FakeClient(201, {}), data=b"")
