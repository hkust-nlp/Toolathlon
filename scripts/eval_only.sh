

# uv run -m tasks.finalpoolcn.git-milestone.preprocess.main \
# --agent_workspace recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpoolcn/English-SingleUserTurn-git-milestone/workspace

uv run -m tasks.finalpoolcn.git-milestone.evaluation.main \
--res_log_file recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpoolcn/English-SingleUserTurn-git-milestone/log.json \
--agent_workspace recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpoolcn/English-SingleUserTurn-git-milestone/workspace \
--groundtruth_workspace tasks/finalpoolcn/git-milestone/groundtruth_workspace