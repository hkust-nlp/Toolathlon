import https from 'https';
import http from 'http';
import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

// Get current file directory
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Get configuration from command line arguments
const PROXY_PORT = process.argv[2] || 4443;
const TARGET_PORT = process.argv[3] || 3000;
const TARGET_HOST = process.argv[4] || 'localhost';
const TARGET_PROTOCOL = process.argv[5] || 'http';
const CERT_DIR = process.argv[6] || __dirname; 

// Use absolute paths
const DEPLOYMENT_DIR = path.resolve(CERT_DIR);
const CERT_FILE = path.join(DEPLOYMENT_DIR, 'cert.pem');
const KEY_FILE = path.join(DEPLOYMENT_DIR, 'key.pem');

console.log(`[${new Date().toISOString()}] Starting HTTPS proxy service
Configuration:
- Proxy port (HTTPS): ${PROXY_PORT}
- Target service: ${TARGET_PROTOCOL}://${TARGET_HOST}:${TARGET_PORT}
- Certificate directory: ${DEPLOYMENT_DIR}
`);

// Check if certificates exist
if (!fs.existsSync(CERT_FILE) || !fs.existsSync(KEY_FILE)) {
  console.log('Generating self-signed certificate...');
  try {
    if (!fs.existsSync(DEPLOYMENT_DIR)) {
      fs.mkdirSync(DEPLOYMENT_DIR, { recursive: true });
      console.log(`Created certificate directory: ${DEPLOYMENT_DIR}`);
    }
    
    execSync(`openssl req -new -x509 -days 365 -nodes -out "${CERT_FILE}" -keyout "${KEY_FILE}" -subj "/CN=localhost"`);
    console.log(`Certificate generated successfully at: ${DEPLOYMENT_DIR}`);
  } catch (error) {
    console.error('Failed to generate certificate:', error.message);
    process.exit(1);
  }
}

// Create HTTPS server
const server = https.createServer({
  key: fs.readFileSync(KEY_FILE),
  cert: fs.readFileSync(CERT_FILE)
}, (req, res) => {
  const options = {
    hostname: TARGET_HOST,
    port: TARGET_PORT,
    path: req.url,
    method: req.method,
    headers: { ...req.headers }
  };
  
  delete options.headers.host;
  options.headers.host = `${TARGET_HOST}:${TARGET_PORT}`;
  
  const client = TARGET_PROTOCOL === 'https' ? https : http;
  
  const proxyReq = client.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res);
  });
  
  proxyReq.on('error', (err) => {
    console.error(`[${new Date().toISOString()}] Proxy error:`, err.message);
    res.writeHead(502);
    res.end('Proxy error: ' + err.message);
  });
  
  req.pipe(proxyReq);
});

server.on('error', (err) => {
  console.error('Server error:', err);
  if (err.code === 'EADDRINUSE') {
    console.error(`Port ${PROXY_PORT} is already in use`);
  }
  process.exit(1);
});

server.listen(PROXY_PORT, () => {
  console.log(`[${new Date().toISOString()}] HTTPS proxy running at https://localhost:${PROXY_PORT}`);
  console.log(`[${new Date().toISOString()}] Proxy target: ${TARGET_PROTOCOL}://${TARGET_HOST}:${TARGET_PORT}`);
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\nShutting down server...');
  server.close(() => {
    console.log('Server has been shut down');
    process.exit(0);
  });
});

process.on('SIGTERM', () => {
  console.log('\nReceived termination signal, shutting down server...');
  server.close(() => {
    console.log('Server has been shut down');
    process.exit(0);
  });
});