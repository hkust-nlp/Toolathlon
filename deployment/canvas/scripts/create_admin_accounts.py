#!/usr/bin/env python3
# Canvas admin account creation script
# Creates three admin accounts: mcpcanvasadminX@mcp.com, password: mcpcanvasadminpassX, token: mcpcanvasadmintokenX (X=1,2,3)

import json
import subprocess
import os
import time
from datetime import datetime

from argparse import ArgumentParser
from configs.global_configs import global_configs
parser = ArgumentParser()
parser.add_argument("--container-name", type=str, default="canvas-docker")
args = parser.parse_args()

CONTAINER_NAME = args.container_name
BUNDLE_PATH = "/opt/canvas/.gems/bin/bundle"
CANVAS_DIR = "/opt/canvas/canvas-lms"

def create_admin_accounts():
    """Create three Canvas admin accounts"""
    admin_users = [
        {
            'name': 'MCP Canvas Admin 1',
            'short_name': 'Admin1',
            'email': 'mcpcanvasadmin1@mcp.com',
            'password': 'mcpcanvasadminpass1',
            'canvas_token': 'mcpcanvasadmintoken1',
            'sis_user_id': 'ADMIN001'
        },
        {
            'name': 'MCP Canvas Admin 2', 
            'short_name': 'Admin2',
            'email': 'mcpcanvasadmin2@mcp.com',
            'password': 'mcpcanvasadminpass2',
            'canvas_token': 'mcpcanvasadmintoken2',
            'sis_user_id': 'ADMIN002'
        },
        {
            'name': 'MCP Canvas Admin 3',
            'short_name': 'Admin3', 
            'email': 'mcpcanvasadmin3@mcp.com',
            'password': 'mcpcanvasadminpass3',
            'canvas_token': 'mcpcanvasadmintoken3',
            'sis_user_id': 'ADMIN003'
        }
    ]
    
    # Ruby script to create admin users
    script = '''
require 'json'

admin_users = JSON.parse(%s)
results = []
errors = []

puts "Creating #{admin_users.length} admin accounts..."

# Get default account
account = Account.default

admin_users.each_with_index do |user_data, index|
  begin
    # Begin transaction
    ActiveRecord::Base.transaction do
      # Create user
      user = User.create!(
        name: user_data['name'],
        short_name: user_data['short_name']
      )
      
      # Create pseudonym (login credential)
      pseudonym = Pseudonym.new(
        user: user,
        account: account,
        unique_id: user_data['email'],
        password: user_data['password'],
        password_confirmation: user_data['password'],
        sis_user_id: user_data['sis_user_id']
      )
      
      pseudonym.save!
      
      # Create preset API token
      token = user.access_tokens.create!(
        purpose: "Admin API Token",
        token: user_data['canvas_token']
      )
      
      # Assign admin role to user - AccountAdmin (same as canvas@example.edu)
      admin_role = account.roles.where(name: 'AccountAdmin').first
      
      # Create AccountUser record with admin role
      account_user = AccountUser.create!(
        account: account,
        user: user,
        role: admin_role
      )
      
      results << {
        'id' => user.id,
        'name' => user_data['name'],
        'email' => user_data['email'], 
        'password' => user_data['password'],
        'token' => user_data['canvas_token'],
        'sis_user_id' => pseudonym.sis_user_id,
        'pseudonym_id' => pseudonym.id,
        'account_user_id' => account_user.id,
        'role' => 'admin'
      }
      
      puts "✅ Created admin user: #{user_data['email']}"
    end
    
  rescue => e
    errors << {
      'email' => user_data['email'],
      'error' => "#{e.class}: #{e.message}",
      'backtrace' => e.backtrace.first(3)
    }
    puts "❌ Error creating #{user_data['email']}: #{e.message}"
  end
end

puts "\\nAdmin account creation complete: #{results.length} success, #{errors.length} errors"

# Output results
puts "\\nJSON_RESULTS_START"
puts results.to_json
puts "JSON_RESULTS_END"

if errors.any?
  puts "\\nJSON_ERRORS_START"
  puts errors.to_json
  puts "JSON_ERRORS_END"  
end
''' % json.dumps(json.dumps(admin_users))

    # Ensure temporary directory exists
    os.makedirs('./deployment/canvas/tmp', exist_ok=True)
    
    script_path = './deployment/canvas/tmp/create_admin_accounts.rb'
    script_path_in_container = '/tmp/create_admin_accounts.rb'
    
    # Write script file
    with open(script_path, 'w') as f:
        f.write(script)
    
    # Copy script into container
    subprocess.run([global_configs.podman_or_docker, 'cp', script_path, f'{CONTAINER_NAME}:{script_path_in_container}'])
    
    # Execute script in container
    cmd = f"cd {CANVAS_DIR} && GEM_HOME=/opt/canvas/.gems {BUNDLE_PATH} exec rails runner {script_path_in_container}"
    result = subprocess.run(
        [global_configs.podman_or_docker, 'exec', CONTAINER_NAME, 'bash', '-c', cmd],
        capture_output=True,
        text=True
    )
    
    output = result.stdout + result.stderr
    results = []
    errors = []
    
    # Parse results
    if "JSON_RESULTS_START" in output and "JSON_RESULTS_END" in output:
        start = output.find("JSON_RESULTS_START") + len("JSON_RESULTS_START")
        end = output.find("JSON_RESULTS_END")
        json_str = output[start:end].strip()
        try:
            results = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
    
    # Parse errors
    if "JSON_ERRORS_START" in output and "JSON_ERRORS_END" in output:
        start = output.find("JSON_ERRORS_START") + len("JSON_ERRORS_START")
        end = output.find("JSON_ERRORS_END")
        json_str = output[start:end].strip()
        try:
            errors = json.loads(json_str)
        except:
            pass
    
    # If no JSON results were found, show raw output for debugging
    if not results and not errors:
        print("\nRaw output:")
        print(output)
    
    # Clean up temporary file
    os.remove(script_path)
    
    return results, errors

