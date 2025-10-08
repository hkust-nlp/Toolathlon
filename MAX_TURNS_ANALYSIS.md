# Max Turns 处理逻辑分析

## 问题描述

当 agent 超过 `max_turns` 后，任务直接被判定为失败，不会运行 evaluation 代码，导致：
1. 即使 agent 在达到 max turns 前已完成任务，也不会被评估
2. `evaluation` 字段在日志中为 `null`
3. 无法知道任务是否实际完成

## Max Turns 配置和使用

### 1. Max Turns 的设置方式

#### 方式 1: 在 TaskConfig 中设置

**文件**: `utils/data_structures/task_config.py`

```python
@dataclass
class TaskConfig:
    max_turns: int = None  # 默认值
```

**配置来源**:
- 任务配置 JSON 文件中的 `max_turns` 字段
- 如果未指定，会使用默认值（通常在 `global_task_config` 中）

#### 方式 2: Single Turn Mode

**文件**: `utils/roles/task_agent.py:716`

```python
max_turns = 1 if self.single_turn_mode else self.task_config.max_turns
```

**说明**:
- `single_turn_mode=True` 时，强制 `max_turns=1`
- 否则使用 `task_config.max_turns`

### 2. Max Turns 的使用位置

#### 主循环控制

**文件**: `utils/roles/task_agent.py:722-826`

```python
async def run_interaction_loop(self, root_task_dir):
    """运行交互循环"""
    max_turns = 1 if self.single_turn_mode else self.task_config.max_turns

    # 主循环：检查是否达到最大轮次
    while self.stats["interaction_turns"] < max_turns:
        # ... 运行一轮交互 ...
        self.stats["interaction_turns"] += 1

    # 循环结束后检查
    if self.stats["interaction_turns"] >= max_turns:
        self._debug_print(f"Maximum turns ({max_turns}) reached")
        self.task_status = TaskStatus.MAX_TURNS_REACHED  # 设置状态
```

#### 内部迭代控制

**文件**: `utils/roles/task_agent.py:561`

```python
self.conversation = Conversation(
    agent=self.agent,
    workspace=str(self.task_config.agent_workspace),
    persistence_dir=str(persistence_dir),
    max_iteration_per_run=self.agent_config.tool.max_inner_turns,  # 内部最大迭代次数
    # ...
)
```

**说明**:
- `max_turns`: 外层用户-agent交互轮次（user message + agent response）
- `max_inner_turns`: 单次 `conversation.run()` 内部的最大迭代次数（tool calls 等）

## 超过 Max Turns 的处理流程

### 1. 状态设置

当达到 `max_turns` 时：

```python
# utils/roles/task_agent.py:824-826
if self.stats["interaction_turns"] >= max_turns:
    self._debug_print(f"Maximum turns ({max_turns}) reached")
    self.task_status = TaskStatus.MAX_TURNS_REACHED
```

### 2. 状态更新到 StatusManager

**文件**: `utils/roles/task_agent.py:978-1006`

```python
async def run(self) -> TaskStatus:
    try:
        # ... 运行交互循环 ...
        await self.run_interaction_loop(...)

        # 根据 task_status 更新 running 状态
        if self.task_status not in [TaskStatus.MAX_TURNS_REACHED, TaskStatus.INTERRUPTED]:
            self.task_status = TaskStatus.SUCCESS
            self.status_manager.update_running("done")
        elif self.task_status == TaskStatus.MAX_TURNS_REACHED:
            self.status_manager.update_running("max_turn_exceeded")  # ❌ 关键点

    except Exception as e:
        # 异常处理
        if self.task_status == TaskStatus.MAX_TURNS_REACHED:
            self.status_manager.update_running("max_turn_exceeded")
        else:
            self.task_status = TaskStatus.FAILED
            self.status_manager.update_running("fail")
```

**关键**: `running` 状态被设置为 `"max_turn_exceeded"`

### 3. Evaluation 执行条件

**文件**: `utils/evaluation/evaluator.py:35-40`

```python
@staticmethod
async def evaluate_one(dump_line: Dict[str, Any]) -> Dict[str, Any]:
    task_status = dump_line['status']

    # ❌ 只有 SUCCESS 才会评估！
    if task_status != TaskStatus.SUCCESS.value:
        return {
            "pass": None,  # 返回 None，不是 True/False
            "details": f"Task status: {task_status}, only SUCCESS counts as pass; pass is null"
        }

    # 只有 status == SUCCESS 才会运行 eval_command
    if eval_command is not None:
        command = f"{eval_command} {args}"
        output, error, returncode = await run_command(command, debug=True)
        # ...
```

