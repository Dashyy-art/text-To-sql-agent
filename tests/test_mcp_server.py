"""Tests du serveur MCP, via un client MCP en mémoire (sans BigQuery)."""

import asyncio

from mcp.client.client import Client

from climate_sql_agent.mcp_server import server as server_module

EXPECTED_TOOLS = {"list_tables", "describe_table", "run_sql", "check_result"}


def list_tools():
    async def _list():
        async with Client(server_module.server) as client:
            return await client.list_tools()

    return asyncio.run(_list()).tools


def call_tool(name, arguments):
    async def _call():
        async with Client(server_module.server) as client:
            return await client.call_tool(name, arguments)

    return asyncio.run(_call())


def test_server_exposes_the_four_tools():
    assert {tool.name for tool in list_tools()} == EXPECTED_TOOLS


def test_every_tool_has_a_description_and_is_read_only():
    for tool in list_tools():
        assert tool.description, f"{tool.name} n'a pas de description"
        assert tool.annotations.read_only_hint


def test_run_sql_refuses_write_without_calling_bigquery(monkeypatch):
    # object() n'a aucune méthode : si BigQuery était appelé, le test planterait.
    monkeypatch.setattr(server_module, "_client", object())
    result = call_tool("run_sql", {"query": "DROP TABLE marts.mart_heatwaves"})
    assert result.is_error
    assert "lecture" in result.content[0].text


def test_check_result_tool_returns_warnings():
    result = call_tool("check_result", {"columns": ["observation_year"], "rows": [[1890]]})
    assert not result.is_error
    assert '"ok": false' in result.content[0].text
