#!/usr/bin/env python3
# 这是给canvas生成账户的脚本
# 可以自定义你需要在canvas容器里建立多少个用户
# 生成完用户可以拿到姓名，邮箱，token， 密码（现在是统一的），sis_user_id，pseudonym_id
import json
import random
import subprocess
import os
import time
from datetime import datetime

# 英文名字库
FIRST_NAMES = [
    'James', 'John', 'Robert', 'Michael', 'William', 'David', 'Richard', 'Joseph', 'Thomas', 'Charles',
    'Christopher', 'Daniel', 'Matthew', 'Anthony', 'Donald', 'Mark', 'Paul', 'Steven', 'Andrew', 'Kenneth',
    'Joshua', 'Kevin', 'Brian', 'George', 'Edward', 'Ronald', 'Timothy', 'Jason', 'Jeffrey', 'Ryan',
    'Jacob', 'Gary', 'Nicholas', 'Eric', 'Jonathan', 'Stephen', 'Larry', 'Justin', 'Scott', 'Brandon',
    'Mary', 'Patricia', 'Jennifer', 'Linda', 'Elizabeth', 'Barbara', 'Susan', 'Jessica', 'Sarah', 'Karen',
    'Nancy', 'Lisa', 'Betty', 'Margaret', 'Sandra', 'Ashley', 'Kimberly', 'Emily', 'Donna', 'Michelle',
    'Dorothy', 'Carol', 'Amanda', 'Melissa', 'Deborah', 'Stephanie', 'Rebecca', 'Sharon', 'Laura', 'Cynthia'
]

LAST_NAMES = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez',
    'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin',
    'Lee', 'Perez', 'Thompson', 'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson',
    'Walker', 'Young', 'Allen', 'King', 'Wright', 'Scott', 'Torres', 'Nguyen', 'Hill', 'Flores'
]

CONTAINER_NAME = "canvas-docker"
BUNDLE_PATH = "/opt/canvas/.gems/bin/bundle"
CANVAS_DIR = "/opt/canvas/canvas-lms"

def get_next_sis_id():
    """获取下一个可用的 SIS ID"""
    check_script = r'''
# 查找最大的 MCP 开头的 SIS ID
max_id = Pseudonym.where("sis_user_id LIKE 'MCP%'").pluck(:sis_user_id).map { |id| 
  id.match(/MCP(\d+)/) ? $1.to_i : 0 
}.max || 0

puts "MAX_SIS_ID:#{max_id}"
'''
    
    with open('./deployment/canvas/tmp/check_sis_id.rb', 'w') as f:
        f.write(check_script)
    
    subprocess.run(['podman', 'cp', './deployment/canvas/tmp/check_sis_id.rb', f'{CONTAINER_NAME}:/tmp/'])
    
    cmd = f"cd {CANVAS_DIR} && GEM_HOME=/opt/canvas/.gems {BUNDLE_PATH} exec rails runner /tmp/check_sis_id.rb"
    result = subprocess.run(
        ['podman', 'exec', CONTAINER_NAME, 'bash', '-c', cmd],
        capture_output=True,
        text=True
    )
    
    try:
        max_id_line = [line for line in result.stdout.split('\n') if 'MAX_SIS_ID:' in line][0]
        max_id = int(max_id_line.split(':')[1])
        return max_id + 1
    except:
        return 1

def generate_unique_users(count=200, start_id=1):
    """生成唯一的用户数据"""
    users = []
    used_emails = set()
    
    for i in range(count):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        full_name = f"{first_name} {last_name}"
        
        # 生成唯一邮箱 - 使用数字后缀
        base_email = f"{first_name.lower()}.{last_name.lower()}"
        email = f"{base_email}@mcp.edu"
        
        # 如果邮箱已存在，添加数字后缀
        counter = 0
        while email in used_emails:
            counter += 1
            if counter > 99:
                raise ValueError(f"无法为 {first_name} {last_name} 生成唯一邮箱，已尝试99个后缀")
            email = f"{base_email}.{counter:02d}@mcp.edu"
        
        used_emails.add(email)
        
        users.append({
            'name': full_name,
            'short_name': first_name,
            'email': email,
            'password': 'Password123!',
            'sis_user_id': f"MCP{start_id + i:06d}"
        })
    
    return users

