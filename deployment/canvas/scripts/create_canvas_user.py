#!/usr/bin/env python3
# This script is used to generate accounts for Canvas.
# You can specify how many users to create in the Canvas container.
# After users are created, you will get: full name, email, token, password (currently unified), sis_user_id, pseudonym_id.
#
# Usage examples:
# python create_canvas_user.py                              # Create all users (skip already exists)
# python create_canvas_user.py -n 50                        # Create the first 50 users
# python create_canvas_user.py --start-id 1 --end-id 20     # Create users with ID 1-20
# python create_canvas_user.py --start-id 101 --end-id 120  # Create users with ID 101-120
# python create_canvas_user.py -n 100 --batch-size 20       # Create the first 100 users, 20 per batch
# python create_canvas_user.py --skip-test                  # Skip test and directly create all users

import json
import subprocess
import os
import time
import argparse
from datetime import datetime
from configs.global_configs import global_configs

BUNDLE_PATH = "/opt/canvas/.gems/bin/bundle"
CANVAS_DIR = "/opt/canvas/canvas-lms"

def get_next_sis_id():
    """Get the next available SIS ID"""
    check_script = r'''
# Find the maximum SIS ID starting with MCP
max_id = Pseudonym.where("sis_user_id LIKE 'MCP%'").pluck(:sis_user_id).map { |id| 
  id.match(/MCP(\d+)/) ? $1.to_i : 0 
}.max || 0

puts "MAX_SIS_ID:#{max_id}"
'''
    with open('./deployment/canvas/tmp/check_sis_id.rb', 'w') as f:
        f.write(check_script)
    
    subprocess.run([global_configs.podman_or_docker, 'cp', './deployment/canvas/tmp/check_sis_id.rb', f'{CONTAINER_NAME}:/tmp/'])
    
    cmd = f"cd {CANVAS_DIR} && GEM_HOME=/opt/canvas/.gems {BUNDLE_PATH} exec rails runner /tmp/check_sis_id.rb"
    result = subprocess.run(
        [global_configs.podman_or_docker, 'exec', CONTAINER_NAME, 'bash', '-c', cmd],
        capture_output=True,
        text=True
    )
    try:
        max_id_line = [line for line in result.stdout.split('\n') if 'MAX_SIS_ID:' in line][0]
        max_id = int(max_id_line.split(':')[1])
        return max_id + 1
    except:
        return 1

def check_existing_users(emails):
    """Check if emails already exist in Canvas"""
    if not emails:
        return []
    
    emails_str = "', '".join(emails)
    check_script = f'''
existing_emails = Pseudonym.where(unique_id: ['{emails_str}']).pluck(:unique_id)
puts "EXISTING_EMAILS:" + existing_emails.join(",")
'''
    with open('./deployment/canvas/tmp/check_existing_users.rb', 'w') as f:
        f.write(check_script)
    
    subprocess.run([global_configs.podman_or_docker, 'cp', './deployment/canvas/tmp/check_existing_users.rb', f'{CONTAINER_NAME}:/tmp/'])
    
    cmd = f"cd {CANVAS_DIR} && GEM_HOME=/opt/canvas/.gems {BUNDLE_PATH} exec rails runner /tmp/check_existing_users.rb"
    result = subprocess.run(
        [global_configs.podman_or_docker, 'exec', CONTAINER_NAME, 'bash', '-c', cmd],
        capture_output=True,
        text=True
    )
    try:
        existing_line = [line for line in result.stdout.split('\n') if 'EXISTING_EMAILS:' in line][0]
        existing_emails = existing_line.split(':', 1)[1].split(',') if ':' in existing_line and existing_line.split(':', 1)[1] else []
        return [email.strip() for email in existing_emails if email.strip()]
    except:
        return []

