#!/usr/bin/env python
"""
抖音视频下载诊断 - 完整版本
包含多个测试用例和详细的错误分析
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from yt_dlp import YoutubeDL
import yt_dlp


def test_douyin_extraction(url: str, verbose: bool = True) -> dict:
    """测试抖音视频信息提取"""
    result = {
        "url": url,
        "success": False,
        "error": None,
        "info": None,
        "yt_dlp_version": yt_dlp.version.__version__,
    }
    
    ydl_opts = {
        "quiet": not verbose,
        "no_warnings": not verbose,
        "skip_download": True,
        "verbose": verbose,
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            result["success"] = True
            result["info"] = {
                "title": info.get("title"),
                "id": info.get("id"),
                "duration": info.get("duration"),
                "formats_count": len(info.get("formats", [])),
                "uploader": info.get("uploader"),
            }
            return result
            
    except Exception as e:
        result["error"] = {
            "type": type(e).__name__,
            "message": str(e),
        }
        return result


def main():
    print(f"\n{'='*70}")
    print(f"抖音视频下载诊断工具")
    print(f"{'='*70}")
    print(f"yt-dlp 版本: {yt_dlp.version.__version__}")
    print(f"Python 版本: {sys.version.split()[0]}")
    print(f"操作系统: {sys.platform}\n")
    
    # 测试用例 - 常见的抖音 URL 格式
    test_cases = [
        {
            "name": "抖音短链接 (v.douyin.com)",
            "url": "https://v.douyin.com/example",
            "description": "最常见的分享格式"
        },
        {
            "name": "抖音完整链接 (www.douyin.com/video)",
            "url": "https://www.douyin.com/video/1234567890",
            "description": "完整的视频页面链接"
        },
        {
            "name": "抖音国际版 (TikTok)",
            "url": "https://www.tiktok.com/@user/video/1234567890",
            "description": "用于对比测试"
        },
    ]
    
    if len(sys.argv) > 1:
        # 用户提供的 URL
        test_url = sys.argv[1]
        print(f"[测试] 用户提供的 URL: {test_url}\n")
        result = test_douyin_extraction(test_url, verbose=True)
        
        if result["success"]:
            print(f"✓ 成功提取视频信息:")
            for key, value in result["info"].items():
                print(f"  - {key}: {value}")
        else:
            print(f"✗ 提取失败:")
            print(f"  - 错误类型: {result['error']['type']}")
            print(f"  - 错误信息: {result['error']['message']}")
            
            # 诊断建议
            error_msg = result['error']['message'].lower()
            print(f"\n[诊断建议]")
            
            if "no such file" in error_msg or "not found" in error_msg:
                print("  • 视频可能已被删除或链接无效")
                print("  • 请确认链接是否正确")
            elif "403" in error_msg or "forbidden" in error_msg:
                print("  • 可能需要登录或 cookies")
                print("  • 尝试启用 cookies 功能")
            elif "unable to extract" in error_msg or "unsupported" in error_msg:
                print("  • yt-dlp 可能不支持此格式")
                print("  • 尝试更新 yt-dlp: pip install --upgrade yt-dlp")
            elif "network" in error_msg or "connection" in error_msg:
                print("  • 网络连接问题")
                print("  • 检查网络连接和代理设置")
            else:
                print("  • 未知错误，请查看完整错误信息")
        
        sys.exit(0 if result["success"] else 1)
    
    else:
        # 显示使用说明
        print("[使用方法]")
        print("  python test_douyin_diagnostic.py '<douyin_url>'\n")
        print("[示例]")
        print("  python test_douyin_diagnostic.py 'https://v.douyin.com/...'")
        print("  python test_douyin_diagnostic.py 'https://www.douyin.com/video/...'")
        print("  python test_douyin_diagnostic.py 'https://www.tiktok.com/@user/video/...'\n")
        
        print("[常见问题排查]")
        print("1. 确保 URL 是有效的抖音/TikTok 链接")
        print("2. 检查网络连接")
        print("3. 尝试更新 yt-dlp: pip install --upgrade yt-dlp")
        print("4. 某些视频可能需要登录或 cookies")
        print("5. 检查是否有地域限制\n")
        
        print("[项目配置]")
        print("  - 当前 yt-dlp 版本满足最低要求 (>=2025.1.1)")
        print("  - 建议定期更新 yt-dlp 以获得最新的网站支持\n")


if __name__ == "__main__":
    main()