**关键逻辑**:
1. ✅ `task_status == SUCCESS` → 运行 evaluation 命令
2. ❌ `task_status == MAX_TURNS_REACHED` → **不运行** evaluation，返回 `{"pass": None}`
3. ❌ `task_status == FAILED` → **不运行** evaluation，返回 `{"pass": None}`

### 4. 数据流程

```
Task Run
  ↓
达到 max_turns
  ↓
task_status = TaskStatus.MAX_TURNS_REACHED
  ↓
status_manager.update_running("max_turn_exceeded")
  ↓
保存日志: {"status": "MAX_TURNS_REACHED", ...}
  ↓
Evaluation
  ↓
检查: task_status != SUCCESS
  ↓
返回: {"pass": None, "details": "..."}  ← ❌ 不运行 evaluation 命令
```

## 问题根源

### 核心问题

**Evaluation 只在 `task_status == SUCCESS` 时执行**

这意味着：
- Agent 即使在第 99 轮完成了任务
- 但在第 100 轮达到 `max_turns`
- 状态被设置为 `MAX_TURNS_REACHED` 而非 `SUCCESS`
- Evaluation 直接返回 `{"pass": None}`，**不检查实际结果**

### 设计缺陷

1. **Max Turns 和任务完成的混淆**
   - Max Turns 应该是一个**资源限制**（防止无限循环）
   - 不应该等同于**任务失败**
   - Agent 可能在达到 max turns 前已经完成任务

2. **缺少任务完成信号**
   - 没有明确的"任务完成"工具或信号
   - 依赖 agent 主动停止或达到 stop condition
   - `finish` 工具被过滤掉了（之前的 kind 字段问题）

3. **Evaluation 逻辑过于严格**
   - 只检查 `task_status == SUCCESS`
   - 不考虑其他可能完成任务的情况
   - 应该**始终**运行 evaluation 命令（除非明确失败）

## 实际影响

### 统计数据

从 `analysis/data/full_stat_1_run.jsonl` 中可以看到大量案例：

```json
{
  "status_data": {
    "preprocess": "done",
    "running": "max_turn_exceeded",  // ← 超过 max turns
    "evaluation": null                // ← 没有评估结果
  },
  "actual_turn": 100
}
```

**示例任务**:
- `travel-expense-reimbursement`: 100 turns, evaluation = null
- `canvas-art-manager`: 100 turns, evaluation = null
- `interview-report`: 100 turns, evaluation = null
- `huggingface-upload`: 100 turns, evaluation = null

### 可能的情况

1. **任务确实未完成**: Agent 一直在尝试但没成功
2. **任务已完成但继续执行**: Agent 完成了但没有明确停止
3. **接近完成**: 在第 99 轮几乎完成，第 100 轮被截断

**问题**: 现有逻辑**无法区分**这些情况！

## 解决方案

### 方案 1: Evaluation 无条件执行（推荐）

**修改**: `utils/evaluation/evaluator.py:35-40`

```python
@staticmethod
async def evaluate_one(dump_line: Dict[str, Any]) -> Dict[str, Any]:
    task_config = TaskConfig.from_dict(dump_line['config'])
    task_status = dump_line['status']

    # 准备评估信息
    res_log_file = task_config.log_file
    agent_workspace = task_config.agent_workspace
    groundtruth_workspace = task_config.evaluation.groundtruth_workspace
    eval_command = task_config.evaluation.evaluation_command
    launch_time = task_config.launch_time

    # ✅ 改进: 对所有非 FAILED 的状态都尝试评估
    should_evaluate = task_status not in [
        TaskStatus.FAILED.value,
        TaskStatus.INTERRUPTED.value
    ]

    if not should_evaluate:
        return {
            "pass": None,
            "details": f"Task status: {task_status}, skipping evaluation"
        }

    # 运行 evaluation 命令（包括 MAX_TURNS_REACHED）
    if eval_command is not None:
        args = f"--res_log_file {res_log_file} --agent_workspace {agent_workspace} --groundtruth_workspace {groundtruth_workspace} --launch_time \"{launch_time}\""
        command = f"{eval_command} {args}"
        output, error, returncode = await run_command(command, debug=True)

        print("== Evaluation STDOUT ==")
        print(output)
        print("== Evaluation STDERR ==")
        print(error)

        if returncode != 0:
            return {
                "pass": False,
                "failure": output,
                "task_status": task_status  # ✅ 添加原始状态
            }

        # ✅ 评估通过，但标注是否超过 max turns
        return {
            "pass": True,
            "details": "Evaluation passed",
            "task_status": task_status,
            "note": "Completed within max_turns" if task_status == TaskStatus.SUCCESS.value
                    else "Completed but exceeded max_turns"
        }

    # 没有 evaluation 命令，只能根据状态判断
    return {
        "pass": task_status == TaskStatus.SUCCESS.value,
        "details": f"No evaluation command, status: {task_status}",
        "task_status": task_status
    }
```

