#!/usr/bin/env python3
"""
测试 train-ticket-plan evaluation 逻辑的脚本
"""

import json
import tempfile
import os
from pathlib import Path
import sys

# 导入evaluation模块
from .evaluation.main import primary_check

def create_test_data():
    """创建测试数据文件"""
    test_cases = []
    
    # 测试案例1: 中文站名，符合所有要求
    case1_chinese = {
        "thursday": {
            "bj2qf": {
                "train number": "G385",
                "departure station": "北京南",
                "arrival station": "曲阜东",
                "departure time": "18:44",
                "arrival time": "21:26"
            },
            "sh2qf": {
                "train number": "G162", 
                "departure station": "上海虹桥",
                "arrival station": "曲阜东",
                "departure time": "17:46",
                "arrival time": "21:31"
            }
        },
        "sunday": {
            "qf2bj": {
                "train number": "G128",
                "departure station": "曲阜东",
                "arrival station": "北京南", 
                "departure time": "15:03",
                "arrival time": "17:22"
            },
            "qf2sh": {
                "train number": "G1227",
                "departure station": "曲阜东",
                "arrival station": "上海虹桥",
                "departure time": "15:01", 
                "arrival time": "18:48"
            }
        }
    }
    test_cases.append(("中文站名_正常情况", case1_chinese, True))
    
    # 测试案例2: 英文站名，符合所有要求
    case2_english = {
        "thursday": {
            "bj2qf": {
                "train number": "G385",
                "departure station": "Beijingnan Railway Station",
                "arrival station": "Qufudong Railway Station", 
                "departure time": "18:44",
                "arrival time": "21:26"
            },
            "sh2qf": {
                "train number": "G162",
                "departure station": "Shanghai Hongqiao Railway Station",
                "arrival station": "Qufudong Railway Station",
                "departure time": "17:46", 
                "arrival time": "21:31"
            }
        },
        "sunday": {
            "qf2bj": {
                "train number": "G128",
                "departure station": "Qufudong Railway Station",
                "arrival station": "Beijingnan Railway Station",
                "departure time": "15:03",
                "arrival time": "17:22"
            },
            "qf2sh": {
                "train number": "G1227", 
                "departure station": "Qufudong Railway Station",
                "arrival station": "Shanghai Hongqiao Railway Station",
                "departure time": "15:01",
                "arrival time": "18:48"
            }
        }
    }
    test_cases.append(("英文站名_正常情况", case2_english, True))
    
    # 测试案例3: 周四发车时间过早（不符合要求）
    case3_early_departure = {
        "thursday": {
            "bj2qf": {
                "train number": "G105",
                "departure station": "北京南", 
                "arrival station": "曲阜东",
                "departure time": "07:17",  # 早于17:00
                "arrival time": "09:31"
            },
            "sh2qf": {
                "train number": "G104",
                "departure station": "上海虹桥",
                "arrival station": "曲阜东", 
                "departure time": "06:17",  # 早于17:00
                "arrival time": "10:44"
            }
        },
        "sunday": {
            "qf2bj": {
                "train number": "G128",
                "departure station": "曲阜东",
                "arrival station": "北京南",
                "departure time": "15:03",
                "arrival time": "17:22"
            },
            "qf2sh": {
                "train number": "G1227",
                "departure station": "曲阜东", 
                "arrival station": "上海虹桥",
                "departure time": "15:01",
                "arrival time": "18:48"
            }
        }
    }
    test_cases.append(("周四发车过早", case3_early_departure, False))
    
    # 测试案例4: 周日发车时间不在范围内
    case4_sunday_out_of_range = {
        "thursday": {
            "bj2qf": {
                "train number": "G385",
                "departure station": "北京南",
                "arrival station": "曲阜东",
                "departure time": "18:44",
                "arrival time": "21:26"
            },
            "sh2qf": {
                "train number": "G162",
                "departure station": "上海虹桥", 
                "arrival station": "曲阜东",
                "departure time": "17:46",
                "arrival time": "21:31"
            }
        },
        "sunday": {
            "qf2bj": {
                "train number": "G162",
                "departure station": "曲阜东",
                "arrival station": "北京南",
                "departure time": "21:43",  # 晚于18:00
                "arrival time": "23:51"
            },
            "qf2sh": {
                "train number": "G159",
                "departure station": "曲阜东",
                "arrival station": "上海虹桥",
                "departure time": "19:38",  # 晚于18:00
                "arrival time": "23:18"
            }
        }
    }
    test_cases.append(("周日发车时间超出范围", case4_sunday_out_of_range, False))
    
    # 测试案例5: 到达站不同
    case5_different_arrival = {
        "thursday": {
            "bj2qf": {
                "train number": "G385",
                "departure station": "北京南",
                "arrival station": "曲阜东", 
                "departure time": "18:44",
                "arrival time": "21:26"
            },
            "sh2qf": {
                "train number": "G162",
                "departure station": "上海虹桥",
                "arrival station": "曲阜南",  # 不同的到达站
                "departure time": "17:46",
                "arrival time": "21:31"
            }
        },
        "sunday": {
            "qf2bj": {
                "train number": "G128",
                "departure station": "曲阜东",
                "arrival station": "北京南",
                "departure time": "15:03", 
                "arrival time": "17:22"
            },
            "qf2sh": {
                "train number": "G1227",
                "departure station": "曲阜南",  # 不同的出发站
                "arrival station": "上海虹桥",
                "departure time": "15:01",
                "arrival time": "18:48"
            }
        }
    }
    test_cases.append(("到达站不同", case5_different_arrival, False))
    
    # 测试案例6: 时间差超过30分钟
    case6_time_diff_too_large = {
        "thursday": {
            "bj2qf": {
                "train number": "G159",
                "departure station": "北京南",
                "arrival station": "曲阜东",
                "departure time": "17:19",
                "arrival time": "19:36"
            },
            "sh2qf": {
                "train number": "G162",
                "departure station": "上海虹桥",
                "arrival station": "曲阜东", 
                "departure time": "17:46",
                "arrival time": "21:31"  # 时间差 > 30分钟
            }
        },
        "sunday": {
            "qf2bj": {
                "train number": "G128",
                "departure station": "曲阜东",
                "arrival station": "北京南",
                "departure time": "15:03",
                "arrival time": "17:22"
            },
            "qf2sh": {
                "train number": "G1227",
                "departure station": "曲阜东",
                "arrival station": "上海虹桥",
                "departure time": "15:01",
                "arrival time": "18:48"
            }
        }
    }
    test_cases.append(("时间差超过30分钟", case6_time_diff_too_large, False))
    
    # 测试案例7: 周四没有合适车次
    case7_thursday_null = {
        "thursday": None,
        "sunday": {
            "qf2bj": {
                "train number": "G128",
                "departure station": "曲阜东",
                "arrival station": "北京南",
                "departure time": "15:03",
                "arrival time": "17:22"
            },
            "qf2sh": {
                "train number": "G1227",
                "departure station": "曲阜东",
                "arrival station": "上海虹桥",
                "departure time": "15:01",
                "arrival time": "18:48"
            }
        }
    }
    test_cases.append(("周四无合适车次", case7_thursday_null, True))
    
    # 测试案例8: 周日没有合适车次  
    case8_sunday_null = {
        "thursday": {
            "bj2qf": {
                "train number": "G385", 
                "departure station": "北京南",
                "arrival station": "曲阜东",
                "departure time": "18:44",
                "arrival time": "21:26"
            },
            "sh2qf": {
                "train number": "G162",
                "departure station": "上海虹桥",
                "arrival station": "曲阜东",
                "departure time": "17:46",
                "arrival time": "21:31"
            }
        },
        "sunday": None
    }
    test_cases.append(("周日无合适车次", case8_sunday_null, True))
    
    return test_cases


def run_tests():
    """运行所有测试案例"""
    test_cases = create_test_data()
    
    print("开始测试 train-ticket-plan evaluation 逻辑...")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for case_name, test_data, expected_result in test_cases:
        print(f"\n测试案例: {case_name}")
        print("-" * 40)
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(test_data, tmp_file, ensure_ascii=False, indent=2)
            tmp_path = tmp_file.name
        
        try:
            # 运行primary_check测试
            result, _ = primary_check(tmp_path)
            
            print(f"期望结果: {expected_result}")
            print(f"实际结果: {result}")
            
            if result == expected_result:
                print("✅ 测试通过")
                passed += 1
            else:
                print("❌ 测试失败")
                failed += 1
                
        except Exception as e:
            print(f"❌ 测试出错: {e}")
            failed += 1
            
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    print("\n" + "=" * 60)
    print(f"测试总结: 通过 {passed} 个，失败 {failed} 个")
    print(f"总测试数: {passed + failed}")
    
    if failed == 0:
        print("🎉 所有测试都通过了！")
        return True
    else:
        print(f"⚠️  有 {failed} 个测试失败")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)