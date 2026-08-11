"""Preflight: this task has no provisioning step; the rail_12306 MCP
server wraps China Railway's live, unauthenticated 12306 API, which is
geo/IP-sensitive and rate-limited. Verify reachability at prepare time so
an unreachable service fails prepare instead of wasting an agent run.
Note: any HTTP response below 500 counts as reachable, so a geo-block that
returns 403 will still pass this probe."""

from argparse import ArgumentParser

from utils.general.preflight import check_url_reachable, run_preflight

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    parser.parse_args()

    run_preflight([
        (
            "12306 (kyfw.12306.cn)",
            lambda: check_url_reachable(
                "https://kyfw.12306.cn/otn/leftTicket/init", description="kyfw.12306.cn"
            ),
        ),
    ])
