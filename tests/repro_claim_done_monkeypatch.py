"""Repro: with the custom_run_impl monkey patch applied (as main.py does),
TaskDoneError raised by RunLifecycle.on_tool_start is swallowed and turned
into the tool output string "Error running tool ..." instead of aborting."""
import asyncio
import sys
import types

helper = types.ModuleType("utils.general.helper")
helper.print_color = lambda *a, **k: None
sys.modules["utils.general.helper"] = helper

sys.path.insert(0, ".")

from agents import Agent, Runner, RunConfig, RunHooks
from agents.items import ModelResponse, ResponseOutputMessage, ResponseFunctionToolCall, Usage
from agents.models.interface import Model
from agents.tool import FunctionTool, RunContextWrapper

from utils.task_runner.hooks import RunLifecycle, TaskDoneError
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
    model = LoopModel()
    agent = Agent(name="t", instructions="you are t", model=model, tools=[CLAIM_DONE_TOOL])
    try:
        await Runner.run(starting_agent=agent, input="do it", max_turns=50,
                         hooks=RunLifecycle(debug=False), run_config=RunConfig())
        print("FAIL: expected TaskDoneError to abort the run")
    except TaskDoneError as e:
        print(f"PASS: run aborted with TaskDoneError after {model.calls} model call(s): {e}")
    assert model.calls == 1, f"loop should stop after 1 call, got {model.calls}"

if __name__ == "__main__":
    asyncio.run(main())
