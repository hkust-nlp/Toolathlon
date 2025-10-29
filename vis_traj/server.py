#!/usr/bin/env python3
"""
Enhanced HTTP/HTTPS server for LLM trajectory visualization
Supports auto-reconnection, health checks, error recovery and monitoring
"""

import http.server
import socketserver
import json
import os
import sys
import urllib.parse
import ssl
import time
import signal
import threading
import logging
import traceback
from pathlib import Path
from datetime import datetime
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global variables
server_stats = {
    'start_time': time.time(),
    'requests_count': 0,
    'errors_count': 0,
    'last_error': None,
    'uptime': 0
}

class TrajectoryHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)
        self.start_time = time.time()
    
    def log_message(self, format, *args):
        """Custom log format"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = format % args
        logger.info(f"[{timestamp}] {message}")
    
    def log_error(self, format, *args):
        """Log errors"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = format % args
        logger.error(f"[{timestamp}] ERROR: {message}")
        server_stats['errors_count'] += 1
        server_stats['last_error'] = message
    
    def do_GET(self):
        try:
            server_stats['requests_count'] += 1
            
            # Parse path, remove query parameters
            parsed_path = urllib.parse.urlparse(self.path)
            path_only = parsed_path.path
            
            # Health check endpoint
            if path_only == '/health':
                self.handle_health_check()
                return
            
            # Statistics endpoint
            if path_only == '/stats':
                self.handle_stats()
                return
            
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
            logger.error(f"Error processing request: {str(e)}")
            logger.error(f"Error details: {traceback.format_exc()}")
            self.send_error(500, f"Internal server error: {str(e)}")
    
    def handle_health_check(self):
        """Health check endpoint"""
        try:
            # Check if key files exist
            index_path = Path(os.path.dirname(os.path.abspath(__file__))) / 'index.html'
            trajs_dir = Path('trajs')
            
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'uptime': time.time() - server_stats['start_time'],
                'requests_count': server_stats['requests_count'],
                'errors_count': server_stats['errors_count'],
                'index_file_exists': index_path.exists(),
                'trajs_dir_exists': trajs_dir.exists(),
                'memory_usage': psutil.Process().memory_info().rss / 1024 / 1024,  # MB
                'cpu_percent': psutil.Process().cpu_percent()
            }
            
            if server_stats['last_error']:
                health_status['last_error'] = server_stats['last_error']
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(health_status, indent=2).encode())
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            self.send_error(500, f"Health check failed: {str(e)}")
    
    def handle_stats(self):
        """Statistics endpoint"""
        try:
            stats = {
                'server_stats': server_stats.copy(),
                'system_info': {
                    'cpu_count': psutil.cpu_count(),
                    'memory_total': psutil.virtual_memory().total / 1024 / 1024 / 1024,  # GB
                    'memory_available': psutil.virtual_memory().available / 1024 / 1024 / 1024,  # GB
                    'disk_usage': psutil.disk_usage('/').percent
                },
                'timestamp': datetime.now().isoformat()
            }
            
            # Update uptime
            stats['server_stats']['uptime'] = time.time() - server_stats['start_time']
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(stats, indent=2).encode())
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {str(e)}")
            self.send_error(500, f"Stats failed: {str(e)}")
    
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
            logger.error(f"API request processing failed: {str(e)}")
            logger.error(f"Error details: {traceback.format_exc()}")
            self.send_error(500, f"Server error: {str(e)}")
    
    def get_trajectory_files(self):
        """Get trajectory file list"""
        try:
            trajs_dir = Path('vis_traj/trajs')
            if not trajs_dir.exists():
                files = []
                logger.warning("Trajectory files directory does not exist")
            else:
                files = [f.name for f in trajs_dir.glob('*.json')]
                logger.info(f"Found {len(files)} trajectory files")
            
            response = {
                'success': True,
                'files': files,
                'count': len(files)
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            logger.error(f"Failed to get trajectory file list: {str(e)}")
            self.send_error(500, f"Error reading files: {str(e)}")
    
    def get_trajectory_data(self, filename):
        """Get trajectory data"""
        try:
            # If filename has no extension, automatically add .json
            if not filename.endswith('.json'):
                filename = filename + '.json'
            
            file_path = Path('vis_traj/trajs') / filename
            if not file_path.exists():
                logger.warning(f"Trajectory file does not exist: {filename}")
                self.send_error(404, f"Trajectory file not found: {filename}")
                return
            
            logger.info(f"Loading trajectory file: {filename}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Add some metadata
            data['_metadata'] = {
                'filename': filename,
                'file_size': file_path.stat().st_size,
                'last_modified': file_path.stat().st_mtime,
                'load_time': datetime.now().isoformat()
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {filename} - {str(e)}")
            self.send_error(400, f"Invalid JSON file: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to read trajectory file: {filename} - {str(e)}")
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
    
    def log_message(self, format, *args):
        """Custom log format"""
        print(f"[{self.date_time_string()}] {format % args}")

def signal_handler(signum, frame):
    """Signal handler"""
    logger.info(f"Received signal {signum}, shutting down server...")
    sys.exit(0)

def health_monitor():
    """Health monitoring thread"""
    while True:
        try:
            time.sleep(30)  # Check every 30 seconds
            uptime = time.time() - server_stats['start_time']
            server_stats['uptime'] = uptime
            
            # Check memory usage
            memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            if memory_usage > 1000:  # Over 1GB
                logger.warning(f"High memory usage: {memory_usage:.2f}MB")
            
            # Check error rate
            if server_stats['requests_count'] > 0:
                error_rate = server_stats['errors_count'] / server_stats['requests_count']
                if error_rate > 0.1:  # Error rate over 10%
                    logger.warning(f"High error rate: {error_rate:.2%}")
            
            logger.info(f"Server status - Uptime: {uptime:.0f}s, Requests: {server_stats['requests_count']}, Errors: {server_stats['errors_count']}")
            
        except Exception as e:
            logger.error(f"Health monitoring exception: {str(e)}")

def run_server(port=8000, use_https=False, certfile=None, keyfile=None):
    """Start server"""
    # Check port permissions
    if port < 1024 and os.geteuid() != 0:
        logger.warning(f"Port {port} requires root privileges, recommend using sudo")
        print(f"⚠️  Port {port} requires root privileges, recommend using sudo")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start health monitoring thread
    monitor_thread = threading.Thread(target=health_monitor, daemon=True)
    monitor_thread.start()
    
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            logger.info(f"Attempting to start server (attempt {retry_count + 1})")
            
            # Configure server options
            class CustomTCPServer(socketserver.TCPServer):
                allow_reuse_address = True
                timeout = 30  # 30 second timeout
                
                def server_bind(self):
                    self.socket.setsockopt(socketserver.socket.SOL_SOCKET, socketserver.socket.SO_REUSEADDR, 1)
                    super().server_bind()
            
            with CustomTCPServer(("", port), TrajectoryHandler) as httpd:
                # If HTTPS is enabled, configure SSL
                if use_https:
                    if not certfile or not keyfile:
                        logger.error("HTTPS requires certificate files to be specified")
                        print("❌ HTTPS requires certificate files to be specified")
                        print("💡 Use --cert and --key parameters to specify certificate files")
                        print("💡 Or use --generate-cert to generate self-signed certificate")
                        sys.exit(1)
                    
                    if not os.path.exists(certfile):
                        logger.error(f"Certificate file does not exist: {certfile}")
                        print(f"❌ Certificate file does not exist: {certfile}")
                        sys.exit(1)
                    
                    if not os.path.exists(keyfile):
                        logger.error(f"Private key file does not exist: {keyfile}")
                        print(f"❌ Private key file does not exist: {keyfile}")
                        sys.exit(1)
                    
                    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                    context.load_cert_chain(certfile=certfile, keyfile=keyfile)
                    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
                    
                    protocol = "https"
                    logger.info(f"HTTPS enabled (using certificate: {certfile})")
                    print(f"🔒 HTTPS enabled (using certificate: {certfile})")
                else:
                    protocol = "http"
                
                logger.info(f"LLM Trajectory Visualization Server started successfully!")
                print(f"🚀 LLM Trajectory Visualization Server started successfully!")
                print(f"📱 Access URL: {protocol}://localhost:{port}")
                print(f"📁 Trajectory files directory: {os.path.abspath('trajs')}")
                print(f"🔍 Health check: {protocol}://localhost:{port}/health")
                print(f"📊 Statistics: {protocol}://localhost:{port}/stats")
                print(f"⏹️  Press Ctrl+C to stop server")
                print("-" * 50)
                
                # Reset retry count
                retry_count = 0
                
                httpd.serve_forever()
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, server shutting down...")
            print("\n👋 Server stopped")
            break
        except OSError as e:
            retry_count += 1
            if e.errno == 98:  # Address already in use
                logger.error(f"Port {port} is already in use (attempt {retry_count}/{max_retries})")
                print(f"❌ Port {port} is already in use, trying port {port + retry_count}")
                port += retry_count
                time.sleep(2)  # Wait 2 seconds before retry
            else:
                logger.error(f"Server startup failed: {e}")
                print(f"❌ Server startup failed: {e}")
                if retry_count >= max_retries:
                    break
                time.sleep(5)  # Wait 5 seconds before retry
        except ssl.SSLError as e:
            logger.error(f"SSL error: {e}")
            print(f"❌ SSL error: {e}")
            print("💡 Please check if certificate files are correct")
            break
        except Exception as e:
            retry_count += 1
            logger.error(f"Server runtime exception: {str(e)}")
            logger.error(f"Error details: {traceback.format_exc()}")
            print(f"❌ Server runtime exception: {e}")
            if retry_count >= max_retries:
                logger.error("Reached maximum retry count, server startup failed")
                print("❌ Reached maximum retry count, server startup failed")
                break
            time.sleep(5)  # Wait 5 seconds before retry
    
    if retry_count >= max_retries:
        logger.error("Server startup failed, reached maximum retry count")
        print("❌ Server startup failed, reached maximum retry count")
        sys.exit(1)

if __name__ == "__main__":
    import sys
    import subprocess
    
    port = 8000
    use_https = False
    certfile = None
    keyfile = None
    
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '--port':
            try:
                port = int(sys.argv[i + 1])
                i += 2
            except (IndexError, ValueError):
                print("❌ Invalid port number")
                sys.exit(1)
        elif sys.argv[i] == '--https':
            use_https = True
            i += 1
        elif sys.argv[i] == '--cert':
            try:
                certfile = sys.argv[i + 1]
                i += 2
            except IndexError:
                print("❌ --cert requires certificate file path to be specified")
                sys.exit(1)
        elif sys.argv[i] == '--key':
            try:
                keyfile = sys.argv[i + 1]
                i += 2
            except IndexError:
                print("❌ --key requires private key file path to be specified")
                sys.exit(1)
        elif sys.argv[i] == '--generate-cert':
            # Generate self-signed certificate
            certfile = 'server.crt'
            keyfile = 'server.key'
            
            # Check if domain is specified
            domain = None
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('--'):
                domain = sys.argv[i + 1]
                i += 1
            
            print("🔧 Generating self-signed certificate...")
            if domain:
                print(f"   Domain: {domain}")
            
            try:
                # Use openssl to generate self-signed certificate with SAN (Subject Alternative Name)
                # This allows support for multiple domains
                cn = domain if domain else 'localhost'
                san_domains = [cn, 'localhost', '127.0.0.1']
                if domain and domain not in san_domains:
                    san_domains.insert(0, domain)
                
                # Generate configuration file for SAN extension
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as conf_file:
                    conf_path = conf_file.name
                    conf_file.write("""[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = CN
ST = State
L = City
O = Organization
CN = {cn}

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
""".format(cn=cn))
                    for idx, alt_name in enumerate(san_domains, 1):
                        conf_file.write(f"DNS.{idx} = {alt_name}\n")
                    conf_file.write("IP.1 = 127.0.0.1\n")
                    conf_file.write("IP.2 = ::1\n")
                
                # Generate private key
                subprocess.run([
                    'openssl', 'genrsa', '-out', keyfile, '4096'
                ], check=True, capture_output=True)
                
                # Generate certificate signing request
                csr_file = certfile.replace('.crt', '.csr')
                subprocess.run([
                    'openssl', 'req', '-new', '-key', keyfile,
                    '-out', csr_file, '-config', conf_path
                ], check=True, capture_output=True)
                
                # Generate self-signed certificate (including SAN)
                subprocess.run([
                    'openssl', 'x509', '-req', '-days', '365',
                    '-in', csr_file, '-signkey', keyfile,
                    '-out', certfile, '-extensions', 'v3_req',
                    '-extfile', conf_path
                ], check=True, capture_output=True)
                
                # Clean up temporary files
                try:
                    os.remove(conf_path)
                    os.remove(csr_file)
                except:
                    pass
                
                print(f"✅ Certificate generated: {certfile}, {keyfile}")
                print(f"   Supported domains: {', '.join(san_domains)}")
                use_https = True
                i += 1
            except subprocess.CalledProcessError as e:
                print("❌ Certificate generation failed, please ensure openssl is installed")
                print(f"   Error info: {e.stderr.decode() if e.stderr else 'unknown'}")
                sys.exit(1)
            except FileNotFoundError:
                print("❌ openssl not found, cannot generate certificate")
                print("💡 Please install openssl: sudo apt-get install openssl")
                print("💡 Or manually generate certificate and use --cert and --key parameters")
                sys.exit(1)
        elif sys.argv[i] == '--help':
            print("Usage: python3 server.py [options]")
            print("\nOptions:")
            print("  --port PORT             Specify port number (default: 8000)")
            print("  --https                 Enable HTTPS")
            print("  --cert CERTFILE         Specify SSL certificate file path")
            print("  --key KEYFILE           Specify SSL private key file path")
            print("  --generate-cert [domain] Generate self-signed certificate and enable HTTPS")
            print("                         Can specify domain, e.g.: --generate-cert toolathlon-traj.xyz")
            print("  --help                  Show this help information")
            print("\nExamples:")
            print("  python3 server.py                              # HTTP mode, port 8000")
            print("  python3 server.py --port 8080                  # HTTP mode, port 8080")
            print("  python3 server.py --generate-cert              # Generate certificate (supports localhost)")
            print("  python3 server.py --generate-cert example.com  # Generate certificate (supports specified domain)")
            print("  python3 server.py --https --cert server.crt --key server.key")
            sys.exit(0)
        else:
            print(f"❌ Unknown parameter: {sys.argv[i]}")
            print("💡 Use --help to view help information")
            sys.exit(1)
    
    # If HTTPS is specified but no certificate is specified, try using default path
    if use_https and not certfile:
        if os.path.exists('server.crt') and os.path.exists('server.key'):
            certfile = 'server.crt'
            keyfile = 'server.key'
            print(f"🔒 Using default certificate files: {certfile}, {keyfile}")
        else:
            print("❌ HTTPS enabled but certificate files not found")
            print("💡 Use --generate-cert to generate self-signed certificate")
            print("💡 Or use --cert and --key to specify certificate files")
            sys.exit(1)
    
    run_server(port, use_https, certfile, keyfile)
