import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from governed_agent import ToolPolicy, ToolRequest


class ToolPolicyTests(unittest.TestCase):
    def test_overlapping_groups_are_rejected(self):
        with self.assertRaises(ValueError):
            ToolPolicy(allowed=frozenset({"duplicate"}), denied=frozenset({"duplicate"}))

    def test_allowlisted_tool_still_mentions_authorization(self):
        decision = ToolPolicy().decide(ToolRequest("search_knowledge", {}, "Answer question"))

        self.assertEqual("allow", decision.outcome)
        self.assertIn("authorization", decision.reason)


if __name__ == "__main__":
    unittest.main()
