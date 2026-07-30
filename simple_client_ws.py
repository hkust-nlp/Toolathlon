#!/usr/bin/env python3
"""
WebSocket Client (Production)
Persistent connection to Server, receive requests and process them
"""

# Version control
WS_CLIENT_VERSION = "1.3"

import asyncio
import httpx
import argparse
import json
import os
from datetime import datetime
from websockets import connect, ConnectionClosedError

def log(msg):
    """Log with timestamp (local time + UTC)"""
    local_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    utc_time = datetime.utcnow().strftime('%H:%M:%S.%f')[:-3]
    print(f"[{local_time}][UTC {utc_time}] {msg}", flush=True)

async def process_single_request(
    llm_base_url: str,
    llm_api_key: str,
    request_data: dict
):
    """Process a single request: call LLM + return response data"""
    request_id = request_data["request_id"]
    response_data = None

    try:
        log(f"[Client] Start processing request: {request_id}")

        # Determine endpoint from metadata (default to /chat/completions for backward compatibility)
        endpoint = request_data.get("_endpoint", "/chat/completions")
        log(f"[Client] Using endpoint: {endpoint}")

        # 调用真实的 LLM
        headers = {"Authorization": f"Bearer {llm_api_key}"}

        # Filter out metadata fields (those starting with _) and internal fields
        filtered_data = {
            k: v for k, v in request_data.items()
            if k not in ["request_id", "pushed", "_server_push_time"] and not k.startswith("_")
        }

        async with httpx.AsyncClient(timeout=600.0) as client:  # 10 minutes timeout
            llm_resp = await client.post(
                f"{llm_base_url}{endpoint}",  # Use the endpoint from metadata
                json=filtered_data,
                headers=headers
            )

            # Log detailed info for non-200 responses
            if llm_resp.status_code != 200:
                log(f"[Client] ❌ Non-200 status for {request_id}: {llm_resp.status_code}")
                log(f"[Client] Response headers: {dict(llm_resp.headers)}")
                log(f"[Client] Response content: {llm_resp.text}")

            # Pack complete response
            response_data = {
                "status_code": llm_resp.status_code,
                "body": llm_resp.json()
            }
            log(f"[Client] LLM response successful: {request_id}, endpoint: {endpoint}, status code: {llm_resp.status_code}")

    except Exception as e:
        # Network error or timeout
        import traceback
        error_detail = traceback.format_exc()
        log(f"[Client] LLM call failed {request_id}:")
        log(f"  Exception type: {type(e).__name__}")
        log(f"  Exception message: {str(e)}")
        log(f"  Full stack:\n{error_detail}")

        response_data = {
            "status_code": 500,
            "body": {
                "error": {
                    "message": f"{type(e).__name__}: {str(e)}" if str(e) else type(e).__name__,
                    "type": "network_error",
                    "code": "client_error"
                }
            }
        }

    return request_id, response_data

async def send_response_with_retry(websocket, request_id: str, response_data: dict, max_retries=3):
    """Send response, with retry"""
    for retry in range(max_retries):
        try:
            await websocket.send(json.dumps({
                "type": "response",
                "request_id": request_id,
                "data": response_data
            }))
            log(f"[Client] Response sent: {request_id}")
            return True
        except Exception as e:
            if retry < max_retries - 1:
                log(f"[Client] Send failed {request_id} (retry {retry+1}/{max_retries}): {e}")
                await asyncio.sleep(1 * (retry + 1))
            else:
                log(f"[Client] Send failed {request_id} (give up): {e}")
                return False

async def receive_messages(websocket, request_queue: asyncio.Queue, last_heartbeat_ack: dict):
    """
    Specialized in receiving WebSocket messages
    Put requests immediately into the queue, without blocking the receive loop
    """
    try:
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "new_requests":
                # Received new request batch, put immediately into the queue
                requests = data.get("requests", [])
                receive_time = datetime.utcnow()
                log(f"[Client] Received {len(requests)} requests, put into processing queue")

                for req in requests:
                    request_id = req.get("request_id", "unknown")
                    # Check if there is a Server push time (if there is)
                    if "_server_push_time" in req:
                        delay = (receive_time - datetime.fromisoformat(req["_server_push_time"])).total_seconds()
                        log(f"[Client] Put into queue: {request_id} (transmission delay: {delay:.3f} seconds)")
                    else:
                        log(f"[Client] Put into queue: {request_id}")
                    await request_queue.put(req)

            elif msg_type == "heartbeat_ack":
                # Received heartbeat response, update time
                last_heartbeat_ack["time"] = datetime.now()

            elif msg_type == "error":
                log(f"[Client] Server error: {data.get('message')}")
                raise Exception(f"Server error: {data.get('message')}")

            else:
                log(f"[Client] Unknown message type: {msg_type}")

    except ConnectionClosedError as e:
        log(f"[Client] receive_messages: Connection closed: {e}")
        raise
    except Exception as e:
        log(f"[Client] receive_messages error: {e}")
        raise

async def process_requests(websocket, request_queue: asyncio.Queue, llm_base_url: str, llm_api_key: str):
    """
    Specialized in processing request queue
    Get requests from the queue, and create independent coroutines for each request (concurrent processing)
    """
    active_tasks = set()  # Track active tasks

    try:
        while True:
            # Get request from the queue
            req = await request_queue.get()

            # Create independent coroutine tasks for each request (without waiting for completion)
            task = asyncio.create_task(
                process_and_respond(websocket, req, llm_base_url, llm_api_key, request_queue)
            )
            active_tasks.add(task)

            # Clean up completed tasks
            active_tasks = {t for t in active_tasks if not t.done()}

    except asyncio.CancelledError:
        log(f"[Client] process_requests task cancelled")
        # Cancel all active sub-tasks
        for task in active_tasks:
            task.cancel()
        # Wait for all tasks to complete cancellation
        await asyncio.gather(*active_tasks, return_exceptions=True)
        raise
    except Exception as e:
        log(f"[Client] process_requests error: {e}")
        raise

