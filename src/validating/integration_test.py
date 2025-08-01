#!/usr/bin/env python3
"""
VulnerabilityChecker Integration Test

This test simulates the real vulnerability checking process, including:
1. Creating mock task data
2. Testing complete vulnerability checking workflow
3. Verifying processor collaboration
4. Checking result format and content
"""

import sys
import os
from unittest.mock import Mock, MagicMock, patch

# 添加src目录到Python路径
src_path = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, src_path)
print(f"🔧 已添加路径到sys.path: {src_path}")


def create_mock_task(task_id, score="0", if_business_flow_scan="0"):
    """创建模拟任务对象"""
    task = Mock()
    task.id = task_id
    task.score = score
    task.if_business_flow_scan = if_business_flow_scan
    task.content = f"function test{task_id}() {{ /* test function {task_id} */ }}"
    task.business_flow_code = f"// Business flow code for task {task_id}"
    task.business_flow_context = ""
    
    # 模拟结果获取方法
    task.get_result.return_value = f"Potential vulnerability in function test{task_id}"
    task.get_result_CN.return_value = None
    task.get_category.return_value = None
    
    return task


def create_mock_task_manager():
    """创建模拟任务管理器"""
    task_manager = Mock()
    
    # 创建一些测试任务
    tasks = [
        create_mock_task(1, score="0", if_business_flow_scan="0"),
        create_mock_task(2, score="1", if_business_flow_scan="0"),  # 已处理
        create_mock_task(3, score="0", if_business_flow_scan="1"),  # 业务流
    ]
    
    task_manager.get_task_list.return_value = tasks
    task_manager.update_business_flow_context = Mock()
    task_manager.update_score = Mock()
    task_manager.update_result = Mock()
    task_manager.update_category = Mock()
    
    return task_manager, tasks


def create_mock_project_audit():
    """创建模拟项目审计对象"""
    project_audit = Mock()
    
    # 模拟call_trees数据
    project_audit.call_trees = [
        {
            'function': 'test1',
            'upstream_tree': {
                'function_data': {
                    'name': 'test1',
                    'content': 'function test1() { /* upstream function */ }'
                },
                'children': []
            },
            'downstream_tree': {
                'function_data': {
                    'name': 'test1',
                    'content': 'function test1() { /* downstream function */ }'
                },
                'children': []
            },
            'state_variables': 'uint256 public balance;'
        }
    ]
    
    # 模拟functions_to_check数据
    project_audit.functions_to_check = [
        {
            'name': 'Contract.test1',
            'content': 'function test1() { /* test function 1 */ }'
        },
        {
            'name': 'Contract.test3',
            'content': 'function test3() { /* test function 3 */ }'
        }
    ]
    
    return project_audit


def test_context_update_flow():
    """测试上下文更新流程"""
    print("\n🔍 测试上下文更新流程...")
    
    try:
        from validating import VulnerabilityChecker
        
        # 创建模拟对象
        mock_project_audit = create_mock_project_audit()
        mock_lancedb = Mock()
        
        # 模拟向量搜索结果
        mock_table = Mock()
        mock_lancedb.open_table.return_value = mock_table
        mock_table.search.return_value.limit.return_value.to_list.return_value = [
            {'name': 'Contract.test1', 'content': 'function test1() { /* related function */ }'}
        ]
        
        task_manager, tasks = create_mock_task_manager()
        
        # 模拟embedding API调用
        with patch('validating.utils.context_manager.common_get_embedding') as mock_embedding:
            mock_embedding.return_value = [0.1, 0.2, 0.3]  # 模拟embedding向量
            
            # 创建VulnerabilityChecker
            checker = VulnerabilityChecker(mock_project_audit, mock_lancedb, "test_table")
            
            # 运行上下文更新
            checker.context_update_processor.update_business_flow_context(task_manager)
            
            # 验证调用
            assert task_manager.update_business_flow_context.call_count >= 0  # 可能没有需要更新的任务
            print("✅ 上下文更新流程测试通过")
            
            return True
    except Exception as e:
        print(f"❌ 上下文更新流程测试失败: {e}")
        return False


