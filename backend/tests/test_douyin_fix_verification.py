#!/usr/bin/env python
"""
抖音视频下载修复验证脚本
验证改进后的 URL 验证和错误处理
"""
import sys
import os
from pathlib import Path

# 设置 PYTHONPATH
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

from backend.app.main import _parse_urls, _human_error
from yt_dlp.utils import DownloadError


def test_url_validation():
    """测试 URL 验证逻辑"""
    print("\n" + "="*70)
    print("测试 1: URL 验证逻辑")
    print("="*70)
    
    test_cases = [
        # (输入, 预期结果, 说明)
        ("https://v.douyin.com/xxxxx/", True, "抖音短链接 - 应该接受"),
        ("https://www.douyin.com/video/1234567890", True, "抖音视频链接 - 应该接受"),
        ("https://www.douyin.com/v/1234567890", True, "抖音 /v/ 格式 - 应该接受"),
        ("https://www.douyin.com/user/MS4wLjABAAAA...", False, "抖音用户主页 - 应该拒绝"),
        ("https://www.tiktok.com/@user/video/1234567890", True, "TikTok 视频链接 - 应该接受"),
        ("https://www.youtube.com/watch?v=xxxxx", True, "YouTube 链接 - 应该接受"),
        ("https://www.bilibili.com/video/BV1xxx", True, "B站链接 - 应该接受"),
    ]
    
    passed = 0
    failed = 0
    
    for url, should_accept, description in test_cases:
        result = _parse_urls(url)
        is_accepted = len(result) > 0
        
        if is_accepted == should_accept:
            status = "✓ PASS"
            passed += 1
        else:
            status = "✗ FAIL"
            failed += 1
        
        print(f"\n{status}: {description}")
        print(f"  URL: {url}")
        print(f"  预期: {'接受' if should_accept else '拒绝'}")
        print(f"  实际: {'接受' if is_accepted else '拒绝'}")
    
    print(f"\n{'-'*70}")
    print(f"结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_error_messages():
    """测试错误消息改进"""
    print("\n" + "="*70)
    print("测试 2: 错误消息改进")
    print("="*70)
    
    test_cases = [
        (
            DownloadError("ERROR: Unsupported URL: https://www.douyin.com/user/xxxxx"),
            "不支持的抖音链接格式",
            "抖音 URL 错误 - 应该显示友好提示"
        ),
        (
            DownloadError("ERROR: Unsupported URL: https://example.com/page"),
            "ERROR: Unsupported URL",
            "其他 URL 错误 - 应该显示原始错误"
        ),
    ]
    
    passed = 0
    failed = 0
    
    for error, expected_substring, description in test_cases:
        result = _human_error(error)
        
        if expected_substring in result:
            status = "✓ PASS"
            passed += 1
        else:
            status = "✗ FAIL"
            failed += 1
        
        print(f"\n{status}: {description}")
        print(f"  错误: {str(error)[:60]}...")
        print(f"  预期包含: {expected_substring}")
        print(f"  实际返回: {result[:80]}...")
    
    print(f"\n{'-'*70}")
    print(f"结果: {passed} 通过, {failed} 失败")
    return failed == 0


def main():
    print("\n" + "="*70)
    print("抖音视频下载修复验证")
    print("="*70)
    
    test1_passed = test_url_validation()
    test2_passed = test_error_messages()
    
    print("\n" + "="*70)
    print("总体结果")
    print("="*70)
    
    if test1_passed and test2_passed:
        print("✓ 所有测试通过！修复方案有效。")
        return 0
    else:
        print("✗ 部分测试失败。请检查修复方案。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
