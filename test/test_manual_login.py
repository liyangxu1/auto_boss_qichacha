#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Boss直聘手动登录功能

此脚本用于测试修改后的手动登录功能，验证用户可以：
1. 手动完成登录操作
2. 按回车确认登录完成
3. 自动保存登录信息（Cookie）
4. 下次登录时自动加载保存的登录信息
"""

import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.boss_zhipin import BossZhipinClient

def test_manual_login():
    """
    测试手动登录功能
    """
    print("=" * 60)
    print("Boss直聘手动登录功能测试")
    print("=" * 60)
    
    try:
        # 创建BossZhipinClient实例
        client = BossZhipinClient()
        print("1. 创建BossZhipinClient实例成功")
        
        # 调用login方法（先尝试加载保存的Cookie，失败则手动登录）
        print("2. 开始登录流程...")
        success = client.login()
        
        if success:
            print("\n✅ 登录成功！")
            print("\n3. 登录状态检查:")
            print(f"   登录状态: 已登录")
            print("   登录信息已自动保存")
            
            # 模拟一些操作
            print("\n4. 模拟浏览招聘信息...")
            time.sleep(2)
            client.page.goto('https://www.zhipin.com/c101010100/?query=Python&page=1', wait_until='networkidle')
            print("   已跳转到Python招聘信息页面")
            time.sleep(3)
            
            # 关闭浏览器
            print("\n5. 关闭浏览器")
            client.close()
            print("✅ 测试完成！")
            return True
        else:
            print("\n❌ 登录失败！")
            client.close()
            return False
            
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        return False

def test_cookie_login():
    """
    测试使用保存的Cookie自动登录功能
    """
    print("\n" + "=" * 60)
    print("Boss直聘Cookie自动登录功能测试")
    print("=" * 60)
    
    try:
        # 创建BossZhipinClient实例
        client = BossZhipinClient()
        print("1. 创建BossZhipinClient实例成功")
        
        # 调用login方法（应该会自动加载保存的Cookie）
        print("2. 尝试使用保存的Cookie自动登录...")
        success = client.login()
        
        if success:
            print("\n✅ Cookie自动登录成功！")
            print("\n3. 登录状态检查:")
            print(f"   登录状态: 已登录")
            
            # 关闭浏览器
            print("\n4. 关闭浏览器")
            client.close()
            print("✅ 测试完成！")
            return True
        else:
            print("\n❌ Cookie自动登录失败！")
            client.close()
            return False
            
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        return False

if __name__ == "__main__":
    print("欢迎使用Boss直聘手动登录功能测试工具")
    print("\n测试说明：")
    print("1. 第一次运行时，将打开浏览器让您手动完成登录")
    print("2. 登录完成后按回车键，系统会自动保存登录信息")
    print("3. 第二次运行时，系统会尝试使用保存的Cookie自动登录")
    
    # 测试手动登录
    manual_login_success = test_manual_login()
    
    if manual_login_success:
        # 测试Cookie自动登录
        input("\n按回车键继续测试Cookie自动登录...")
        cookie_login_success = test_cookie_login()
    
    print("\n" + "=" * 60)
    print("测试结束")
    print("=" * 60)