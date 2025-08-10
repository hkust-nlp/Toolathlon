#!/usr/bin/env python3
# 这是给canvas生成账户的脚本
# 可以自定义你需要在canvas容器里建立多少个用户
# 生成完用户可以拿到姓名，邮箱，token， 密码（现在是统一的），sis_user_id，pseudonym_id
#
# 使用方法:
# python create_canvas_user.py                     # 创建所有用户
# python create_canvas_user.py -n 50               # 创建前50个用户
# python create_canvas_user.py -n 100 --batch-size 20  # 创建前100个用户，每批20个
# python create_canvas_user.py --skip-test         # 跳过测试直接创建所有用户
import json
import subprocess
import os
import time
import argparse
from datetime import datetime

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

def load_users_from_json():
    """从configs/users_data.json读取用户数据"""
    try:
        with open('configs/users_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        users = []
        for user in data['users']:
            users.append({
                'name': user['full_name'],
                'short_name': user['first_name'],
                'email': user['email'],
                'password': user['password'],
                'canvas_token': user.get('canvas_token', ''),
                'sis_user_id': f"MCP{user['id']:06d}"
            })
        
        print(f"Loaded {len(users)} users from configs/users_data.json")
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
      
      # 创建 API token - 使用预设token或生成新token
      if user_data['canvas_token'] && !user_data['canvas_token'].empty?
        # 使用预设的token
        token = user.access_tokens.create!(
          purpose: "Predefined API Token",
          token: user_data['canvas_token']
        )
        token_value = user_data['canvas_token']
      else
        # 生成新的token
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

def create_users(total_count=None, batch_size=10):
    """主函数：创建用户"""
    print(f"\nLoading users from JSON...")
    users = load_users_from_json()
    
    if not users:
        print("No users loaded. Exiting.")
        return [], []
    
    if total_count is None:
        total_count = len(users)
    else:
        users = users[:total_count]
    
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
        
        # 显示错误详情
        if batch_errors:
            print("Error details:")
            for err in batch_errors[:3]:  # 只显示前3个错误
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
        with open("./deployment/canvas/configs/canvas_users_update_time.txt", 'w') as f:
            f.write(f"{timestamp}")

        print("\n✅ Results saved:")
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
    """主函数"""
    # 设置命令行参数
    parser = argparse.ArgumentParser(description='Canvas用户批量创建工具')
    parser.add_argument('-n', '--count', type=int, default=None, 
                        help='指定创建前N个用户（默认创建所有用户）')
    parser.add_argument('--batch-size', type=int, default=10,
                        help='批处理大小（默认10个用户一批）')
    parser.add_argument('--skip-test', action='store_true',
                        help='跳过测试直接创建所有用户')
    
    args = parser.parse_args()
    
    print("=== Canvas Batch User Creation Tool v2 ===")
    
    # 获取用户总数和实际要创建的数量
    users = load_users_from_json()
    if not users:
        print("No users loaded. Exiting.")
        return
    
    total_available = len(users)
    target_count = args.count if args.count is not None else total_available
    target_count = min(target_count, total_available)  # 确保不超过可用数量
    
    print("\n用户信息:")
    print(f"  可用用户总数: {total_available}")
    print(f"  计划创建数量: {target_count}")
    print(f"  批处理大小: {args.batch_size}")
    
    if not args.skip_test:
        # 先测试创建一个用户
        print("\nTesting single user creation...")
        test_results, test_errors = create_users(1, 1)
        
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
        
        # 如果只要创建1个用户，直接保存测试结果
        if target_count == 1:
            save_results(test_results, test_errors)
            return
        
        # 调整目标数量（减去已测试的1个）
        target_count -= 1
        print(f"\n继续创建剩余 {target_count} 个用户...")
    
    # 创建用户
    if target_count > 0:
        results, errors = create_users(target_count, args.batch_size)
        
        # 如果有测试结果，合并到最终结果中
        if not args.skip_test and 'test_results' in locals():
            results = test_results + results
            
        save_results(results, errors)
    else:
        print("没有用户需要创建")

if __name__ == "__main__":
    # ./deployment/canvas/tmp create this dir in advance
    os.makedirs('./deployment/canvas/tmp', exist_ok=True)
    main()