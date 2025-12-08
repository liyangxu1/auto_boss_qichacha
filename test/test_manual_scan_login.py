#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试手动扫码登录功能
"""

import os
import sys
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.boss_zhipin import BossZhipinClient

def test_manual_scan_login():
    """测试手动扫码登录功能"""
    print("=== Boss直聘手动扫码登录测试 ===")
    
    # 创建Boss直聘客户端实例（非无头模式）
    client = BossZhipinClient(headless=False)
    
    try:
        # 打开登录页面
        print("正在打开Boss直聘登录页面...")
        success = client.open_login_page()
        
        if not success:
            print("❌ 打开登录页面失败")
            return
        
        print("\n✅ 登录页面已打开，请使用Boss直聘APP扫码登录")
        print("二维码图片已保存到 data/img/qrcode.png")
        print("\n提示：扫码完成后，系统会自动检测登录状态")
        print("按 Ctrl+C 可以中断测试")
        
        # 循环检查登录状态，直到用户完成扫码
        login_success = False
        max_checks = 120  # 最多检查20分钟（每分钟检查一次）
        
        for i in range(max_checks):
            try:
                time.sleep(5)  # 每5秒检查一次
                
                # 检查登录状态
                if client.check_login_status():
                    login_success = True
                    break
                
                # 每10次检查（50秒）提示一次
                if (i + 1) % 10 == 0:
                    print(f"\n⏳ 等待登录中... ({(i + 1) * 5}秒)")
                    print("请确保已经使用Boss直聘APP扫码并确认登录")
                    
            except KeyboardInterrupt:
                print("\n\n❌ 测试已中断")
                return
            except Exception as e:
                print(f"\n⚠️  检查登录状态时发生错误: {e}")
                continue
        
        if login_success:
            print("\n🎉 登录成功！")
            
            # 保存登录信息
            print("正在保存登录信息...")
            if client.save_login_info():
                print("✅ 登录信息已保存到 data/login_info.json")
            else:
                print("❌ 保存登录信息失败")
                
            # 停留3秒让用户查看
            time.sleep(3)
            
        else:
            print(f"\n❌ 登录超时（已等待{max_checks * 5}秒）")
            print("请重新运行测试或检查网络连接")
            
    finally:
        print("\n正在关闭浏览器...")
        client.close()
        print("✅ 浏览器已关闭")
        print("\n=== 测试结束 ===")

if __name__ == "__main__":
    test_manual_scan_login()
