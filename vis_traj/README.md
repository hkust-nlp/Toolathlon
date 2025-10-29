# LLM Trajectory Replay

To facilitate viewing the reasoning trajectories of LLMs, we provide this replay tool.

## Prepare Trajectory

After obtaining the Toolathlon results, you need to perform a data conversion first. Taking the `notion-hr` task as an example, you can run the following command:

```bash
uv run vis_traj/convert_format.py --input_path /path/to/your/results/notion-hr/ --output_file notion-hr.json
```

The directory `/path/to/your/results/notion-hr/` should contain: `traj_log.json` and `eval_res.json`.

## Start Replay Server

Then, you need to run the following command:

```bash
uv run vis_traj/server.py --port 8000
```

And you can visit localhost:8000 to view the trajectory.
