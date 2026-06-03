import json
import os
import sys
import unittest
from pathlib import Path

try:
    import anyio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except Exception:  # pragma: no cover - optional dependency missing
    anyio = None
    ClientSession = None
    StdioServerParameters = None
    stdio_client = None

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(anyio is None, "mcp optional dependency is not installed")
class McpTransportIntegrationTests(unittest.TestCase):
    def test_stdio_initialize_list_tools_and_call_tool(self):
        async def scenario():
            env = {
                **os.environ,
                "PYTHONPATH": str(ROOT / "src"),
                "G2B_ARTIFACT_DIR": str(ROOT / "artifacts"),
            }
            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "g2b_mcp.server", "--mode", "stdio"],
                cwd=str(ROOT),
                env=env,
            )
            async with stdio_client(params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    init = await session.initialize()
                    self.assertEqual(init.serverInfo.name, "g2b-procurement-intelligence")

                    tools = await session.list_tools()
                    names = {tool.name for tool in tools.tools}
                    self.assertIn("g2b_list_services", names)
                    self.assertIn("g2b_privacy_boundary", names)
                    self.assertGreaterEqual(len(names), 12)

                    result = await session.call_tool("g2b_list_services", {})
                    self.assertFalse(result.isError)
                    payload = json.loads(result.content[0].text)
                    self.assertEqual(payload["service_count"], 18)
                    self.assertTrue(payload["privacy"]["no_raw_rows"])

        anyio.run(scenario)


if __name__ == "__main__":
    unittest.main()
