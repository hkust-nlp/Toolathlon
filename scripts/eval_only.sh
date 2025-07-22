

# uv run -m tasks.finalpoolcn.hk-top-conf.preprocess.main \
# --agent_workspace recorded_trajectories_v2/run1/claude-4-sonnet-0514/finalpoolcn/English-SingleUserTurn-hk-top-conf/workspace

uv run -m tasks.finalpoolcn.hk-top-conf.evaluation.main \
--res_log_file dumps/run1/claude-4-sonnet-0514/finalpoolcn/SingleUserTurn-hk-top-conf/log.json \
--agent_workspace dumps/run1/claude-4-sonnet-0514/finalpoolcn/SingleUserTurn-hk-top-conf/workspace \
--groundtruth_workspace tasks/finalpoolcn/hk-top-conf/groundtruth_workspace