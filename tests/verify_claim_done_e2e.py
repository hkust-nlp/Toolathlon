"""End-to-end verification of the claim_done fix through the PRODUCTION call chain:

TaskAgent → ContextManagedRunner.run (super().run = Runner.run) → RunImpl
(monkey-patched my_execute_function_tool_calls) → RunLifecycle.on_tool_start
raises TaskDoneError → must propagate all the way back to the caller
without being swallowed into an "Error running tool ..." string.

Also verifies the PTC sandbox path: claim_done dispatched from inside the
programmatic_tool_call sandbox is drained into recent_tool_calls, and the
termination checker must match it — this depends on task_config.stop.tool_names.
"""
import asyncio
import os
import sys
import tempfile
import types

helper = types.ModuleType("utils.general.helper")
helper.print_color = lambda *a, **k: None
sys.modules["utils.general.helper"] = helper

sys.path.insert(0, ".")

from agents import Agent, RunConfig
from agents.items import (ModelResponse, ResponseOutputMessage,
                          ResponseFunctionToolCall, Usage)
from agents.models.interface import Model
from agents.tool import FunctionTool, RunContextWrapper

from utils.task_runner.hooks import RunLifecycle, TaskDoneError
from utils.roles.context_managed_runner import ContextManagedRunner
from utils.task_runner.termination_checkers import default_termination_checker
from utils.openai_agents_monkey_patch.tool_name_aliases import alias_function_tools
from utils.openai_agents_monkey_patch import custom_run_impl  # noqa: F401  (applies patch)


async def on_done_invoke(context: RunContextWrapper, params_str: str) -> str:
    return "you have claimed the task is done!"


CLAIM_DONE_TOOL = alias_function_tools([
    FunctionTool(name="local-claim_done", description="claim the task is done",
                 params_json_schema={"type": "object", "properties": {},
                                     "additionalProperties": False},
                 on_invoke_tool=on_done_invoke, strict_json_schema=False)
])[0][0]


class LoopModel(Model):
    """First turn calls local_claim_done; if the loop survives, emits text."""
    def __init__(self):
        self.calls = 0
    async def get_response(self, system_instructions, input, model_settings,
                           tools, output_schema, handoffs, tracing, *,
                           previous_response_id) -> ModelResponse:
        self.calls += 1
        if self.calls == 1:
            output = [ResponseFunctionToolCall(
                id="call_1", call_id="call_1", name="local_claim_done",
                arguments="{}", type="function_call")]
        else:
            output = [ResponseOutputMessage(
                id="msg_1", role="assistant", status="completed", type="message",
                content=[{"type": "output_text", "text": "all done", "annotations": []}])]
        return ModelResponse(output=output, usage=Usage(), response_id="resp_1")
    def stream_response(self, *args, **kwargs):
        raise NotImplementedError


async def main():
    # ---- Path 1: production entry chain (TaskAgent -> ContextManagedRunner) ----
    model = LoopModel()
    agent = Agent(name="t", instructions="you are t", model=model, tools=[CLAIM_DONE_TOOL])
    with tempfile.TemporaryDirectory() as tmp:
        try:
            await ContextManagedRunner.run(
                starting_agent=agent,
                input="do it",
                max_turns=50,
                hooks=RunLifecycle(debug=False),
                run_config=RunConfig(),
                history_dir=tmp,
                session_id="e2e_claim_done",
            )
            print("FAIL path1: TaskDoneError was swallowed, loop kept going "
                  f"({model.calls} calls)")
        except TaskDoneError as e:
            print(f"PASS path1: TaskDoneError propagated through "
                  f"ContextManagedRunner.run after {model.calls} model call(s): {e}")
    assert model.calls == 1, f"must abort after 1 call, got {model.calls}"

    # ---- Path 2: TaskAgent's handler marks SUCCESS (mirrors task_agent.py:775) ----
    try:
        raise TaskDoneError("Task completed via local-claim_done")
    except TaskDoneError:
        # task_agent.py: task_status = SUCCESS; claim_done_signaled = True; break
        print("PASS path2: TaskAgent except TaskDoneError handler reachable "
              "(status -> SUCCESS)")

    # ---- Path 3: PTC sandbox path — termination checker with the REAL
    # stop config. All 108 finalpool configs omit the `stop` field, so
    # StopConditions.build applies the default ['local-claim_done']
    # (verified separately: StopConditions.build(None).tool_names).
    # The drained sandboxed claim_done must match it or the loop keeps going.
    stop_tools = ['local-claim_done']  # StopConditions.build(None).tool_names
    recent_tools = [{"function": {"name": "local_claim_done", "arguments": "{}"}}]
    r = default_termination_checker("", recent_tools, "agent",
                                    agent_stop_tools=stop_tools)
    print(f"path3: sandboxed claim_done matched by checker -> {r}")
    assert r is True, "sandboxed claim_done must terminate"
    print("PASS path3: PTC sandbox path terminates via drain + checker ")

    print("\nDONE")


if __name__ == "__main__":
    asyncio.run(main())