async def process_and_respond(websocket, req: dict, llm_base_url: str, llm_api_key: str, request_queue: asyncio.Queue):
    """
    Process a single request and send response (independent coroutine)
    """
    try:
        # Process request
        request_id, response_data = await process_single_request(llm_base_url, llm_api_key, req)

        # Send response
        await send_response_with_retry(websocket, request_id, response_data)

    except Exception as e:
        request_id = req.get("request_id", "unknown")
        log(f"[Client] Process request {request_id} exception: {e}")
        import traceback
        log(f"[Client] Stack: {traceback.format_exc()}")
    finally:
        # Mark task as done
        request_queue.task_done()

async def main(server_url: str, llm_base_url: str, llm_api_key: str, job_id: str = None):
    print("="*50)
    print("WebSocket Proxy Client (Production)")
    print(f"Version: {WS_CLIENT_VERSION}")
    print(f"Server URL: {server_url}")
    print(f"Real LLM URL: {llm_base_url}")
    if job_id:
        print(f"Job ID: {job_id}")
    print("="*50)

    # Convert HTTP URL to WebSocket URL and add job_id parameter
    ws_url = server_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
    if job_id:
        ws_url += f"?job_id={job_id}"

    # Reconnect exponential backoff parameters
    retry_delay = 5  # Initial 5 seconds
    max_retry_delay = 60  # Maximum 60 seconds

    while True:  # Automatic reconnect loop
        # For heartbeat timeout detection
        last_heartbeat_ack = {"time": datetime.now()}

        # Request queue
        request_queue = asyncio.Queue()

        try:
            log(f"[Client] Connecting to WebSocket: {ws_url}")
            # Underlying WebSocket ping/pong timeout changed to 120 seconds (originally 10 seconds)
            # This allows for Server short-term busy or network jitter
            async with connect(ws_url, ping_interval=20, ping_timeout=120, max_size=32 * 1024 * 1024) as websocket:
                log(f"[Client] WebSocket connection successful")

                # Connection successful, reset retry delay
                retry_delay = 5

                # Start three independent tasks
                heartbeat_task = asyncio.create_task(send_heartbeat(websocket, last_heartbeat_ack))
                receive_task = asyncio.create_task(receive_messages(websocket, request_queue, last_heartbeat_ack))
                process_task = asyncio.create_task(process_requests(websocket, request_queue, llm_base_url, llm_api_key))

                try:
                    # Wait for any task to complete (usually because of connection closed)
                    done, pending = await asyncio.wait(
                        [heartbeat_task, receive_task, process_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    # Cancel incomplete tasks
                    for task in pending:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                        except Exception as e:
                            log(f"[Client] Error canceling task: {e}")

                    # Check exceptions of completed tasks
                    for task in done:
                        try:
                            task.result()
                        except ConnectionClosedError as e:
                            log(f"[Client] Connection closed: {e}")
                        except Exception as e:
                            log(f"[Client] Task exception: {e}")

                except Exception as e:
                    log(f"[Client] Main loop error: {e}")
                finally:
                    # Ensure cleanup
                    for task in [heartbeat_task, receive_task, process_task]:
                        if task is not None and not task.done():
                            task.cancel()
                            try:
                                await task
                            except:
                                pass

        except Exception as e:
            log(f"[Client] Connection failed: {e}")

        # Reconnect wait (exponential backoff)
        log(f"[Client] Reconnect in {retry_delay} seconds...")
        await asyncio.sleep(retry_delay)

        # Increase retry delay (exponential backoff), maximum 60 seconds
        retry_delay = min(retry_delay * 2, max_retry_delay)

async def send_heartbeat(websocket, last_heartbeat_ack: dict):
    """Send heartbeat periodically, and detect if Server is responding"""
    try:
        while True:
            await asyncio.sleep(30)  # Send heartbeat every 30 seconds

            # Send heartbeat
            await websocket.send(json.dumps({"type": "heartbeat"}))

            # Check last received ack time, if more than 120 seconds没收到，认为 Server 卡住了
            # 120 seconds = 4 heartbeat cycles, tolerate 3 missed
            time_since_last_ack = (datetime.now() - last_heartbeat_ack["time"]).total_seconds()
            if time_since_last_ack > 120:
                log(f"[Client] Heartbeat timeout: {time_since_last_ack:.0f} seconds no heartbeat_ack received, Server may be stuck")
                raise Exception(f"Heartbeat timeout: no ack for {time_since_last_ack:.0f} seconds")

    except asyncio.CancelledError:
        pass
    except Exception as e:
        log(f"[Client] Heartbeat task failed: {e}")
        raise  # Propagate upwards, trigger reconnect

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebSocket Proxy Client")
    parser.add_argument("--server-url", required=True, help="Server URL (e.g., http://47.253.6.47:8080)")
    parser.add_argument("--llm-base-url", required=True, help="Real LLM base URL (e.g., https://api.deepseek.com/v1)")
    parser.add_argument(
        "--llm-api-key",
        default=os.environ.get(
            "TOOLATHLON_OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", "")
        ),
        help="Real LLM API key; defaults to TOOLATHLON_OPENAI_API_KEY, then "
             "OPENAI_API_KEY, then empty for endpoints without authentication",
    )
    parser.add_argument("--job-id", required=False, help="Job ID for authentication (required by server)")

    args = parser.parse_args()
    asyncio.run(main(args.server_url, args.llm_base_url, args.llm_api_key, args.job_id))
