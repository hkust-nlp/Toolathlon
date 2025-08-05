#!/usr/bin/env python3
"""
严格模式evaluation测试脚本
测试严格模式的各项功能和验证逻辑
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)

from .evaluation.main import (
    STRICT_MODE_CONFIG, check_json_structure_strict, check_required_locations_strict,
    extract_agent_route, calculate_route_efficiency_strict
)

def test_strict_mode_config():
    """测试严格模式配置"""
    print("🧪 测试严格模式配置...")
    
    # 验证配置完整性
    required_keys = ["efficiency_threshold", "fallback_threshold", "min_locations_required", 
                    "max_evaluation_time", "max_api_calls", "scoring_weights"]
    
    for key in required_keys:
        assert key in STRICT_MODE_CONFIG, f"缺少配置项: {key}"
    
    # 验证阈值设置
    assert STRICT_MODE_CONFIG["efficiency_threshold"] == 1.10, "严格阈值应为1.10"
    assert STRICT_MODE_CONFIG["fallback_threshold"] == 1.15, "容错阈值应为1.15"
    assert STRICT_MODE_CONFIG["min_locations_required"] == 5, "必须包含5个地点"
    
    print("✅ 严格模式配置测试通过")

def test_json_structure_validation():
    """测试JSON结构验证的严格模式"""
    print("\n🧪 测试JSON结构验证...")
    
    # 测试1: 完整有效的JSON
    valid_json = [
        {
            "destinations": [{
                "order": 1,
                "name": "Penn Museum",
                "description": "测试描述",  # description是可选的
                "location": "Penn Museum, 3260 South St, Philadelphia, PA 19104"
            }],
            "route_plan": [{
                "from": "Penn Bookstore",
                "to": "Penn Museum",
                "distance": "0.4 mi",
                "estimated_time": "8 minutes"
                # directions 被移除，不再强制要求
            }],
            "total_distance": "0.4 mi",
            "total_time": "8 minutes"
        }
    ]
    
    result, details = check_json_structure_strict(valid_json)
    assert result == True, "有效JSON应该通过验证"
    print("✅ 有效JSON验证通过")
    
    # 测试2: 缺少关键字段
    invalid_json = [
        {
            "destinations": [{
                "order": 1,
                "name": "Penn Museum"
                # 缺少location字段
            }],
            "route_plan": [],
            "total_distance": "0.4 mi",
            "total_time": "8 minutes"
        }
    ]
    
    result, details = check_json_structure_strict(invalid_json)
    assert result == False, "缺少关键字段的JSON应该失败"
    print("✅ 无效JSON验证正确")
    
    # 测试3: 空的route_plan应该被允许
    empty_route_json = [
        {
            "destinations": [{
                "order": 1,
                "name": "Penn Museum",
                "location": "Penn Museum, 3260 South St, Philadelphia, PA 19104"
            }],
            "route_plan": [],  # 空的route_plan
            "total_distance": "0.4 mi",
            "total_time": "8 minutes"
        }
    ]
    
    result, details = check_json_structure_strict(empty_route_json)
    assert result == True, "空的route_plan应该被允许"
    print("✅ 空route_plan验证通过")

def test_location_matching():
    """测试地点匹配的严格模式"""
    print("\n🧪 测试地点匹配...")
    
    # 测试1: 完整地点覆盖
    complete_json = [
        {"destinations": [{"order": 1, "name": "University of Pennsylvania School of Engineering", "location": "220 S 33rd St"}]},
        {"destinations": [{"order": 2, "name": "Penn Museum", "location": "3260 South St"}]},
        {"destinations": [{"order": 3, "name": "Benjamin Franklin Statue", "location": "University of Pennsylvania"}]},
        {"destinations": [{"order": 4, "name": "Fisher Fine Arts Library", "location": "220 S 34th St"}]},
        {"destinations": [{"order": 5, "name": "College Hall", "location": "Philadelphia, PA 19104"}]}
    ]
    
    result, details = check_required_locations_strict(complete_json)
    assert result == True, "完整地点覆盖应该通过"
    assert len(details["found_locations"]) == 5, "应该找到5个地点"
    print("✅ 完整地点覆盖验证通过")
    
    # 测试2: 缺少地点
    incomplete_json = [
        {"destinations": [{"order": 1, "name": "Penn Museum", "location": "3260 South St"}]},
        {"destinations": [{"order": 2, "name": "Franklin Statue", "location": "University of Pennsylvania"}]}
    ]
    
    result, details = check_required_locations_strict(incomplete_json)
    assert result == False, "缺少地点应该失败"
    assert len(details["missing_locations"]) > 0, "应该有缺少的地点"
    print("✅ 缺少地点验证正确")
    
    # 测试3: 别名匹配
    alias_json = [
        {"destinations": [{"order": 1, "name": "ENIAC Museum", "location": "Engineering School"}]},  # 应该匹配Engineering
        {"destinations": [{"order": 2, "name": "Archaeological Museum", "location": "3260 South St"}]},  # 应该匹配Penn Museum
        {"destinations": [{"order": 3, "name": "Franklin", "location": "Campus"}]},  # 应该匹配Franklin Statue
        {"destinations": [{"order": 4, "name": "Library", "location": "Art building"}]},  # 应该匹配Fisher Library
        {"destinations": [{"order": 5, "name": "Main Hall", "location": "College"}]}  # 应该匹配College Hall
    ]
    
    result, details = check_required_locations_strict(alias_json)
    # 别名匹配可能部分成功，取决于具体的匹配算法
    print(f"✅ 别名匹配测试完成，找到{len(details['found_locations'])}个地点")

def test_route_extraction():
    """测试路线提取"""
    print("\n🧪 测试路线提取...")
    
    # 使用实际录制数据的格式
    test_json = [
        {
            "destinations": [{
                "order": 1,
                "name": "Benjamin Franklin Statue & College Hall",
                "location": "College Hall, University of Pennsylvania"
            }]
        },
        {
            "destinations": [{
                "order": 2,
                "name": "Fisher Fine Arts Library",
                "location": "220 S 34th St"
            }]
        },
        {
            "destinations": [{
                "order": 3,
                "name": "ENIAC Exhibit (School of Engineering)",
                "location": "220 S 33rd St"
            }]
        },
        {
            "destinations": [{
                "order": 4,
                "name": "Penn Museum",  
                "location": "3260 South St"
            }]
        }
    ]
    
    route = extract_agent_route(test_json)
    
    assert len(route) >= 4, "路线应该包含至少4个地点（包括起点）"
    assert route[0] == "Penn Bookstore", "起点应该是Penn Bookstore"
    
    print(f"✅ 路线提取成功: {' -> '.join(route)}")
    print(f"✅ 路线长度: {len(route)}个地点")

def create_mock_distance_matrix():
    """创建mock距离矩阵用于测试"""
    locations = [
        "Penn Bookstore",
        "University of Pennsylvania School of Engineering and Applied Science",
        "Penn Museum",
        "Benjamin Franklin Statue", 
        "Fisher Fine Arts Library",
        "College Hall"
    ]
    
    # 简化的距离数据（秒为单位）
    base_distances = {
        ("Penn Bookstore", "Benjamin Franklin Statue"): (300, "0.1 mi"),
        ("Penn Bookstore", "Fisher Fine Arts Library"): (420, "0.2 mi"),
        ("Penn Bookstore", "University of Pennsylvania School of Engineering and Applied Science"): (480, "0.2 mi"),
        ("Penn Bookstore", "Penn Museum"): (720, "0.4 mi"),
        ("Penn Bookstore", "College Hall"): (300, "0.1 mi"),
        
        ("Benjamin Franklin Statue", "College Hall"): (60, "0.05 mi"),
        ("Benjamin Franklin Statue", "Fisher Fine Arts Library"): (180, "0.1 mi"),
        ("College Hall", "Fisher Fine Arts Library"): (120, "0.1 mi"),
        ("Fisher Fine Arts Library", "University of Pennsylvania School of Engineering and Applied Science"): (120, "0.1 mi"),
        ("University of Pennsylvania School of Engineering and Applied Science", "Penn Museum"): (360, "0.2 mi"),
    }
    
    distance_matrix = {}
    for origin in locations:
        distance_matrix[origin] = {}
        for destination in locations:
            if origin == destination:
                distance_matrix[origin][destination] = (0, "0 m")
            else:
                key1 = (origin, destination)
                key2 = (destination, origin)
                if key1 in base_distances:
                    distance_matrix[origin][destination] = base_distances[key1]
                elif key2 in base_distances:
                    distance_matrix[origin][destination] = base_distances[key2]
                else:
                    distance_matrix[origin][destination] = (600, "0.3 mi")  # 默认值
    
    return distance_matrix

def test_efficiency_calculation():
    """测试效率计算"""
    print("\n🧪 测试效率计算...")
    
    distance_matrix = create_mock_distance_matrix()
    
    # 测试相同路线
    same_route = ["Penn Bookstore", "Benjamin Franklin Statue", "College Hall", "Fisher Fine Arts Library"]
    efficiency_result = calculate_route_efficiency_strict(same_route, same_route, distance_matrix)
    
    assert abs(efficiency_result["efficiency"] - 1.0) < 0.001, "相同路线效率应该为1.0"
    print("✅ 相同路线效率计算正确")
    
    # 测试不同路线
    optimal_route = ["Penn Bookstore", "Benjamin Franklin Statue", "College Hall", "Fisher Fine Arts Library"]
    suboptimal_route = ["Penn Bookstore", "Penn Museum", "Fisher Fine Arts Library", "College Hall"]
    
    efficiency_result = calculate_route_efficiency_strict(suboptimal_route, optimal_route, distance_matrix)
    
    assert efficiency_result["efficiency"] > 1.0, "次优路线效率应该大于1.0"
    assert "agent_time" in efficiency_result, "应该包含agent时间"
    assert "optimal_time" in efficiency_result, "应该包含最优时间"
    
    print(f"✅ 不同路线效率计算正确: {efficiency_result['efficiency']:.3f}")

def test_strict_mode_thresholds():
    """测试严格模式阈值判定"""
    print("\n🧪 测试严格模式阈值判定...")
    
    # 测试不同效率值的判定
    test_cases = [
        (1.05, "应该在严格阈值内通过"),
        (1.12, "应该在容错阈值内通过"),
        (1.18, "应该超出容错阈值失败"),
        (1.50, "应该明显失败")
    ]
    
    for efficiency, description in test_cases:
        if efficiency <= STRICT_MODE_CONFIG["efficiency_threshold"]:
            level = "优秀"
        elif efficiency <= STRICT_MODE_CONFIG["fallback_threshold"]:
            level = "通过"
        else:
            level = "失败"
        
        print(f"   效率 {efficiency:.2f}: {level} - {description}")
    
    print("✅ 阈值判定逻辑验证完成")

async def test_integration():
    """集成测试"""
    print("\n🧪 集成测试...")
    
    # 创建测试用的JSON文件
    test_json_data = [
        {
            "destinations": [{
                "order": 1,
                "name": "Benjamin Franklin Statue",
                "description": "The iconic statue of Benjamin Franklin",
                "location": "College Hall, University of Pennsylvania, Philadelphia, PA 19104"
            }],
            "route_plan": [{
                "from": "Penn Bookstore",
                "to": "Benjamin Franklin Statue", 
                "distance": "0.1 mi",
                "estimated_time": "5 minutes"
            }],
            "total_distance": "0.1 mi",
            "total_time": "5 minutes"
        },
        {
            "destinations": [{
                "order": 2,
                "name": "Fisher Fine Arts Library",
                "description": "Victorian Gothic building designed by Frank Furness",
                "location": "220 S 34th St, Philadelphia, PA 19104"
            }],
            "route_plan": [{
                "from": "Benjamin Franklin Statue",
                "to": "Fisher Fine Arts Library",
                "distance": "0.1 mi", 
                "estimated_time": "3 minutes"
            }],
            "total_distance": "0.1 mi",
            "total_time": "3 minutes"
        },
        {
            "destinations": [{
                "order": 3,
                "name": "ENIAC Exhibit",
                "description": "Birthplace of the modern computer",
                "location": "University of Pennsylvania School of Engineering and Applied Science, 220 S 33rd St, Philadelphia, PA 19104"
            }],
            "route_plan": [{
                "from": "Fisher Fine Arts Library",
                "to": "ENIAC Exhibit",
                "distance": "0.1 mi",
                "estimated_time": "2 minutes"
            }],
            "total_distance": "0.1 mi", 
            "total_time": "2 minutes"
        },
        {
            "destinations": [{
                "order": 4,
                "name": "Penn Museum",
                "description": "Museum of Archaeology and Anthropology", 
                "location": "3260 South St, Philadelphia, PA 19104"
            }],
            "route_plan": [{
                "from": "ENIAC Exhibit",
                "to": "Penn Museum",
                "distance": "0.2 mi",
                "estimated_time": "5 minutes"
            }],
            "total_distance": "0.2 mi",
            "total_time": "5 minutes"
        },
        {
            "destinations": [{
                "order": 5,
                "name": "College Hall",
                "description": "The oldest building on campus",
                "location": "College Hall, Philadelphia, PA 19104"
            }],
            "route_plan": [{
                "from": "Penn Museum", 
                "to": "College Hall",
                "distance": "0.3 mi",
                "estimated_time": "6 minutes"
            }],
            "total_distance": "0.3 mi",
            "total_time": "6 minutes"
        }
    ]
    
    # 1. 结构验证
    structure_valid, structure_result = check_json_structure_strict(test_json_data)
    assert structure_valid, "集成测试JSON结构应该有效"
    
    # 2. 地点验证
    locations_valid, location_result = check_required_locations_strict(test_json_data)
    assert locations_valid, "集成测试地点覆盖应该完整"
    
    # 3. 路线提取
    agent_route = extract_agent_route(test_json_data)
    assert len(agent_route) == 6, "应该包含6个地点（起点+5个目的地）"
    
    print("✅ 集成测试通过")
    print(f"   - 结构验证: ✅")
    print(f"   - 地点验证: ✅ ({len(location_result['found_locations'])}/5)")
    print(f"   - 路线提取: ✅ ({len(agent_route)}个地点)")

async def main():
    """运行所有测试"""
    print("🚀 开始严格模式evaluation测试")
    print("=" * 60)
    
    try:
        # 运行各项测试
        test_strict_mode_config()
        test_json_structure_validation()
        test_location_matching()
        test_route_extraction()
        test_efficiency_calculation()
        test_strict_mode_thresholds()
        await test_integration()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试通过！严格模式evaluation准备就绪")
        print("=" * 60)
        
        # 输出严格模式的关键特性
        print("\n📋 严格模式关键特性:")
        print(f"   🎯 效率阈值: {STRICT_MODE_CONFIG['efficiency_threshold']} (优秀)")
        print(f"   ⚡ 容错阈值: {STRICT_MODE_CONFIG['fallback_threshold']} (通过)")
        print(f"   📍 必需地点: {STRICT_MODE_CONFIG['min_locations_required']}个")
        print(f"   ⏱️  最大时间: {STRICT_MODE_CONFIG['max_evaluation_time']}秒")
        print(f"   🔍 关键字段验证: location, route_plan, total_distance, total_time")
        print(f"   📝 忽略字段: description, directions (可选)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)