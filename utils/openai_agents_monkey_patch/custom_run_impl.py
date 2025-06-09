# monkeypatch
from __future__ import annotations
from agents._run_impl import *
from agents.util import _coro, _error_tracing

# 定义你的替代函数
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
        func_tool: FunctionTool, tool_call: ResponseFunctionToolCall
    ) -> Any:
        with function_span(func_tool.name) as span_fn:
            # logger.warning("我在这里！！！！！！！！！！！！")
            if config.trace_include_sensitive_data:
                span_fn.span_data.input = tool_call.arguments
            try:
                # basially, if the tool has an explicitly stated argument named like `path`
                # we can identify it and stop it before the tool is actually called
                # however, if we cannot do this
                # e.g. the argument is a python code, and the code tries to acces some other files
                # then it is very hard to detect such behaviour
                # and we may need system level sandbox technique to avoid that
                # which is hard on my dev machine

                # we can also have other techniques, see https://www.notion.so/hkust-nlp/Sandbox-20839bdc1c6b8014936ef7c11c57b189
                # however, on my dev machine, this is hard to implement as I donot have sudo previlige ...
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
                # fix: instead of raising an error and destory the whole dialogue, we choose to return this error as a result
                # if isinstance(e, AgentsException):
                #     raise e
                # raise UserError(f"Error running tool {func_tool.name}: {e}") from e
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

# 替换方法
RunImpl.execute_function_tool_calls = my_execute_function_tool_calls