def load_users_from_json(start_id=None, end_id=None):
    """Load users from configs/users_data.json, support filtering by ID range"""
    try:
        with open('configs/users_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        users = []
        for user in data['users']:
            user_id = user['id']
            # If ID range is specified, filter
            if start_id is not None and user_id < start_id:
                continue
            if end_id is not None and user_id > end_id:
                continue
            if user['full_name'].startswith('MCP Canvas Admin'):
                continue
            users.append({
                'name': user['full_name'],
                'short_name': user['first_name'],
                'email': user['email'],
                'password': user['password'],
                'canvas_token': user.get('canvas_token', ''),
                'sis_user_id': f"MCP{user['id']:06d}"
            })
        
        range_info = ""
        if start_id is not None or end_id is not None:
            range_info = f" (ID range: {start_id or 'start'}-{end_id or 'end'})"
        
        print(f"Loaded {len(users)} users from configs/users_data.json{range_info}")
        return users
    except FileNotFoundError:
        print("Error: configs/users_data.json not found")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return []
    except KeyError as e:
        print(f"Error: Missing key {e} in JSON data")
        return []

def create_batch_script(users, batch_num):
    """Create Ruby script for batch user creation"""
    return '''
require 'json'

users_data = JSON.parse(%s)
results = []
errors = []

puts "Starting batch %d with #{users_data.length} users..."

# Get the default account
account = Account.default

users_data.each_with_index do |user_data, index|
  begin
    # Start transaction
    ActiveRecord::Base.transaction do
      # Create user
      user = User.create!(
        name: user_data['name'],
        short_name: user_data['short_name']
      )
      
      # Create login credential (pseudonym) - assign to default account
      pseudonym = Pseudonym.new(
        user: user,
        account: account,
        unique_id: user_data['email'],
        password: user_data['password'],
        password_confirmation: user_data['password']
      )
      
      # Set SIS ID if not existed
      existing_sis = Pseudonym.where(sis_user_id: user_data['sis_user_id']).exists?
      if !existing_sis
        pseudonym.sis_user_id = user_data['sis_user_id']
      else
        # If existed, generate new SIS ID
        timestamp = Time.now.to_i
        pseudonym.sis_user_id = "MCP#{timestamp}_#{index}"
      end
      
      pseudonym.save!
      
      # Create API token - use predefined token or generate new
      if user_data['canvas_token'] && !user_data['canvas_token'].empty?
        # Use predefined token
        token = user.access_tokens.create!(
          purpose: "Predefined API Token",
          token: user_data['canvas_token']
        )
        token_value = user_data['canvas_token']
      else
        # Generate new token
        token = user.access_tokens.create!(
          purpose: "Auto Generated API Token"
        )
        token_value = token.full_token
      end
      
      results << {
        'id' => user.id,
        'name' => user_data['name'],
        'email' => user_data['email'],
        'password' => user_data['password'],
        'token' => token_value,
        'sis_user_id' => pseudonym.sis_user_id,
        'pseudonym_id' => pseudonym.id
      }
    end
    
    # Progress info
    if (index + 1) %% 5 == 0 || index == users_data.length - 1
      puts "Progress: #{index + 1}/#{users_data.length} completed"
    end
    
  rescue => e
    errors << {
      'email' => user_data['email'],
      'error' => "#{e.class}: #{e.message}",
      'backtrace' => e.backtrace.first(3)
    }
    puts "Error with #{user_data['email']}: #{e.message}"
  end
end

puts "\\nBatch complete: #{results.length} success, #{errors.length} errors"

# Output result
puts "\\nJSON_RESULTS_START"
puts results.to_json
puts "JSON_RESULTS_END"

if errors.any?
  puts "\\nJSON_ERRORS_START" 
  puts errors.to_json
  puts "JSON_ERRORS_END"
end
''' % (json.dumps(json.dumps(users)), batch_num)

def execute_batch(users, batch_num):
    """Execute creation of a single user batch"""
    script = create_batch_script(users, batch_num)
    script_path = f'./deployment/canvas/tmp/create_batch_{batch_num}.rb'
    script_path_in_container = f'/tmp/create_batch_{batch_num}.rb'
    
    with open(script_path, 'w') as f:
        f.write(script)
    
    subprocess.run([global_configs.podman_or_docker, 'cp', script_path, f'{CONTAINER_NAME}:{script_path_in_container}'])
    
    cmd = f"cd {CANVAS_DIR} && GEM_HOME=/opt/canvas/.gems {BUNDLE_PATH} exec rails runner {script_path_in_container}"
    result = subprocess.run(
        [global_configs.podman_or_docker, 'exec', CONTAINER_NAME, 'bash', '-c', cmd],
        capture_output=True,
        text=True
    )
    output = result.stdout + result.stderr
    batch_results = []
    batch_errors = []
    
    # Parse result
    if "JSON_RESULTS_START" in output and "JSON_RESULTS_END" in output:
        start = output.find("JSON_RESULTS_START") + len("JSON_RESULTS_START")
        end = output.find("JSON_RESULTS_END")
        json_str = output[start:end].strip()
        try:
            batch_results = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
    
    # Parse errors
    if "JSON_ERRORS_START" in output and "JSON_ERRORS_END" in output:
        start = output.find("JSON_ERRORS_START") + len("JSON_ERRORS_START")
        end = output.find("JSON_ERRORS_END")
        json_str = output[start:end].strip()
        try:
            batch_errors = json.loads(json_str)
        except:
            pass
    
    # If no json result found, show raw output for debugging
    if not batch_results and not batch_errors:
        print(f"\nRaw output for batch {batch_num}:")
        print(output[:1000])
        if len(output) > 1000:
            print("...")
    
    os.remove(script_path)
    
    return batch_results, batch_errors

def create_users(users, batch_size=10):
    """Main function to create users"""
    if not users:
        print("No users to create. Exiting.")
        return [], []
    
    # Check for existing users
    print(f"\nChecking for existing users...")
    emails = [user['email'] for user in users]
    existing_emails = check_existing_users(emails)
    
    if existing_emails:
        print(f"Found {len(existing_emails)} existing users, skipping them:")
        for email in existing_emails[:5]:  # Show only first 5
            print(f"  - {email}")
        if len(existing_emails) > 5:
            print(f"  ... and {len(existing_emails) - 5} more")
        
        # Filter out users that already exist
        users = [user for user in users if user['email'] not in existing_emails]
        
        if not users:
            print("All users already exist. Nothing to create.")
            return [], []
    
    all_results = []
    all_errors = []
    
    print(f"\nStarting batch creation of {len(users)} users...")
    print(f"Batch size: {batch_size}")
    
    start_time = time.time()
    
    for i in range(0, len(users), batch_size):
        batch = users[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        print(f"\nProcessing batch {batch_num} (users {i+1}-{min(i+batch_size, len(users))})...")
        
        batch_results, batch_errors = execute_batch(batch, batch_num)
        
        all_results.extend(batch_results)
        all_errors.extend(batch_errors)
        
        print(f"✅ Batch {batch_num} completed: {len(batch_results)} success, {len(batch_errors)} failed")
        
        # Show error details
        if batch_errors:
            print("Error details:")
            for err in batch_errors[:3]:  # Show only first 3 errors
                print(f"  - {err['email']}: {err['error']}")
        
        if i + batch_size < len(users):
            time.sleep(0.5)
    
    end_time = time.time()
    
    print(f"\n=== Creation completed ===")
    print(f"Success: {len(all_results)} users")
    print(f"Failed: {len(all_errors)} users")
    print(f"Time taken: {end_time - start_time:.1f} seconds")
    
    return all_results, all_errors

def save_results(results, errors):
    """Save results to files"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save successfully created users
    if results:
        filename = "./deployment/canvas/configs/canvas_users.json"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "canvas_url": "http://localhost:10001",
                "created_at": timestamp,
                "total_users": len(results),
                "users": results
            }, f, indent=2, ensure_ascii=False)
        
        # Save a simple token list
        tokens_file = f"./deployment/canvas/configs/canvas_tokens.txt"
        with open(tokens_file, 'w') as f:
            f.write("# Canvas User Tokens\n")
            f.write(f"# Generated: {timestamp}\n")
            f.write(f"# Total: {len(results)} users\n\n")
            for user in results:
                f.write(f"{user['email']}: {user['token']}\n")
        
        # Save a simple update timestamp file
        with open("./deployment/canvas/configs/canvas_users_update_time.txt", 'w') as f:
            f.write(f"{timestamp}")

        print("\n✅ Results saved:")
        print(f"   - User data: {filename}")
        print(f"   - Token list: {tokens_file}")
        
        # Show some examples
        print("\nSample users:")
        for user in results[:3]:
            print(f"  {user['name']} ({user['email']})")
            print(f"  Token: {user['token'][:40]}...")
    
    # Save error log
    if errors:
        error_file = f"./deployment/canvas/configs/canvas_errors_{timestamp}.json"
        os.makedirs(os.path.dirname(error_file), exist_ok=True)
        with open(error_file, 'w') as f:
            json.dump(errors, f, indent=2)
        print(f"\n❌ Error log: {error_file}")

def main():
    """Main function"""
    # Argument parsing
    parser = argparse.ArgumentParser(description='Canvas bulk user creation tool')
    parser.add_argument('-n', '--count', type=int, default=None, 
                        help='Create the first N users (default: all)')
    parser.add_argument('--start-id', type=int, default=None,
                        help='Set starting user ID (inclusive)')
    parser.add_argument('--end-id', type=int, default=None,
                        help='Set ending user ID (inclusive)')
    parser.add_argument('--batch-size', type=int, default=10,
                        help='Batch size (default: 10 users per batch)')
    parser.add_argument('--skip-test', action='store_true',
                        help='Skip test and create users directly')
    parser.add_argument("--container-name", type=str, default="canvas-docker")
    args = parser.parse_args()
    
    global CONTAINER_NAME
    CONTAINER_NAME = args.container_name

    print("=== Canvas Batch User Creation Tool v3 ===")
    
    # Check argument conflicts
    if args.count is not None and (args.start_id is not None or args.end_id is not None):
        print("❌ Error: Cannot use --count with --start-id/--end-id")
        return
    
    # Load user data
    print(f"\nLoading users from JSON...")
    users = load_users_from_json(args.start_id, args.end_id)
    if not users:
        print("No users loaded. Exiting.")
        return
    
    # If --count parameter is used, truncate user list
    if args.count is not None:
        users = users[:args.count]
    
    total_users = len(users)
    
    print("\nUser Info:")
    if args.start_id is not None or args.end_id is not None:
        print(f"  ID Range: {args.start_id or 'start'}-{args.end_id or 'end'}")
    if args.count is not None:
        print(f"  Limit: {args.count}")
    print(f"  Total to be processed: {total_users}")
    print(f"  Batch size: {args.batch_size}")
    
    if not args.skip_test and total_users > 0:
        # Test creating one user first
        print("\nTesting single user creation...")
        test_users = [users[0]]
        test_results, test_errors = create_users(test_users, 1)
        
        if not test_results:
            print("❌ Test failed!")
            if test_errors:
                print("\nError details:")
                for err in test_errors:
                    print(f"Email: {err['email']}")
                    print(f"Error: {err['error']}")
                    if 'backtrace' in err:
                        print("Backtrace:")
                        for line in err['backtrace']:
                            print(f"  {line}")
            return
        
        print("✅ Test successful!")
        
        # If only one user to create, save test result directly
        if total_users == 1:
            save_results(test_results, test_errors)
            return
        
        # Remove tested user from the list
        users = users[1:]
        print(f"\nContinue creating the remaining {len(users)} users...")
    
    # Create users
    if users:
        results, errors = create_users(users, args.batch_size)
        
        # Merge test result if any
        if not args.skip_test and 'test_results' in locals():
            results = test_results + results
            
        save_results(results, errors)
    else:
        print("No users to create.")

if __name__ == "__main__":
    # Make sure ./deployment/canvas/tmp exists
    os.makedirs('./deployment/canvas/tmp', exist_ok=True)
    main()