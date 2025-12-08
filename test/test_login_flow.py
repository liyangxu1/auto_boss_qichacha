#!/usr/bin/env python3
"""
测试Boss直聘客户端登录流程
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.boss_zhipin import BossZhipinClient


def test_login_flow():
    """
    测试登录流程：先加载登录信息，没有则扫码登录
    """
    print("=== Boss直聘登录流程测试 ===")
    
    # 创建客户端实例
    client = BossZhipinClient(headless=False)
    
    try:
        # 测试登录流程
        login_success = client.login()
        
        if login_success:
            print("✅ 登录成功")
            
            # 登录成功后，让用户有时间进行操作
            print("\n请在浏览器中进行您需要的操作。")
            print("操作完成后，请按回车键继续...")
            input()
            
            # 如果需要，可以在这里添加更多测试代码
            # 例如：检查登录状态、获取用户信息等
            
        else:
            print("❌ 登录失败")
            # 登录失败后，让用户有时间查看浏览器中的情况
            print("\n您可以在浏览器中查看登录失败的原因。")
            print("查看完成后，请按回车键继续...")
            input()
            return False
            
    finally:
        # 确保资源被释放
        client.close()
        print("资源已释放")
    
    return login_success


if __name__ == "__main__":
    test_login_flow()
