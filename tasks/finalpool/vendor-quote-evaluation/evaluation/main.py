from argparse import ArgumentParser

from .check_local import check_local

if __name__ == "__main__":
    parser = ArgumentParser(description="Evaluate the vendor-quote-evaluation task")
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--groundtruth_workspace", required=True)
    parser.add_argument("--res_log_file", required=False, help="Path to result log file")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    try:
        local_pass, local_message = check_local(args.agent_workspace, args.groundtruth_workspace)
    except Exception as exc:
        print("local check error: ", exc)
        exit(1)

    if not local_pass:
        print("local check failed: ", local_message)
        exit(1)

    print("Pass all tests!")
