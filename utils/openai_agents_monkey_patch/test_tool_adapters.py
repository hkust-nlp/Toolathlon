import asyncio
import unittest

from agents import FunctionTool, RunContextWrapper
from agents._run_impl import ResponseFunctionToolCall
from agents.mcp.util import MCPUtil
from mcp.types import CallToolResult, TextContent, Tool as MCPTool

from utils.openai_agents_monkey_patch.custom_mcp_util import coerce_mcp_arguments
from utils.openai_agents_monkey_patch.custom_run_impl import (
    _canonicalize_tool_call,
    _resolve_registered_tool_name,
)
from utils.openai_agents_monkey_patch.tool_name_aliases import (
    alias_function_tools,
    rewrite_tool_name_references,
    to_model_mcp_tool_name,
    to_model_tool_choice,
    to_model_tool_name,
    validate_model_tool_names,
)
from utils.task_runner.termination_checkers import default_termination_checker


def _function_tool(name: str) -> FunctionTool:
    async def invoke(context, arguments):
        return "ok"

    return FunctionTool(
        name=name,
        description=f"description for {name}",
        params_json_schema={"type": "object", "properties": {}},
        on_invoke_tool=invoke,
        strict_json_schema=False,
    )


class ToolNameResolverTests(unittest.TestCase):
    def test_exact_name_wins(self):
        self.assertEqual(
            _resolve_registered_tool_name(
                "notion_API_post_search",
                ["notion-API-post-search", "notion_API_post_search"],
            ),
            "notion_API_post_search",
        )

    def test_unique_underscore_alias_resolves_hyphenated_tool(self):
        self.assertEqual(
            _resolve_registered_tool_name(
                "notion_API_post_search",
                ["notion-API-post-search"],
            ),
            "notion-API-post-search",
        )

    def test_ambiguous_alias_is_rejected(self):
        self.assertIsNone(
            _resolve_registered_tool_name(
                "service_a_b",
                ["service-a_b", "service_a-b"],
            )
        )

    def test_tool_call_is_copied_with_canonical_registered_name(self):
        tool_call = ResponseFunctionToolCall(
            arguments='{}',
            call_id='call-id',
            name='local_claim_done',
            type='function_call',
        )

        canonical = _canonicalize_tool_call(tool_call, ['local-claim_done'])

        self.assertEqual(canonical.name, 'local-claim_done')
        self.assertEqual(tool_call.name, 'local_claim_done')

    def test_alias_collision_between_handoff_and_function_is_not_rewritten(self):
        tool_call = ResponseFunctionToolCall(
            arguments='{}',
            call_id='call-id',
            name='service_a_b',
            type='function_call',
        )

        canonical = _canonicalize_tool_call(
            tool_call,
            ['service-a_b', 'service_a-b'],
        )

        self.assertIs(canonical, tool_call)

    def test_legacy_hyphen_name_resolves_to_underscore_registration(self):
        self.assertEqual(
            _resolve_registered_tool_name(
                "local-claim_done",
                ["local_claim_done"],
            ),
            "local_claim_done",
        )


class ModelToolNameAliasTests(unittest.TestCase):
    def test_model_names_replace_every_hyphen(self):
        self.assertEqual(
            to_model_mcp_tool_name("yahoo-finance", "get-price_history"),
            "yahoo_finance_get_price_history",
        )
        self.assertEqual(to_model_tool_name("local-claim_done"), "local_claim_done")

    def test_local_function_tool_is_cloned_without_changing_callback(self):
        original = _function_tool("local-python-execute")

        aliased, aliases = alias_function_tools([original])

        self.assertEqual(aliases, {"local-python-execute": "local_python_execute"})
        self.assertIsNot(aliased[0], original)
        self.assertEqual(aliased[0].name, "local_python_execute")
        self.assertEqual(original.name, "local-python-execute")
        self.assertIs(aliased[0].on_invoke_tool, original.on_invoke_tool)
        self.assertIs(aliased[0].params_json_schema, original.params_json_schema)
        self.assertEqual(aliased[0].description, original.description)
        self.assertEqual(aliased[0].strict_json_schema, original.strict_json_schema)

    def test_local_alias_executes_original_callback(self):
        calls = []

        async def invoke(context, arguments):
            calls.append((context, arguments))
            return "ok"

        original = FunctionTool(
            name="local-claim_done",
            description="done",
            params_json_schema={"type": "object", "properties": {}},
            on_invoke_tool=invoke,
            strict_json_schema=False,
        )
        aliased, _ = alias_function_tools([original])
        context = RunContextWrapper(context={})

        result = asyncio.run(aliased[0].on_invoke_tool(context, "{}"))

        self.assertEqual(result, "ok")
        self.assertEqual(calls, [(context, "{}")])

    def test_prompt_rewrite_only_changes_complete_tool_names(self):
        prompt = (
            "Call local-claim_done, but preserve "
            "local-claim_done-extra and state-of-the-art."
        )

        rewritten = rewrite_tool_name_references(
            prompt,
            {"local-claim_done": "local_claim_done"},
        )

        self.assertEqual(
            rewritten,
            "Call local_claim_done, but preserve "
            "local-claim_done-extra and state-of-the-art.",
        )

    def test_prompt_rewrite_preserves_non_string_instructions(self):
        def instruction_callable(context, agent):
            return "local-claim_done"

        self.assertIs(
            rewrite_tool_name_references(
                instruction_callable,
                {"local-claim_done": "local_claim_done"},
            ),
            instruction_callable,
        )

    def test_prompt_rewrite_handles_legacy_typo_next_to_chinese_text(self):
        self.assertEqual(
            rewrite_tool_name_references(
                "可以调用local-claim-done工具完成任务",
                {"local-claim-done": "local_claim_done"},
            ),
            "可以调用local_claim_done工具完成任务",
        )

    def test_model_name_validation_rejects_normalization_collision(self):
        aliased, _ = alias_function_tools(
            [_function_tool("service-a"), _function_tool("service_a")]
        )

        with self.assertRaisesRegex(ValueError, "duplicate model-facing names"):
            validate_model_tool_names(aliased)

    def test_named_tool_choice_is_normalized(self):
        self.assertEqual(
            to_model_tool_choice("local-python-execute"),
            "local_python_execute",
        )
        self.assertEqual(to_model_tool_choice("auto"), "auto")

    def test_termination_matches_legacy_stop_name_to_model_alias(self):
        self.assertTrue(
            default_termination_checker(
                content="",
                recent_tools=[
                    {"function": {"name": "local_claim_done", "arguments": "{}"}}
                ],
                check_target="agent",
                agent_stop_tools=["local-claim_done"],
            )
        )

    def test_termination_matches_legacy_call_to_model_stop_name(self):
        self.assertTrue(
            default_termination_checker(
                content="",
                recent_tools=[
                    {"function": {"name": "local-claim_done", "arguments": "{}"}}
                ],
                check_target="agent",
                agent_stop_tools=["local_claim_done"],
            )
        )