def create_batch_script(users, batch_num):
    """创建批量创建用户的 Ruby 脚本"""
    return '''
require 'json'

users_data = JSON.parse(%s)
results = []
errors = []

puts "Starting batch %d with #{users_data.length} users..."

# 获取默认账户
account = Account.default

users_data.each_with_index do |user_data, index|
  begin
    # 开始事务
    ActiveRecord::Base.transaction do
      # 创建用户
      user = User.create!(
        name: user_data['name'],
        short_name: user_data['short_name']
      )
      
      # 创建登录凭证 - 使用 account
      pseudonym = Pseudonym.new(
        user: user,
        account: account,
        unique_id: user_data['email'],
        password: user_data['password'],
        password_confirmation: user_data['password']
      )
      
      # 只有在 SIS ID 不存在时才设置
      existing_sis = Pseudonym.where(sis_user_id: user_data['sis_user_id']).exists?
      if !existing_sis
        pseudonym.sis_user_id = user_data['sis_user_id']
      else
        # 生成新的 SIS ID
        timestamp = Time.now.to_i
        pseudonym.sis_user_id = "MCP#{timestamp}_#{index}"
      end
      
      pseudonym.save!
      
      # 创建 API token
      token = user.access_tokens.create!(
        purpose: "Auto Generated API Token"
      )
      
      results << {
        'id' => user.id,
        'name' => user_data['name'],
        'email' => user_data['email'],
        'password' => user_data['password'],
        'token' => token.full_token,
        'sis_user_id' => pseudonym.sis_user_id,
        'pseudonym_id' => pseudonym.id
      }
    end
    
    # 进度提示
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

# 输出结果
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
    """执行单个批次的用户创建"""
    script = create_batch_script(users, batch_num)
    script_path = f'./deployment/canvas/tmp/create_batch_{batch_num}.rb'
    script_path_in_container = f'/tmp/create_batch_{batch_num}.rb'
    
    with open(script_path, 'w') as f:
        f.write(script)
    
    subprocess.run(['podman', 'cp', script_path, f'{CONTAINER_NAME}:{script_path_in_container}'])
    
    cmd = f"cd {CANVAS_DIR} && GEM_HOME=/opt/canvas/.gems {BUNDLE_PATH} exec rails runner {script_path_in_container}"
    result = subprocess.run(
        ['podman', 'exec', CONTAINER_NAME, 'bash', '-c', cmd],
        capture_output=True,
        text=True
    )
    
    output = result.stdout + result.stderr
    batch_results = []
    batch_errors = []
    
    # 提取结果
    if "JSON_RESULTS_START" in output and "JSON_RESULTS_END" in output:
        start = output.find("JSON_RESULTS_START") + len("JSON_RESULTS_START")
        end = output.find("JSON_RESULTS_END")
        json_str = output[start:end].strip()
        try:
            batch_results = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
    
    # 提取错误
    if "JSON_ERRORS_START" in output and "JSON_ERRORS_END" in output:
        start = output.find("JSON_ERRORS_START") + len("JSON_ERRORS_START")
        end = output.find("JSON_ERRORS_END")
        json_str = output[start:end].strip()
        try:
            batch_errors = json.loads(json_str)
        except:
            pass
    
    # 如果没有找到 JSON 结果，显示原始输出用于调试
    if not batch_results and not batch_errors:
        print(f"\nRaw output for batch {batch_num}:")
        print(output[:1000])
        if len(output) > 1000:
            print("...")
    
    os.remove(script_path)
    
    return batch_results, batch_errors

def create_users(total_count=200, batch_size=10):
    """主函数：创建用户"""
    print(f"\nGetting starting SIS ID...")
    start_sis_id = get_next_sis_id()
    print(f"Will start from MCP{start_sis_id:06d}")
    
    users = generate_unique_users(total_count, start_sis_id)
    all_results = []
    all_errors = []
    
    print(f"\nStarting batch creation of {total_count} users...")
    print(f"Batch size: {batch_size}")
    
    start_time = time.time()
    
    for i in range(0, total_count, batch_size):
        batch = users[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        print(f"\nProcessing batch {batch_num} (users {i+1}-{min(i+batch_size, total_count)})...")
        
        batch_results, batch_errors = execute_batch(batch, batch_num)
        
        all_results.extend(batch_results)
        all_errors.extend(batch_errors)
        
        print(f"✅ Batch {batch_num} completed: {len(batch_results)} success, {len(batch_errors)} failed")
        
        # 显示错误详情
        if batch_errors:
            print("Error details:")
            for err in batch_errors[:3]:  # 只显示前3个错误
                print(f"  - {err['email']}: {err['error']}")
        
        if i + batch_size < total_count:
            time.sleep(0.5)
    
    end_time = time.time()
    
    print(f"\n=== Creation completed ===")
    print(f"Success: {len(all_results)} users")
    print(f"Failed: {len(all_errors)} users") 
    print(f"Time taken: {end_time - start_time:.1f} seconds")
    
    return all_results, all_errors

def save_results(results, errors):
    """保存结果"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存成功的用户
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
        
        # 保存简化的 token 列表
        tokens_file = f"./deployment/canvas/configs/canvas_tokens.txt"
        with open(tokens_file, 'w') as f:
            f.write("# Canvas User Tokens\n")
            f.write(f"# Generated: {timestamp}\n")
            f.write(f"# Total: {len(results)} users\n\n")
            for user in results:
                f.write(f"{user['email']}: {user['token']}\n")
        
        #保存一个简单的txt文件记录更新时间
        with open(f"./deployment/canvas/configs/canvas_users_update_time.txt", 'w') as f:
            f.write(f"{timestamp}")

        print(f"\n✅ Results saved:")
        print(f"   - User data: {filename}")
        print(f"   - Token list: {tokens_file}")
        
        # 显示示例
        print("\nSample users:")
        for user in results[:3]:
            print(f"  {user['name']} ({user['email']})")
            print(f"  Token: {user['token'][:40]}...")
    
    # 保存错误日志
    if errors:
        error_file = f"./deployment/canvas/configs/canvas_errors_{timestamp}.json"
        os.makedirs(os.path.dirname(error_file), exist_ok=True)
        with open(error_file, 'w') as f:
            json.dump(errors, f, indent=2)
        print(f"\n❌ Error log: {error_file}")

def main():
    TOTAL = 200

    """主函数"""
    print("=== Canvas Batch User Creation Tool v2 ===")
    
    # 先测试创建一个用户
    print("\nTesting single user creation...")
    test_results, test_errors = create_users(1, 1)
    
    if test_results:
        print("✅ Test successful!")
        
        # 询问是否继续
        # total = input("\nHow many users to create? (default 200): ")
        # total = int(total) if total else 200
        total = TOTAL
        
        if total > 1:
            # batch = input("How many per batch? (default 10): ")
            # batch = int(batch) if batch else 10
            batch = TOTAL
            
            # confirm = input(f"\nWill create {total} users, {batch} per batch. Continue? (y/n): ")
            confirm = 'y'
            if confirm.lower() == 'y':
                results, errors = create_users(total, batch)
                save_results(results, errors)
            else:
                print("Cancelled")
        else:
            save_results(test_results, test_errors)
    else:
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

if __name__ == "__main__":
    # ./deployment/canvas/tmp create this dir in advance
    os.makedirs('./deployment/canvas/tmp', exist_ok=True)
    main()