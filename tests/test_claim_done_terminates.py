"""Integration test: local-claim_done must terminate the agent run immediately.

Validates the fix in utils/task_runner/hooks.py:
- With the RunLifecycle hook, invoking local-claim_done raises TaskDoneError
  out of Runner.run instead of letting the loop continue.
- Without the hook (control), the Runner keeps looping after claim_done and
  only stops on a text-only output — reproducing the production bug.
"""
import asyncio
import sys
import types
from typing import AsyncIterator, Optional

# Stub out utils.general.helper so hooks.py can be imported without the
# container's full dependency set.
helper = types.ModuleType("utils.general.helper")
helper.print_color = lambda *a, **k: None
sys.modules["utils.general.helper"] = helper

sys.path.insert(0, ".")

from agents import Agent, Runner, RunConfig, RunHooks
from agents.items import ModelResponse, ResponseOutputMessage, ResponseFunctionToolCall, Usage
from agents.models.interface import Model, ModelTracing
from agents.tool import FunctionTool, RunContextWrapper

from utils.task_runner.hooks import RunLifecycle, TaskDoneError
from utils.openai_agents_monkey_patch.tool_name_aliases import alias_function_tools


async def on_done_invoke(context: RunContextWrapper, params_str: str) -> str:
    return "you have claimed the task is done!"


CLAIM_DONE_TOOL = alias_function_tools([
    FunctionTool(
        name="local-claim_done",
        description="claim the task is done",
        params_json_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        on_invoke_tool=on_done_invoke,
        strict_json_schema=False,
    )
])[0][0]


class LoopModel(Model):
    """Fake model: first turn calls claim_done, second turn (if reached)
    emits a text-only final output — proving the loop would otherwise go on."""

    def __init__(self, call_claim_done: bool = True):
        self.calls = 0
        self.call_claim_done = call_claim_done

    async def get_response(self, system_instructions, input, model_settings,
                           tools, output_schema, handoffs, tracing, *,
                           previous_response_id) -> ModelResponse:
        self.calls += 1
        if self.call_claim_done and self.calls == 1:
            output = [
                ResponseFunctionToolCall(
                    id="call_1", call_id="call_1", name="local_claim_done",
                    arguments="{}", type="function_call",
                )
            ]
        else:
            output = [ResponseOutputMessage(
                id="msg_1", role="assistant", status="completed", type="message",
                content=[{"type": "output_text", "text": "all done", "annotations": []}],
            )]
        return ModelResponse(output=output, usage=Usage(), response_id="resp_1")

    def stream_response(self, *args, **kwargs) -> AsyncIterator:
        raise NotImplementedError


async def main():
    agent = Agent(name="t", instructions="you are t", model=LoopModel(), tools=[CLAIM_DONE_TOOL])

    # --- Test 1: with the fixed hook, claim_done aborts the run ---
    loop_model = agent.model
    try:
        await Runner.run(
            starting_agent=agent,
            input="do it",
            max_turns=50,
            hooks=RunLifecycle(debug=False),
            run_config=RunConfig(),
        )
        raise AssertionError("EXPECTED TaskDoneError to be raised")
    except TaskDoneError as e:
        print(f"PASS: Runner aborted with TaskDoneError after {loop_model.calls} model call(s): {e}")
    except Exception as e:  # noqa: BLE001
        raise AssertionError(f"FAIL: unexpected exception {type(e).__name__}: {e}")

    # --- Test 2: control — without the hook the loop continues past claim_done ---
    control_model = LoopModel()
    control_agent = Agent(name="t2", instructions="you are t", model=control_model,
                          tools=[CLAIM_DONE_TOOL])
    result = await Runner.run(
        starting_agent=control_agent,
        input="do it",
        max_turns=50,
        hooks=RunHooks(),  # plain hooks: no claim_done handling
        run_config=RunConfig(),
    )
    print(f"PASS: control loop continued ({control_model.calls} model calls) and returned "
          f"final output: {result.final_output!r}")

    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
