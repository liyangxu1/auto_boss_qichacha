#!/usr/bin/env python3
"""
Boss直聘模块测试脚本

功能：
1. 测试Boss直聘自动登录功能
2. 测试职位搜索功能
"""

import os
import sys
import json
import argparse

# 将项目根目录添加到Python搜索路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.boss_zhipin import BossZhipinClient


def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(description='Boss直聘模块测试脚本')
    parser.add_argument('--username', help='Boss直聘用户名', required=False)
    parser.add_argument('--password', help='Boss直聘密码', required=False)
    parser.add_argument('--keyword', help='搜索关键词', default='Python开发')
    parser.add_argument('--location', help='工作地点', default='全国')
    parser.add_argument('--page', type=int, help='页码', default=1)
    args = parser.parse_args()

    try:
        # 初始化Boss直聘客户端
        client = BossZhipinClient()
        
        # 登录
        login_success = client.login(args.username, args.password)
        if not login_success:
            print("登录失败，请检查用户名和密码是否正确")
            return
        
        print("登录成功！")
        
        # 搜索职位
        print(f"\n正在搜索职位：关键词={args.keyword}, 地点={args.location}, 页码={args.page}")
        jobs = client.search_jobs(args.keyword, args.location, args.page)
        
        if jobs:
            print(f"\n搜索成功！共找到 {len(jobs)} 个职位")
            print("\n职位列表预览：")
            for i, job in enumerate(jobs[:5]):  # 只显示前5个职位
                print(f"\n{i+1}. {job['job_title']} - {job['company_name']}")
                print(f"   薪资：{job['salary']}")
                print(f"   地点：{job['work_location']}")
                print(f"   要求：{job['job_requirements']}")
                print(f"   技能：{', '.join(job['skills'])}")
                print(f"   福利：{', '.join(job['welfare'])}")
                print(f"   链接：{job['job_link']}")
            
            # 保存搜索结果
            output_file = f"boss_jobs_{args.keyword.replace(' ', '_')}_{args.page}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(jobs, f, ensure_ascii=False, indent=2)
            print(f"\n搜索结果已保存到 {output_file}")
        else:
            print("未找到职位")
            
    except Exception as e:
        print(f"测试失败：{e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭浏览器
        client.close()


if __name__ == '__main__':
    main()