**优点**:
- ✅ 超过 max turns 也会运行 evaluation
- ✅ 可以发现"已完成但超时"的任务
- ✅ 提供更准确的评估结果
- ✅ 保留原始 task_status 信息

**缺点**:
- 可能评估未完成的工作空间

### 方案 2: 使用 `finish` 工具标记完成

**前提**: 修复 `kind` 字段问题（已完成）

**修改**: `utils/roles/task_agent.py`

在 stop_conditions 中添加对 `finish` 工具的检测：

```python
# 检查是否调用了 finish 工具
if event_type == EventType.Action:
    action = event.action
    if hasattr(action, 'kind') and action.kind == 'FinishAction':
        self._debug_print("Agent called finish tool")
        self.task_status = TaskStatus.SUCCESS
        # 提前退出循环
        break
```

**优点**:
- ✅ Agent 主动标记任务完成
- ✅ 明确的任务完成语义
- ✅ 不依赖 max turns

**缺点**:
- 需要 agent 正确使用 `finish` 工具
- 当前 `finish` 被过滤掉了

### 方案 3: 增加 Max Turns 值

**简单方案**: 提高 `max_turns` 限制

```python
# 在 task config 或 global_task_config 中
{
  "max_turns": 200  // 从 100 增加到 200
}
```

**优点**:
- ✅ 最简单
- ✅ 给 agent 更多时间完成任务

**缺点**:
- ❌ 治标不治本
- ❌ 增加成本和时间
- ❌ 仍然可能达到新的限制

### 方案 4: 两层检查机制（综合方案）

1. **Max Turns 作为软限制**: 达到后设置标志，但继续评估
2. **Hard Timeout 作为硬限制**: 绝对时间或步数限制

```python
# utils/roles/task_agent.py

async def run_interaction_loop(self, root_task_dir):
    max_turns = self.task_config.max_turns
    hard_limit = self.task_config.max_turns * 2  # 硬限制是软限制的 2 倍

    while self.stats["interaction_turns"] < hard_limit:
        # ... 运行交互 ...

        self.stats["interaction_turns"] += 1

        # 软限制：标记但继续
        if self.stats["interaction_turns"] == max_turns:
            self._debug_print(f"Soft limit ({max_turns}) reached, will stop at {hard_limit}")
            # 不设置 MAX_TURNS_REACHED，继续运行

        # 检查停止条件
        if self._should_stop():
            self.task_status = TaskStatus.SUCCESS
            break

    # 硬限制：强制停止
    if self.stats["interaction_turns"] >= hard_limit:
        self._debug_print(f"Hard limit ({hard_limit}) reached")
        self.task_status = TaskStatus.MAX_TURNS_REACHED
```

## 推荐实施方案

### 短期修复（立即实施）

**修改**: `utils/evaluation/evaluator.py:35-62`