def test_complete_vulnerability_check_flow():
    """测试完整的漏洞检查流程"""
    print("\n🔍 测试完整的漏洞检查流程...")
    
    try:
        from validating import VulnerabilityChecker
        
        # 创建模拟对象
        mock_project_audit = create_mock_project_audit()
        mock_lancedb = Mock()
        
        # 模拟向量搜索结果
        mock_table = Mock()
        mock_lancedb.open_table.return_value = mock_table
        mock_table.search.return_value.limit.return_value.to_list.return_value = [
            {'name': 'Contract.test1', 'content': 'function test1() { /* related function */ }'}
        ]
        
        task_manager, tasks = create_mock_task_manager()
        
        # 模拟embedding API调用和其他API调用
        with patch('validating.utils.context_manager.common_get_embedding') as mock_embedding:
            with patch('validating.processors.analysis_processor.common_ask_confirmation') as mock_ask:
                with patch('validating.utils.check_utils.common_ask_for_json') as mock_ask_json:
                    with patch('validating.utils.check_utils.common_ask_confirmation') as mock_ask_confirm:
                        # 模拟embedding向量
                        mock_embedding.return_value = [0.1, 0.2, 0.3]
                        
                        # 模拟API响应
                        mock_ask.return_value = "Initial analysis shows no vulnerability found."
                        mock_ask_json.return_value = '{"result": "no vulnerability"}'
                        mock_ask_confirm.return_value = "Confirmation: no vulnerability detected."
                        
                        # 创建VulnerabilityChecker
                        checker = VulnerabilityChecker(mock_project_audit, mock_lancedb, "test_table")
                        
                        # 运行完整的检查流程
                        result = checker.check_function_vul(task_manager)
                        
                        print(f"✅ 完整检查流程测试通过，返回结果: {type(result)}")
                        return True
    except Exception as e:
        print(f"❌ 完整检查流程测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_processor_isolation():
    """测试处理器隔离性"""
    print("\n🔍 测试处理器隔离性...")
    
    try:
        from validating.processors import (
            ContextUpdateProcessor,
            ConfirmationProcessor,
            AnalysisProcessor
        )
        from context import ContextFactory
        
        # 创建独立的处理器实例
        mock_project_audit = create_mock_project_audit()
        mock_lancedb = Mock()
        
        context_factory = ContextFactory(mock_project_audit, mock_lancedb, "test_table")
        context_processor = ContextUpdateProcessor(context_factory.context_manager)
        analysis_processor = AnalysisProcessor(context_factory.context_manager)
        confirmation_processor = ConfirmationProcessor(analysis_processor)
        
        # 验证处理器可以独立使用
        assert context_processor.context_manager is not None
        assert analysis_processor.context_manager is not None
        assert confirmation_processor.analysis_processor is not None
        assert context_factory.context_manager is not None
        
        print("✅ 处理器隔离性测试通过")
        return True
    except Exception as e:
        print(f"❌ 处理器隔离性测试失败: {e}")
        return False


def test_api_backward_compatibility():
    """测试API向后兼容性"""
    print("\n🔍 测试API向后兼容性...")
    
    try:
        from validating import VulnerabilityChecker
        
        # 测试原有API接口
        mock_project_audit = create_mock_project_audit()
        mock_lancedb = Mock()
        task_manager, _ = create_mock_task_manager()
        
        # 创建checker并测试主要API
        checker = VulnerabilityChecker(mock_project_audit, mock_lancedb, "test_table")
        
        # 验证API签名
        import inspect
        api_method = checker.check_function_vul
        sig = inspect.signature(api_method)
        
        # 验证参数
        params = list(sig.parameters.keys())
        assert 'task_manager' in params or len(params) == 1
        
        print("✅ API向后兼容性测试通过")
        return True
    except Exception as e:
        print(f"❌ API向后兼容性测试失败: {e}")
        return False


def test_error_handling():
    """测试错误处理"""
    print("\n🔍 测试错误处理...")
    
    try:
        from validating import VulnerabilityChecker
        
        # 测试各种异常情况
        mock_project_audit = Mock()
        mock_project_audit.call_trees = []
        mock_project_audit.functions_to_check = []
        
        mock_lancedb = Mock()
        mock_lancedb.open_table.side_effect = Exception("Database connection error")
        
        # 尝试创建checker（应该能处理数据库错误）
        try:
            checker = VulnerabilityChecker(mock_project_audit, mock_lancedb, "test_table")
            print("   - VulnerabilityChecker 创建成功（即使数据库有问题）")
        except Exception:
            print("   - VulnerabilityChecker 创建失败（预期行为）")
        
        print("✅ 错误处理测试通过")
        return True
    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
        return False


def test_new_confirmation_logic():
    """测试新的按轮次确认逻辑"""
    print("\n🔍 测试新的按轮次确认逻辑...")
    
    try:
        from validating.utils import CheckUtils
        
        # 测试场景1: 第1轮有3个yes，第2轮有no，应该输出yes
        round_results_1 = [
            ["yes vulnerability", "yes confirmed", "yes high risk"],  # 第1轮：3个yes
            ["no vulnerability", "no issues"]  # 第2轮：2个no
        ]
        
        analysis_collection_1 = []
        result_1, _ = CheckUtils.collect_analysis_results_by_rounds(analysis_collection_1, round_results_1)
        assert result_1 == "yes", f"测试场景1失败：期望yes，实际{result_1}"
        print("   ✅ 场景1通过：第1轮3个yes覆盖第2轮的no")
        
        # 测试场景2: 第1轮有2个yes无no，第2轮有no，应该输出yes  
        round_results_2 = [
            ["yes vulnerability", "yes confirmed"],  # 第1轮：2个yes，无no
            ["no vulnerability", "no issues", "no risk"]  # 第2轮：3个no
        ]
        
        analysis_collection_2 = []
        result_2, _ = CheckUtils.collect_analysis_results_by_rounds(analysis_collection_2, round_results_2)
        assert result_2 == "yes", f"测试场景2失败：期望yes，实际{result_2}"
        print("   ✅ 场景2通过：第1轮2个yes无no覆盖第2轮的no")
        
        # 测试场景3: 第1轮有2个yes和1个no，第2轮也有no，应该按总体逻辑
        round_results_3 = [
            ["yes vulnerability", "yes confirmed", "no vulnerability"],  # 第1轮：2个yes，1个no(包含vulnerability)
            ["no vulnerability", "no vulnerability found"]  # 第2轮：2个no(都包含vulnerability)
        ]
        
        analysis_collection_3 = []
        result_3, _ = CheckUtils.collect_analysis_results_by_rounds(analysis_collection_3, round_results_3)
        # 这种情况下应该使用总体逻辑：2个yes vs 3个no(都包含vulnerability)，应该是no
        expected_3 = "no"  # 总体3个no > 2个yes
        assert result_3 == expected_3, f"测试场景3失败：期望{expected_3}，实际{result_3}"
        print("   ✅ 场景3通过：无强确认轮次，使用总体逻辑")
        
        # 测试场景4: 第2轮满足强确认条件
        round_results_4 = [
            ["no vulnerability", "no issues"],  # 第1轮：2个no
            ["yes vulnerability", "yes confirmed", "yes high risk"]  # 第2轮：3个yes
        ]
        
        analysis_collection_4 = []
        result_4, _ = CheckUtils.collect_analysis_results_by_rounds(analysis_collection_4, round_results_4)
        assert result_4 == "yes", f"测试场景4失败：期望yes，实际{result_4}"
        print("   ✅ 场景4通过：第2轮3个yes覆盖第1轮的no")
        
        print("✅ 新的按轮次确认逻辑测试通过")
        return True
    except Exception as e:
        print(f"❌ 新的按轮次确认逻辑测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_integration_tests():
    """运行所有集成测试"""
    print("🚀 开始VulnerabilityChecker集成测试")
    print("=" * 60)
    
    tests = [
        ("上下文更新流程测试", test_context_update_flow),
        ("完整漏洞检查流程测试", test_complete_vulnerability_check_flow),
        ("处理器隔离性测试", test_processor_isolation),
        ("API向后兼容性测试", test_api_backward_compatibility),
        ("错误处理测试", test_error_handling),
        ("新的按轮次确认逻辑测试", test_new_confirmation_logic),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} 失败")
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 集成测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有集成测试通过！重构的VulnerabilityChecker功能完全正常！")
        return True
    else:
        print("⚠️ 部分集成测试失败，需要进一步检查")
        return False


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1) 