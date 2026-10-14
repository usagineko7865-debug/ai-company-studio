import json, logging, os, socket, sys, tempfile, unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_business_lab import meeting, prompts
from ai_business_lab.clients import ApiError, MockClient
from ai_business_lab.config import Config

CFG = Config(True, "", "", "m1", "m2", 150, 155, 0.15, 0.6, 1.0, 5.0, 900)
LOG = logging.getLogger("test"); LOG.addHandler(logging.NullHandler())


class Phase1Tests(unittest.TestCase):
    def test_mock_full_run_no_network(self):
        orig = socket.socket
        socket.socket = lambda *a, **k: (_ for _ in ()).throw(AssertionError("network used!"))
        try:
            res, b = meeting.run_meeting(CFG, prompts.DEFAULT_THEME, False, LOG)
        finally:
            socket.socket = orig
        self.assertEqual(res.status, "completed")
        self.assertEqual(len(res.turns), 6)  # 3往復
        self.assertTrue(all(t.reply.source == "MOCK" for t in res.turns))
        self.assertIsNotNone(res.final_proposal)

    def test_outputs_saved_and_marked_mock(self):
        res, b = meeting.run_meeting(CFG, "t", False, LOG)
        with tempfile.TemporaryDirectory() as d:
            md, js = meeting.save_outputs(res, b, Path(d), "x")
            self.assertIn("MOCK", md.read_text(encoding="utf-8"))
            self.assertTrue(json.loads(js.read_text(encoding="utf-8"))["is_mock"])

    def test_real_flag_ignored_when_env_mock(self):
        _, _, mode = meeting.build_clients(CFG, True)
        self.assertEqual(mode, "MOCK")

    def test_real_without_keys_refused(self):
        with self.assertRaises(meeting.ModeError):
            meeting.build_clients(replace(CFG, use_mock_env=False), True)

    def test_real_needs_flag_even_if_env_false(self):
        c = replace(CFG, use_mock_env=False, openai_key="a", anthropic_key="b")
        self.assertEqual(meeting.build_clients(c, False)[2], "MOCK")
        self.assertEqual(meeting.build_clients(c, True)[2], "REAL")

    def test_budget_stops_before_overspend(self):
        res, b = meeting.run_meeting(replace(CFG, max_budget_jpy=0.0005), "t", False, LOG)
        self.assertEqual(res.status, "stopped")
        self.assertIn("予算", res.stop_reason)
        self.assertLessEqual(b.spent_usd, b.limit_usd)

    def test_api_error_stops_safely_and_saves(self):
        class Boom(MockClient):
            def chat(self, *a):
                raise ApiError("HTTP 500")
        orig = meeting.build_clients
        meeting.build_clients = lambda c, r: (MockClient("openai", "ceo"), Boom("anthropic", "cto"), "MOCK")
        try:
            res, b = meeting.run_meeting(CFG, "t", False, LOG)
        finally:
            meeting.build_clients = orig
        self.assertEqual(res.status, "stopped")
        self.assertEqual(len(res.turns), 1)
        with tempfile.TemporaryDirectory() as d:
            md, js = meeting.save_outputs(res, b, Path(d), "x")
            self.assertTrue(md.exists() and js.exists())

    def test_env_example_first_run_settings(self):
        """.env.example が「初回は50円以内・3往復・公式確認済みモデル」になっている"""
        env = {}
        for line in (Path(__file__).resolve().parents[1] / ".env.example").read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1); env[k] = v.strip()
        self.assertEqual(env["USE_MOCK"], "true")
        self.assertEqual(env["OPENAI_API_KEY"], "")
        self.assertEqual(env["ANTHROPIC_API_KEY"], "")
        self.assertEqual((env["OPENAI_MODEL"], env["ANTHROPIC_MODEL"]), ("gpt-6-luna", "claude-haiku-5-5"))
        self.assertLessEqual(float(env["MAX_BUDGET_JPY"]), 50)
        cfg = replace(CFG, max_budget_jpy=float(env["MAX_BUDGET_JPY"]),
                      openai_in=float(env["OPENAI_INPUT_USD_PER_M"]), openai_out=float(env["OPENAI_OUTPUT_USD_PER_M"]),
                      anthropic_in=float(env["ANTHROPIC_INPUT_USD_PER_M"]), anthropic_out=float(env["ANTHROPIC_OUTPUT_USD_PER_M"]))
        res, b = meeting.run_meeting(cfg, prompts.DEFAULT_THEME, False, LOG)
        self.assertEqual(res.status, "completed")
        self.assertEqual(len(res.turns), 6)
        self.assertLessEqual(b.summary()["estimated_total_jpy"], 50)


if __name__ == "__main__":
    unittest.main()