```python
@staticmethod
async def evaluate_one(dump_line: Dict[str, Any]) -> Dict[str, Any]:
    task_config = TaskConfig.from_dict(dump_line['config'])
    task_status = dump_line['status']

    res_log_file = task_config.log_file
    agent_workspace = task_config.agent_workspace
    groundtruth_workspace = task_config.evaluation.groundtruth_workspace
    eval_command = task_config.evaluation.evaluation_command
    launch_time = task_config.launch_time

    print(f"Evaluating task with status: {task_status}")

    # ✅ 只跳过明确失败的状态，对 MAX_TURNS_REACHED 也进行评估
    if task_status in [TaskStatus.FAILED.value, TaskStatus.INTERRUPTED.value]:
        return {
            "pass": None,
            "details": f"Task status: {task_status}, skipping evaluation",
            "task_status": task_status
        }

    # 运行 evaluation（包括 SUCCESS 和 MAX_TURNS_REACHED）
    if eval_command is not None:
        args = f"--res_log_file {res_log_file} --agent_workspace {agent_workspace} --groundtruth_workspace {groundtruth_workspace} --launch_time \"{launch_time}\""
        command = f"{eval_command} {args}"
        output, error, returncode = await run_command(command, debug=True)

        print("== Evaluation STDOUT ==")
        print(output)
        print("== Evaluation STDERR ==")
        print(error)

        if returncode != 0:
            return {
                "pass": False,
                "failure": output,
                "task_status": task_status
            }

        # Evaluation 通过
        return {
            "pass": True,
            "details": "Evaluation checks passed",
            "task_status": task_status,
            "exceeded_max_turns": task_status == TaskStatus.MAX_TURNS_REACHED.value
        }

    # 没有 evaluation 命令
    return {
        "pass": task_status == TaskStatus.SUCCESS.value,
        "details": f"No evaluation command, judged by status: {task_status}",
        "task_status": task_status
    }
```

### 长期改进

1. **使用 `finish` 工具**
   - 移除 `finish` 工具的过滤
   - 在 stop_conditions 中检测 `finish` 调用
   - 主动完成任务而非被动等待 max turns

2. **改进停止条件**
   - 添加更智能的停止检测
   - 检测 agent 重复行为（可能卡住）
   - 检测任务完成信号（如调用 `local-claim_done`）

3. **分离资源限制和任务状态**
   - Max Turns 只是资源限制
   - 任务成功/失败由 evaluation 决定
   - 添加 `RESOURCE_EXHAUSTED` 状态（区别于 `FAILED`）

## 验证修复

### 测试场景

1. **正常完成**: Agent 在 max_turns 内完成 → `pass=True`, `task_status=SUCCESS`
2. **超时但完成**: Agent 超过 max_turns 但任务已完成 → `pass=True`, `task_status=MAX_TURNS_REACHED`, `exceeded_max_turns=True`
3. **超时未完成**: Agent 超过 max_turns 且任务未完成 → `pass=False`, `task_status=MAX_TURNS_REACHED`
4. **明确失败**: Agent 遇到错误 → `pass=None`, `task_status=FAILED`

### 预期改进

```json
// 修复前
{
  "status_data": {
    "preprocess": "done",
    "running": "max_turn_exceeded",
    "evaluation": null  // ❌ 无评估结果
  }
}

// 修复后（任务实际已完成）
{
  "status_data": {
    "preprocess": "done",
    "running": "max_turn_exceeded",
    "evaluation": true  // ✅ 通过评估！
  },
  "evaluation_details": {
    "pass": true,
    "exceeded_max_turns": true
  }
}
```

## 配置建议

### Max Turns 设置指南

根据任务复杂度设置合理的 `max_turns`:

| 任务类型 | 推荐 Max Turns | 说明 |
|---------|---------------|------|
| 简单任务（读取、查询） | 10-20 | 1-2 次交互即可完成 |
| 中等任务（数据处理、文件操作） | 50-100 | 需要多步骤操作 |
| 复杂任务（多系统集成、大量操作） | 100-200 | 需要大量交互和调试 |
| 探索性任务（搜索、分析） | 200+ | 可能需要大量尝试 |

### 监控指标

建议监控：
- `actual_turn` / `max_turns` 比率（接近 1.0 说明可能需要更多轮次）
- 超过 max_turns 但 evaluation 通过的比例
- 平均完成轮次

## 总结

**问题本质**:
- `max_turns` 被错误地当作任务失败标志
- Evaluation 只对 `SUCCESS` 状态执行，跳过 `MAX_TURNS_REACHED`
- 导致可能已完成的任务被标记为失败

**解决方案**:
- 短期：修改 `evaluator.py`，对 `MAX_TURNS_REACHED` 也运行 evaluation
- 长期：使用 `finish` 工具明确标记任务完成，分离资源限制和任务状态

**预期效果**:
- ✅ 发现更多实际完成的任务
- ✅ 更准确的评估结果
- ✅ 更好地理解 agent 性能
