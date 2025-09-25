#!/usr/bin/env python3
"""
Generate enhanced statistics for parallel evaluation results.
This script processes evaluation results from parallel task execution and creates
comprehensive statistics similar to global_eval.py output.
"""

import json
import glob
import os
import sys
from pathlib import Path
import argparse


def extract_task_name(eval_file_path, tasks_folder):
    """Extract clean task name from evaluation file path"""
    # Current path structure: dumps_0908_new/finalpool/taskname/eval_res.json
    # We need the taskname part (second from the end)
    path_parts = eval_file_path.split('/')
    if len(path_parts) >= 2:
        task_name = path_parts[-2]  # Get taskname from dumps_0908_new/finalpool/taskname/eval_res.json
    else:
        # Fallback to parent directory
        task_name = os.path.basename(os.path.dirname(eval_file_path))
    
    # Remove common prefixes to get clean task name
    task_name = task_name.replace('SingleUserTurn-', '').replace(f'{tasks_folder}-', '')
    return task_name


def generate_enhanced_stats(dump_path, tasks_folder, temp_config, task_list_file):
    """Generate enhanced statistics from evaluation results"""

    # Find all eval_res.json files with more specific pattern
    eval_files = glob.glob(f'{dump_path}/{tasks_folder}/*/eval_res.json')
    status_files = glob.glob(f'{dump_path}/{tasks_folder}/*/status.json')

    successful_tasks = []
    unsuccessful_tasks = []
    all_turns = []
    all_tool_calls = []
    tasks_with_valid_turns = []
    tasks_without_valid_turns = []

    # 新增：基于 status.json 的统计
    tasks_with_preprocess_done = []
    tasks_with_preprocess_fail = []
    tasks_with_running_done = []
    tasks_with_running_fail = []
    tasks_with_running_timeout = []
    tasks_with_running_max_turns = []
    tasks_with_running_null = []
    tasks_with_evaluation_pass = []
    tasks_with_evaluation_fail = []
    tasks_with_evaluation_null = []

    # 兼容性：基于原有逻辑的统计
    tasks_with_failed_status = []
    task_with_max_turns_exceeded = []
    tasks_with_success_status = []

    print(f'📊 Processing {len(status_files)} status files...')

    for status_file in status_files:
        task_name = extract_task_name(status_file, tasks_folder)
        try:
            eval_file = status_file.replace('status.json', 'eval_res.json')
            if os.path.exists(eval_file):
                with open(eval_file, 'r') as f:
                    eval_data = json.load(f)

                # Extract task name from path
                # task_name = extract_task_name(eval_file, tasks_folder)

                # Check if task passed (原有逻辑保持不变)
                if eval_data.get('pass', False):
                    successful_tasks.append(task_name)
                else:
                    unsuccessful_tasks.append(task_name)

            # 优先检查 status.json
            # status_file = eval_file.replace('eval_res.json', 'status.json')
            if os.path.exists(status_file):
                try:
                    with open(status_file, 'r', encoding='utf-8') as f:
                        status_data = json.load(f)

                    # 统计各阶段状态
                    preprocess_status = status_data.get('preprocess', None)
                    running_status = status_data.get('running', None)
                    evaluation_status = status_data.get('evaluation', None)

                    if preprocess_status == 'done':
                        tasks_with_preprocess_done.append(task_name)
                    elif preprocess_status == 'fail':
                        tasks_with_preprocess_fail.append(task_name)

                    if running_status == 'done':
                        tasks_with_running_done.append(task_name)
                    elif running_status == 'fail':
                        tasks_with_running_fail.append(task_name)
                    elif running_status == 'timeout':
                        tasks_with_running_timeout.append(task_name)
                    elif running_status == 'max_turn_exceeded':
                        tasks_with_running_max_turns.append(task_name)
                    elif running_status is None:
                        tasks_with_running_null.append(task_name)

                    if evaluation_status is not None:
                        if evaluation_status:
                            tasks_with_evaluation_pass.append(task_name)
                        else:
                            tasks_with_evaluation_fail.append(task_name)
                    else:
                        tasks_with_evaluation_null.append(task_name)

                except Exception as e:
                    print(f'⚠️  Error reading status.json for {task_name}: {e}')

            # 尝试从 traj_log.json 获取详细统计信息
            log_file = eval_file.replace('eval_res.json', 'traj_log.json')
            run_log = eval_file.replace('eval_res.json', 'run.log')

            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        log_data = json.load(f)

                    # 兼容性：保持原有的状态统计（用于对比）
                    task_status = log_data.get('status', 'unknown')
                    if task_status == 'failed':
                        tasks_with_failed_status.append(task_name)
                        if os.path.exists(run_log):
                            with open(run_log, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if "[THIS IS A TAG FOR MAX TURNS EXCEEDED]" in content:
                                    task_with_max_turns_exceeded.append(task_name)
                    elif task_status == 'success':
                        tasks_with_success_status.append(task_name)

                    # Extract turn count and tool calls from log
                    num_turns = log_data.get('key_stats', {}).get('total_turns', 0)
                    num_tool_calls = log_data.get('key_stats', {}).get('tool_calls', 0)

                    if num_turns > 0:
                        all_turns.append(num_turns)
                        tasks_with_valid_turns.append(task_name)
                    else:
                        tasks_without_valid_turns.append(task_name)

                    # Always collect tool calls if available (even if turns is 0)
                    if num_tool_calls > 0:
                        all_tool_calls.append(num_tool_calls)
                except Exception as e:
                    print(f'⚠️  Error reading traj_log.json for {task_name}: {e}')
                    tasks_without_valid_turns.append(task_name)
            else:
                tasks_without_valid_turns.append(task_name)

        except Exception as e:
            print(f'⚠️  Error processing {eval_file}: {e}')

    # Calculate statistics
    total_tasks = len(status_files)
    average_turns = sum(all_turns) / len(all_turns) if all_turns else 0
    average_tool_calls = sum(all_tool_calls) / len(all_tool_calls) if all_tool_calls else 0
    success_rate = len(successful_tasks) / total_tasks if total_tasks > 0 else 0

    # Create enhanced statistics with status.json information
    enhanced_stats = {
        'total_tasks': total_tasks,
        'successful_tasks_count': len(successful_tasks),
        'unsuccessful_tasks_count': len(unsuccessful_tasks),
        'average_success_rate': success_rate,
        'average_turns': average_turns,
        'average_tool_calls': average_tool_calls,
        'successful_tasks': sorted(successful_tasks),
        'unsuccessful_tasks': sorted(unsuccessful_tasks),

        # 新增：基于 status.json 的详细统计
        'status_breakdown': {
            'preprocess': {
                'done_count': len(tasks_with_preprocess_done),
                'fail_count': len(tasks_with_preprocess_fail),
                'done_tasks': sorted(tasks_with_preprocess_done),
                'fail_tasks': sorted(tasks_with_preprocess_fail)
            },
            'running': {
                'done_count': len(tasks_with_running_done),
                'fail_count': len(tasks_with_running_fail),
                'timeout_count': len(tasks_with_running_timeout),
                'max_turns_count': len(tasks_with_running_max_turns),
                'null_count': len(tasks_with_running_null),
                'done_tasks': sorted(tasks_with_running_done),
                'fail_tasks': sorted(tasks_with_running_fail),
                'timeout_tasks': sorted(tasks_with_running_timeout),
                'max_turns_tasks': sorted(tasks_with_running_max_turns),
                'null_tasks': sorted(tasks_with_running_null)
            },
            'evaluation': {
                'pass_count': len(tasks_with_evaluation_pass),
                'fail_count': len(tasks_with_evaluation_fail),
                'null_count': len(tasks_with_evaluation_null),
                'pass_tasks': sorted(tasks_with_evaluation_pass),
                'fail_tasks': sorted(tasks_with_evaluation_fail),
                'null_tasks': sorted(tasks_with_evaluation_null)
            }
        },

        # 保留原有的统计信息用于兼容性
        'legacy_execution_status': {
            'tasks_with_failed_status_count': len(tasks_with_failed_status),
            'tasks_with_success_status_count': len(tasks_with_success_status),
            'tasks_with_max_turns_exceeded_count (subset of failed)': len(task_with_max_turns_exceeded),
            'tasks_with_failed_status': sorted(tasks_with_failed_status),
            'tasks_with_success_status': sorted(tasks_with_success_status),
            'tasks_with_max_turns_exceeded': sorted(task_with_max_turns_exceeded)
        },

        'summary': {
            'tasks_with_valid_turns': len(tasks_with_valid_turns),
            'tasks_without_valid_turns': len(tasks_without_valid_turns),
            'tasks_without_valid_turns_list': sorted(tasks_without_valid_turns),
            'config_used': temp_config,
            'task_list_file': task_list_file
        }
    }

    # Save enhanced statistics
    stats_file = f'{dump_path}/eval_stats.json'
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(enhanced_stats, f, indent=2)

    print(f'✅ Enhanced statistics saved to: {stats_file}')
    print(f'📊 Summary: {len(successful_tasks)}/{total_tasks} tasks passed ({success_rate:.1%})')
    print(f'🔄 Average turns: {average_turns:.1f}')
    print(f'🔧 Average tool calls: {average_tool_calls:.1f}')

    # 新增：打印基于 status.json 的统计信息
    print(f'📈 Status breakdown:')
    print(f'   Preprocess: {len(tasks_with_preprocess_done)} done, {len(tasks_with_preprocess_fail)} fail')
    print(f'   Running: {len(tasks_with_running_done)} done, {len(tasks_with_running_fail)} fail, '
          f'{len(tasks_with_running_timeout)} timeout, {len(tasks_with_running_max_turns)} max_turns, {len(tasks_with_running_null)} null')
    print(f'   Evaluation: {len(tasks_with_evaluation_pass)} pass, {len(tasks_with_evaluation_fail)} fail, {len(tasks_with_evaluation_null)} null')

    # 兼容性输出
    print(f'📈 Legacy status: {len(tasks_with_success_status)} success, {len(tasks_with_failed_status)} failed')

    return enhanced_stats


def main():
    parser = argparse.ArgumentParser(description='Generate enhanced statistics for parallel evaluation results')
    parser.add_argument('--dump_path', required=True, help='Path to dump directory containing results')
    parser.add_argument('--tasks_folder', required=True, help='Name of tasks folder')
    parser.add_argument('--temp_config', required=True, help='Path to temporary config file used')
    parser.add_argument('--task_list_file', default='all_tasks', help='Task list file used (default: all_tasks)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.dump_path):
        print(f'❌ Error: Dump path does not exist: {args.dump_path}')
        sys.exit(1)
    
    try:
        generate_enhanced_stats(args.dump_path, args.tasks_folder, args.temp_config, args.task_list_file)
    except Exception as e:
        print(f'❌ Error generating statistics: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main() 