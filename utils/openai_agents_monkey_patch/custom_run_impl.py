# monkeypatch
from __future__ import annotations
from agents._run_impl import *
from agents.util import _coro, _error_tracing

@classmethod
async def my_execute_function_tool_calls(
    cls,
    *,
    agent: Agent[TContext],
    tool_runs: list[ToolRunFunction],
    hooks: RunHooks[TContext],
    context_wrapper: RunContextWrapper[TContext],
    config: RunConfig,
) -> list[FunctionToolResult]:
    async def run_single_tool(
        func_tool: FunctionTool = None, tool_call: ResponseFunctionToolCall = None
    ) -> Any:
        if func_tool is None:
            return f"Tool {tool_call.name} not found in agent {agent.name}"
        with function_span(func_tool.name) as span_fn:
            if config.trace_include_sensitive_data:
                span_fn.span_data.input = tool_call.arguments
            try:
                _, _, result = await asyncio.gather(
                    hooks.on_tool_start(context_wrapper, agent, func_tool),
                    (
                        agent.hooks.on_tool_start(context_wrapper, agent, func_tool)
                        if agent.hooks
                        else _coro.noop_coroutine()
                    ),
                    func_tool.on_invoke_tool(context_wrapper, tool_call.arguments),
                )
                await asyncio.gather(
                    hooks.on_tool_end(context_wrapper, agent, func_tool, result),
                    (
                        agent.hooks.on_tool_end(context_wrapper, agent, func_tool, result)
                        if agent.hooks
                        else _coro.noop_coroutine()
                    ),
                )
            except Exception as e:
                _error_tracing.attach_error_to_current_span(
                    SpanError(
                        message="Error running tool",
                        data={"tool_name": func_tool.name, "error": str(e)},
                    )
                )
                return f"Error running tool {func_tool.name}: {e}"
            if config.trace_include_sensitive_data:
                span_fn.span_data.output = result
        return result

    tasks = []
    for tool_run in tool_runs:
        function_tool = tool_run.function_tool
        tasks.append(run_single_tool(function_tool, tool_run.tool_call))

    results = await asyncio.gather(*tasks)

    return [
        FunctionToolResult(
            tool=tool_run.function_tool,
            output=result,
            run_item=ToolCallOutputItem(
                output=result,
                raw_item=ItemHelpers.tool_call_output_item(tool_run.tool_call, str(result)),
                agent=agent,
            ),
        )
        for tool_run, result in zip(tool_runs, results)
    ]


@classmethod
def my_process_model_response(
    cls,
    *,
    agent: Agent[Any],
    all_tools: list[Tool],
    response: ModelResponse,
    output_schema: AgentOutputSchemaBase | None,
    handoffs: list[Handoff],
) -> ProcessedResponse:
    items: list[RunItem] = []

    run_handoffs = []
    functions = []
    computer_actions = []
    tools_used: list[str] = []
    handoff_map = {handoff.tool_name: handoff for handoff in handoffs}
    function_map = {tool.name: tool for tool in all_tools if isinstance(tool, FunctionTool)}
    computer_tool = next((tool for tool in all_tools if isinstance(tool, ComputerTool)), None)

    for output in response.output:
        if isinstance(output, ResponseOutputMessage):
            items.append(MessageOutputItem(raw_item=output, agent=agent))
        elif isinstance(output, ResponseFileSearchToolCall):
            items.append(ToolCallItem(raw_item=output, agent=agent))
            tools_used.append("file_search")
        elif isinstance(output, ResponseFunctionWebSearch):
            items.append(ToolCallItem(raw_item=output, agent=agent))
            tools_used.append("web_search")
        elif isinstance(output, ResponseReasoningItem):
            items.append(ReasoningItem(raw_item=output, agent=agent))
        elif isinstance(output, ResponseComputerToolCall):
            items.append(ToolCallItem(raw_item=output, agent=agent))
            tools_used.append("computer_use")
            if not computer_tool:
                _error_tracing.attach_error_to_current_span(
                    SpanError(
                        message="Computer tool not found",
                        data={},
                    )
                )
                raise ModelBehaviorError(
                    "Model produced computer action without a computer tool."
                )
            computer_actions.append(
                ToolRunComputerAction(tool_call=output, computer_tool=computer_tool)
            )
        elif not isinstance(output, ResponseFunctionToolCall):
            logger.warning(f"Unexpected output type, ignoring: {type(output)}")
            continue

        # At this point we know it's a function tool call
        if not isinstance(output, ResponseFunctionToolCall):
            continue

        tools_used.append(output.name)

        # Handoffs
        if output.name in handoff_map:
            items.append(HandoffCallItem(raw_item=output, agent=agent))
            handoff = ToolRunHandoff(
                tool_call=output,
                handoff=handoff_map[output.name],
            )
            run_handoffs.append(handoff)
        # Regular function tool call
        else:
            if output.name not in function_map:
                # add not found tool call processing here
                logger.warning(f"Tool {output.name} not found in agent {agent.name}")
                items.append(ToolCallItem(raw_item=output, agent=agent))
                functions.append(
                        ToolRunFunction(
                            tool_call=output,
                            function_tool=None,
                        )
                    )
                continue            
            items.append(ToolCallItem(raw_item=output, agent=agent))
            functions.append(
                ToolRunFunction(
                    tool_call=output,
                    function_tool=function_map[output.name],
                )
            )

    return ProcessedResponse(
        new_items=items,
        handoffs=run_handoffs,
        functions=functions,
        computer_actions=computer_actions,
        tools_used=tools_used,
    )

RunImpl.process_model_response = my_process_model_response
RunImpl.execute_function_tool_calls = my_execute_function_tool_calls