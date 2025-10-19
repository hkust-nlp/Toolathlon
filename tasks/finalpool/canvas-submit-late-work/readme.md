Since the Canvas API cannot directly upload files to the Canvas storage system, Playwright is used for file operations.

In the legacy workspace, the Excel file indicates that assignments 2, 4, and 6 of the "film" course are missing submissions. However, assignment 2 has a leave note and does not require submission. The prompt explicitly states that any other unsubmitted assignments are not the agent's responsibility. Therefore, in `check_local`, if any submission is found for assignments 1, 2, 3, or 5, it should be considered a failure.

According to Junlong's requirements, the workspace is intentionally made more complex, with many unrelated or distracting files added. The agent must search for the correct homework files. File names no longer include the assignment ID—only the topic. The agent must use the assignment's description to determine which is the correct file. The actual valid homework files are located in:
/ssddata/xiaochen/workspace/mcpbench_dev/tasks/xiaochen/canvas_collect_work_data/initial_workspace/homeworks/temp

Additionally, there is a trap to test for confusion, with homeworks from other students (different IDs, and filenames/content containing other names) placed in:
/ssddata/xiaochen/workspace/mcpbench_dev/tasks/xiaochen/canvas_collect_work_data/initial_workspace/homeworks/films
This checks whether the agent distinguishes them correctly.

There is also a leave note, which the agent should find automatically and send to the TA email listed in the Excel file.

Update 9.19:
All files in `initial_workspace` have been compressed into an archive. Please note that git may not track changes inside the archive automatically.