def save_admin_results(results, errors):
    """Save admin account creation results"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if results:
        # Save detailed info
        filename = "./deployment/canvas/configs/canvas_admin_users.json"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "canvas_url": "http://localhost:10001",
                "created_at": timestamp,
                "total_admin_users": len(results),
                "admin_users": results
            }, f, indent=2, ensure_ascii=False)
        
        # Save admin token list
        tokens_file = "./deployment/canvas/configs/canvas_admin_tokens.txt"
        with open(tokens_file, 'w') as f:
            f.write("# Canvas Admin User Tokens\n")
            f.write(f"# Generated: {timestamp}\n")
            f.write(f"# Total: {len(results)} admin users\n\n")
            for user in results:
                f.write(f"{user['email']}: {user['token']}\n")
        
        print("\n✅ Admin accounts created successfully:")
        print(f"   - Detailed info: {filename}")
        print(f"   - Token list: {tokens_file}")
        
        # Show created account info
        print("\nCreated admin accounts:")
        for user in results:
            print(f"  📧 Email: {user['email']}")
            print(f"  🔑 Password: {user['password']}")
            print(f"  🎫 Token: {user['token']}")
            print(f"  👤 Role: {user['role']}")
            print()
    
    # Save error log if any
    if errors:
        error_file = f"./deployment/canvas/configs/canvas_admin_errors_{timestamp}.json"
        with open(error_file, 'w') as f:
            json.dump(errors, f, indent=2)
        print(f"\n❌ Error log: {error_file}")

def main():
    """Main function"""
    print("=== Canvas Admin Account Creation Tool ===")
    print("Creating 3 admin accounts with predefined credentials...")
    
    start_time = time.time()
    
    try:
        results, errors = create_admin_accounts()
        
        if results:
            save_admin_results(results, errors)
            print(f"\n🎉 Successfully created {len(results)} admin account(s)")
        else:
            print("\n❌ No admin accounts were created")
            if errors:
                print("\nErrors encountered:")
                for error in errors:
                    print(f"  - {error['email']}: {error['error']}")
        
        end_time = time.time()
        print(f"\nTotal time: {end_time - start_time:.1f} seconds")
        
    except Exception as e:
        print(f"\n❌ Script failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())