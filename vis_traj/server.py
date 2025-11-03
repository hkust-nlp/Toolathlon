#!/usr/bin/env python3
"""
Simple HTTP server for LLM trajectory visualization
"""

import http.server
import socketserver
import json
import os
import sys
import urllib.parse
from pathlib import Path
from copy import deepcopy

# Global in-memory storage for trajectory data
TRAJECTORY_CACHE = {}

class TrajectoryHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)
    
    def do_GET(self):
        try:
            # Parse path, remove query parameters
            parsed_path = urllib.parse.urlparse(self.path)
            path_only = parsed_path.path
            
            # Handle API requests
            if path_only.startswith('/api/'):
                self.handle_api_request(path_only)
            # Handle numeric paths (e.g., /306), directly show corresponding trajectory
            elif path_only != '/' and path_only.lstrip('/').replace('/', '').isdigit():
                # Temporarily save original path for use in serve_trajectory_page
                original_path = self.path
                self.path = path_only  # Use cleaned path
                self.serve_trajectory_page()
                self.path = original_path  # Restore original path
            # Handle filename paths (e.g., /deepseek-v3.2-exp_woocommerce-customer-survey)
            elif path_only != '/' and not path_only.startswith('/api/'):
                # Check if it's a trajectory filename path
                traj_name = path_only.lstrip('/')
                # If already has .json extension, remove it; otherwise keep as is
                if traj_name.endswith('.json'):
                    traj_name = traj_name[:-5]
                
                # Construct full filename
                filename = f"{traj_name}.json"
                file_path = Path('trajs') / filename
                
                # If file exists, show trajectory page
                if file_path.exists():
                    original_path = self.path
                    self.path = path_only  # Use original path, but will extract traj_name
                    self.serve_trajectory_page_by_filename(traj_name)
                    self.path = original_path  # Restore original path
                else:
                    # Not a trajectory file, handle as static file
                    super().do_GET()
            else:
                # Handle static files
                super().do_GET()
                
        except Exception as e:
            print(f"Error processing request: {str(e)}")
            self.send_error(500, f"Internal server error: {str(e)}")
    
    def handle_api_request(self, path):
        """Handle API requests"""
        try:
            if path == '/api/files':
                self.get_trajectory_files()
            elif path.startswith('/api/trajectory/'):
                # Get filename, may need URL decoding
                filename = urllib.parse.unquote(path.split('/')[-1])
                self.get_trajectory_data(filename)
            else:
                self.send_error(404, "API endpoint not found")
        except Exception as e:
            print(f"API request processing failed: {str(e)}")
            self.send_error(500, f"Server error: {str(e)}")
    
    def get_trajectory_files(self):
        """Get trajectory file list"""
        try:
            # Get files from memory cache
            memory_files = [f"{name}.json" for name in TRAJECTORY_CACHE.keys()]
            
            # Get files from disk
            trajs_dir = Path('vis_traj/trajs')
            disk_files = []
            if trajs_dir.exists():
                disk_files = [f.name for f in trajs_dir.glob('*.json')]
            
            # Merge and deduplicate
            all_files = list(set(memory_files + disk_files))
            all_files.sort()
            
            response = {
                'success': True,
                'files': all_files,
                'count': len(all_files)
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Failed to get trajectory file list: {str(e)}")
            self.send_error(500, f"Error reading files: {str(e)}")
    
    def get_trajectory_data(self, filename):
        """Get trajectory data"""
        try:
            # If filename has no extension, automatically add .json
            if not filename.endswith('.json'):
                filename = filename + '.json'
            
            # Remove .json extension for cache key
            cache_key = filename[:-5] if filename.endswith('.json') else filename
            
            # Try to get from memory cache first
            if cache_key in TRAJECTORY_CACHE:
                data = TRAJECTORY_CACHE[cache_key].copy()
                data['_metadata'] = {
                    'filename': filename,
                    'source': 'memory'
                }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
                return
            
            # Fall back to disk if not in cache
            file_path = Path('vis_traj/trajs') / filename
            if not file_path.exists():
                self.send_error(404, f"Trajectory file not found: {filename}")
                return
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Add some metadata
            data['_metadata'] = {
                'filename': filename,
                'file_size': file_path.stat().st_size,
                'last_modified': file_path.stat().st_mtime,
                'source': 'disk'
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {filename} - {str(e)}")
            self.send_error(400, f"Invalid JSON file: {str(e)}")
        except Exception as e:
            print(f"Failed to read trajectory file: {filename} - {str(e)}")
            self.send_error(500, f"Error reading trajectory: {str(e)}")
    
    def serve_trajectory_page(self):
        """Serve for numeric paths (e.g., /306), return HTML page containing trajectory ID"""
        try:
            # Extract trajectory ID, remove leading and trailing slashes
            traj_id = self.path.strip('/')
            filename = f"{traj_id}.json"
            file_path = Path('vis_traj/trajs') / filename
            
            # Check if trajectory file exists
            if not file_path.exists():
                self.send_error(404, f"Trajectory {traj_id} not found")
                return
            
            # Read index.html and add trajectory ID information
            # Use path relative to server script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            index_path = Path(script_dir) / 'vis_traj/index.html'
            if not index_path.exists():
                self.send_error(500, "Index page not found")
                return
            
            with open(index_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Add trajectory ID meta tag to page for frontend reading
            # Insert before </head> or replace first <head> tag
            meta_tag = f'    <meta name="trajectory-id" content="{traj_id}">\n'
            if '</head>' in html_content:
                # Insert before </head>
                html_content = html_content.replace('</head>', meta_tag + '</head>', 1)
            elif '<head>' in html_content:
                # Insert after <head>
                html_content = html_content.replace('<head>', '<head>\n' + meta_tag, 1)
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error serving trajectory page: {str(e)}")
    
    def serve_trajectory_page_by_filename(self, traj_name):
        """Serve for filename paths (e.g., /deepseek-v3.2-exp_woocommerce-customer-survey), return HTML page containing trajectory filename"""
        try:
            filename = f"{traj_name}.json"
            file_path = Path('vis_traj/trajs') / filename
            
            # Check if trajectory file exists
            if not file_path.exists():
                self.send_error(404, f"Trajectory {traj_name} not found")
                return
            
            # Read index.html and add trajectory filename information
            # Use path relative to server script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            index_path = Path(script_dir) / 'index.html'
            if not index_path.exists():
                self.send_error(500, "Index page not found")
                return
            
            with open(index_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Add trajectory filename meta tag to page for frontend reading
            # traj_name does not include .json extension, as loadTrajectoryById will automatically add it
            meta_tag = f'    <meta name="trajectory-id" content="{traj_name}">\n'
            if '</head>' in html_content:
                # Insert before </head>
                html_content = html_content.replace('</head>', meta_tag + '</head>', 1)
            elif '<head>' in html_content:
                # Insert after <head>
                html_content = html_content.replace('<head>', '<head>\n' + meta_tag, 1)
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error serving trajectory page: {str(e)}")

def convert_format(input_path):
    """Convert trajectory format from input directory and store in memory"""
    # Get all subdirectories
    all_paths = []
    for root, dirs, files in os.walk(input_path):
        if root == input_path:
            for d in dirs:
                all_paths.append(os.path.join(root, d))
            break
    
    if not all_paths:
        print(f"⚠️  No subdirectories found in {input_path}")
        return
    
    print(f"🔄 Found {len(all_paths)} directories to convert...")
    converted_count = 0
    failed_count = 0
    
    for path in all_paths:
        task_name = os.path.basename(path)
        try:
            res = {}
            
            # Read eval_res.json
            eval_res_path = os.path.join(path, "eval_res.json")
            if not os.path.exists(eval_res_path):
                print(f"⚠️  Skipping {task_name}: eval_res.json not found")
                failed_count += 1
                continue
            
            with open(eval_res_path, "r") as f:
                is_pass = json.load(f)["pass"]
                res["pass"] = is_pass
            
            # Read traj_log.json
            traj_log_path = os.path.join(path, "traj_log.json")
            if not os.path.exists(traj_log_path):
                print(f"⚠️  Skipping {task_name}: traj_log.json not found")
                failed_count += 1
                continue
            
            with open(traj_log_path, "r") as f:
                data = json.load(f)
                if "messages" not in data:
                    print(f"⚠️  Skipping {task_name}: 'messages' field not found in traj_log.json")
                    failed_count += 1
                    continue
                
                msgs = data["messages"]
                msg_copies = []
                
                for msg in msgs:
                    msg_copy = deepcopy(msg)
                    if msg["role"] == "tool":
                        content = msg["content"]
                    elif msg["role"] == "user":
                        content = msg["content"]
                    elif msg["role"] == "assistant":
                        content = msg["content"]
                        if content is not None:
                            msg_copy["content"] = content
                        if "tool_calls" in msg:
                            for i, tool_call in enumerate(msg["tool_calls"]):
                                arguments = tool_call["function"]["arguments"]
                                if tool_call["function"]["name"] == "local-python-execute":
                                    if arguments == "":
                                        msg_copy["tool_calls"][i]["function"]["arguments"] = arguments
                                    else:
                                        msg_copy["tool_calls"][i]["function"]["arguments"] = arguments
                    msg_copies.append(msg_copy)
                
                res["messages"] = msg_copies
            
            # Store in memory cache instead of writing to disk
            TRAJECTORY_CACHE[task_name] = res
            
            print(f"✅ Converted: {task_name}")
            converted_count += 1
            
        except Exception as e:
            print(f"❌ Failed to convert {task_name}: {str(e)}")
            failed_count += 1


def run_server(port=8000):
    """Start server"""
    try:
        with socketserver.TCPServer(("", port), TrajectoryHandler) as httpd:
            httpd.allow_reuse_address = True
            
            print(f"🚀 LLM Trajectory Visualization Server started successfully!")
            print(f"📱 Access URL: http://localhost:{port}")
            print(f"💾 Trajectories in memory: {len(TRAJECTORY_CACHE)}")
            print(f"⏹️  Press Ctrl+C to stop server")
            print("-" * 50)
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except OSError as e:
        if e.errno == 98 or e.errno == 10048:  # Address already in use (Linux/Windows)
            print(f"❌ Port {port} is already in use")
            print(f"💡 Try using a different port: python3 server.py --port <port_number>")
        else:
            print(f"❌ Server startup failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    port = 8000
    input_path = None
    
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '--port':
            try:
                port = int(sys.argv[i + 1])
                i += 2
            except (IndexError, ValueError):
                print("❌ Invalid port number")
                sys.exit(1)
        elif sys.argv[i] == '--res_path':
            try:
                input_path = sys.argv[i + 1]
                i += 2
            except IndexError:
                print("❌ --res_path requires input path to be specified")
                sys.exit(1)
        elif sys.argv[i] == '--help':
            print("Usage: python3 server.py --res_path RES_PATH [--port PORT]")
            print("\nOptions:")
            print("  --res_path RES_PATH     Path to trajectory results directory (required)")
            print("  --port PORT             Specify port number (default: 8000)")
            print("  --help                  Show this help information")
            print("\nExamples:")
            print("  python3 server.py --res_path ./trajectory_data")
            print("  python3 server.py --res_path ./trajectory_data --port 9000")
            sys.exit(0)
        else:
            print(f"❌ Unknown parameter: {sys.argv[i]}")
            print("💡 Use --help to view help information")
            sys.exit(1)
    
    # Check if --res_path is provided
    if not input_path:
        print("❌ Missing required parameter: --res_path RES_PATH")
        print("💡 Use --help to view help information")
        print("\nExample:")
        print("  python3 server.py --res_path ./trajectory_data")
        sys.exit(1)
    
    # Check if input path exists
    if not os.path.exists(input_path):
        print(f"❌ Input path does not exist: {input_path}")
        sys.exit(1)
    
    # Convert and load data into memory
    convert_format(input_path)
    
    # Start server with loaded data
    print(f"\n🚀 Starting server with {len(TRAJECTORY_CACHE)} trajectories in memory...\n")
    run_server(port)