class MCPModelAliasTests(unittest.IsolatedAsyncioTestCase):
    async def test_mcp_alias_calls_original_backend_tool_name(self):
        class FakeServer:
            name = "yahoo-finance"

            def __init__(self):
                self.calls = []

            async def call_tool(self, name, arguments):
                self.calls.append((name, arguments))
                return CallToolResult(
                    content=[TextContent(type="text", text="ok")],
                    isError=False,
                )

        server = FakeServer()
        raw_tool = MCPTool(
            name="get-price_history",
            description="get prices",
            inputSchema={"type": "object", "properties": {}},
        )
        function_tool = MCPUtil.to_function_tool(raw_tool, server, False)

        self.assertEqual(
            function_tool.name,
            "yahoo_finance_get_price_history",
        )
        await function_tool.on_invoke_tool(RunContextWrapper(context={}), "{}")
        self.assertEqual(server.calls, [("get-price_history", {})])


class MCPArgumentCoercionTests(unittest.TestCase):
    def setUp(self):
        self.schema = {
            "type": "object",
            "properties": {
                "page_id": {"type": "string"},
                "properties": {"type": "object", "additionalProperties": True},
                "filter": {"type": "object"},
                "filter_properties": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "page_size": {"type": "integer"},
                "enabled": {"type": "boolean"},
            },
        }

    def test_notion_container_and_scalar_arguments_are_repaired(self):
        arguments = {
            "page_id": "1234",
            "properties": '{"Status":{"select":{"name":"Applied"}}}',
            "filter": '{"property":"Status","select":{"equals":"Checking"}}',
            "filter_properties": '["title","status"]',
            "page_size": "30",
            "enabled": "false",
        }

        self.assertEqual(
            coerce_mcp_arguments(arguments, self.schema),
            {
                "page_id": "1234",
                "properties": {"Status": {"select": {"name": "Applied"}}},
                "filter": {
                    "property": "Status",
                    "select": {"equals": "Checking"},
                },
                "filter_properties": ["title", "status"],
                "page_size": 30,
                "enabled": False,
            },
        )

    def test_string_fields_and_malformed_json_are_unchanged(self):
        arguments = {
            "page_id": '{"still":"a string"}',
            "filter": "{malformed",
            "page_size": "thirty",
        }

        self.assertEqual(coerce_mcp_arguments(arguments, self.schema), arguments)

    def test_schema_that_allows_string_is_not_coerced(self):
        schema = {
            "type": "object",
            "properties": {
                "value": {
                    "anyOf": [
                        {"type": "object"},
                        {"type": "string"},
                    ]
                }
            },
        }
        arguments = {"value": '{"keep":"string"}'}

        self.assertEqual(coerce_mcp_arguments(arguments, schema), arguments)

    def test_already_typed_values_are_preserved(self):
        arguments = {
            "properties": {"Status": {"select": {"name": "Applied"}}},
            "filter_properties": ["title"],
            "page_size": 20,
            "enabled": True,
        }

        self.assertEqual(coerce_mcp_arguments(arguments, self.schema), arguments)


if __name__ == "__main__":
    unittest.main()
