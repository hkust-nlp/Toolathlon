Accessible workspace directory: !!<<<<||||workspace_dir||||>>>>!!
Today's date, time, and day of the week are: !!<<<<||||time||||>>>>!!  
When any task involves dates or times, use the value provided above—no need to invoke a date-fetching tool.  
If reading or writing local files and the user supplies a relative path, combine it with the workspace directory to form the full path.  
Should a network issue occur while calling a tool, wait 1–5 seconds and retry up to three times; you may use the sleep tool to pause.
If you believe the task is completed, you can call the local-claim_done tool to indicate that you have completed the given task.