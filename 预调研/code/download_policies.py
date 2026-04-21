"""
环境政策文件批量下载脚本
═══════════════════════════════════════════════════════
从中国政府官方网站下载 40 份真实环境政策 PDF 文件
（与已有 10 份合计 50 份预调研样本）

使用方法：
  cd code
  python download_policies.py

来源网站：
  - 中国政府网 (www.gov.cn)
  - 生态环境部 (www.mee.gov.cn)
  - 全国人大法律法规库 (flk.npc.gov.cn)
  - 北大法宝 (pkulaw.com)
  - 各省级政府门户

注意：
  1. 部分 URL 可能因政府网站改版而失效，脚本会自动跳过并报告
  2. 建议在中国大陆网络环境下运行，海外网络可能无法访问部分站点
  3. 如自动下载失败，可参照 政策文件清单.md 手动下载
"""

import os
import sys
import time
import urllib.request
import urllib.error
import ssl
from pathlib import Path

# ──────────────────────────────────────────────
# 40 份待下载的真实环境政策文件清单
# 编号 11—50，与已有 01—10 合计 50 份
# ──────────────────────────────────────────────

POLICY_LIST = [
    # ═══ 中央法律（全国人大/人大常委会）═══
    {
        "id": 11,
        "name": "中华人民共和国水污染防治法_2017修订",
        "year": 2017,
        "type": "法律",
        "authority": "全国人大常委会",
        "urls": [
            "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjMzYTAxNzk4NjJjOTkzNzBiZjk%3D",
            "https://www.mee.gov.cn/ywgz/fgbz/fl/201811/t20181114_673442.shtml",
        ],
        "search_keywords": "水污染防治法 2017 全文 PDF",
    },
    {
        "id": 12,
        "name": "中华人民共和国大气污染防治法_2018修正",
        "year": 2018,
        "type": "法律",
        "authority": "全国人大常委会",
        "urls": [
            "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjMzYTAxNzk4NjJjOTIzNzBiZTc%3D",
            "https://www.mee.gov.cn/ywgz/fgbz/fl/201811/t20181114_673438.shtml",
        ],
        "search_keywords": "大气污染防治法 2018修正 全文 PDF",
    },
    {
        "id": 13,
        "name": "中华人民共和国固体废物污染环境防治法_2020修订",
        "year": 2020,
        "type": "法律",
        "authority": "全国人大常委会",
        "urls": [
            "https://www.gov.cn/xinwen/2020-04/30/content_5507561.htm",
            "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3MjlkMWVmZTAxNzI5ZDUwYjVjNTAwYmY%3D",
        ],
        "search_keywords": "固体废物污染环境防治法 2020 全文 PDF",
    },
    {
        "id": 14,
        "name": "中华人民共和国噪声污染防治法_2021",
        "year": 2021,
        "type": "法律",
        "authority": "全国人大常委会",
        "urls": [
            "https://www.gov.cn/xinwen/2021-12/25/content_5664675.htm",
            "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3ZGMzMTdlNDAxN2RjODc0MTMxMTAwMTI%3D",
        ],
        "search_keywords": "噪声污染防治法 2021 全文 PDF",
    },
    {
        "id": 15,
        "name": "中华人民共和国土壤污染防治法_2018",
        "year": 2018,
        "type": "法律",
        "authority": "全国人大常委会",
        "urls": [
            "https://www.gov.cn/xinwen/2018-09/01/content_5318937.htm",
            "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE2NWY1NmQ4NDAxNjVmNzE4MDU2NjA1OWI%3D",
        ],
        "search_keywords": "土壤污染防治法 2018 全文 PDF",
    },
    {
        "id": 16,
        "name": "中华人民共和国海洋环境保护法_2023修订",
        "year": 2023,
        "type": "法律",
        "authority": "全国人大常委会",
        "urls": [
            "https://www.gov.cn/yaowen/liebiao/202310/content_6911753.htm",
            "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE4YjIzYjMxNjAxOGI1NWM3NmJkMjAwNjQ%3D",
        ],
        "search_keywords": "海洋环境保护法 2023修订 全文 PDF",
    },
    {
        "id": 17,
        "name": "中华人民共和国长江保护法_2020",
        "year": 2020,
        "type": "法律",
        "authority": "全国人大常委会",
        "urls": [
            "https://www.gov.cn/xinwen/2020-12/27/content_5573950.htm",
            "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3NjY2ZTdlMzAxNzY3ODE0NzRmMTAwMWU%3D",
        ],
        "search_keywords": "长江保护法 2020 全文 PDF",
    },
    {
        "id": 18,
        "name": "中华人民共和国黄河保护法_2022",
        "year": 2022,
        "type": "法律",
        "authority": "全国人大常委会",
        "urls": [
            "https://www.gov.cn/xinwen/2022-10/31/content_5723425.htm",
        ],
        "search_keywords": "黄河保护法 2022 全文 PDF",
    },
    {
        "id": 19,
        "name": "中华人民共和国湿地保护法_2021",
        "year": 2021,
        "type": "法律",
        "authority": "全国人大常委会",
        "urls": [
            "https://www.gov.cn/xinwen/2021-12/25/content_5664668.htm",
        ],
        "search_keywords": "湿地保护法 2021 全文 PDF",
    },
    {
        "id": 20,
        "name": "中华人民共和国清洁生产促进法_2012修正",
        "year": 2012,
        "type": "法律",
        "authority": "全国人大常委会",
        "urls": [
            "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjMzYTAxNzk4NjJjMGI3NjBiYTk%3D",
        ],
        "search_keywords": "清洁生产促进法 2012修正 全文 PDF",
    },
    {
        "id": 21,
        "name": "中华人民共和国环境影响评价法_2018修正",
        "year": 2018,
        "type": "法律",
        "authority": "全国人大常委会",
        "urls": [
            "https://www.mee.gov.cn/ywgz/fgbz/fl/201811/t20181114_673440.shtml",
        ],
        "search_keywords": "环境影响评价法 2018修正 全文 PDF",
    },
    {
        "id": 22,
        "name": "中华人民共和国节约能源法_2018修正",
        "year": 2018,
        "type": "法律",
        "authority": "全国人大常委会",
        "urls": [
            "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjMzYTAxNzk4NjJkZjYxNzBjMmE%3D",
        ],
        "search_keywords": "节约能源法 2018修正 全文 PDF",
    },
    {
        "id": 23,
        "name": "中华人民共和国可再生能源法_2009修正",
        "year": 2009,
        "type": "法律",
        "authority": "全国人大常委会",
        "urls": [
            "https://flk.npc.gov.cn/detail2.html?ZmY4MDgxODE3OTZhNjMzYTAxNzk4NjJlMDUzNjBjMzE%3D",
        ],
        "search_keywords": "可再生能源法 2009修正 全文 PDF",
    },

    # ═══ 国务院行政法规 ═══
    {
        "id": 24,
        "name": "碳排放权交易管理暂行条例_2024_国务院",
        "year": 2024,
        "type": "行政法规",
        "authority": "国务院",
        "urls": [
            "https://www.gov.cn/zhengce/content/202402/content_6930063.htm",
        ],
        "search_keywords": "碳排放权交易管理暂行条例 2024 全文 PDF",
    },
    {
        "id": 25,
        "name": "建设项目环境保护管理条例_2017修订_国务院",
        "year": 2017,
        "type": "行政法规",
        "authority": "国务院",
        "urls": [
            "https://www.gov.cn/zhengce/content/2017-10/23/content_5233894.htm",
        ],
        "search_keywords": "建设项目环境保护管理条例 2017 全文 PDF",
    },
    {
        "id": 26,
        "name": "畜禽规模养殖污染防治条例_2013_国务院",
        "year": 2013,
        "type": "行政法规",
        "authority": "国务院",
        "urls": [
            "https://www.gov.cn/zwgk/2013-11/26/content_2534836.htm",
        ],
        "search_keywords": "畜禽规模养殖污染防治条例 2013 全文 PDF",
    },
    {
        "id": 27,
        "name": "城镇排水与污水处理条例_2013_国务院",
        "year": 2013,
        "type": "行政法规",
        "authority": "国务院",
        "urls": [
            "https://www.gov.cn/zwgk/2013-10/16/content_2508049.htm",
        ],
        "search_keywords": "城镇排水与污水处理条例 2013 全文 PDF",
    },
    {
        "id": 28,
        "name": "消耗臭氧层物质管理条例_2010_国务院",
        "year": 2010,
        "type": "行政法规",
        "authority": "国务院",
        "urls": [
            "https://www.gov.cn/flfg/2010-04/19/content_1586420.htm",
        ],
        "search_keywords": "消耗臭氧层物质管理条例 2010 全文 PDF",
    },

    # ═══ 国务院/中央规范性文件 ═══
    {
        "id": 29,
        "name": "打赢蓝天保卫战三年行动计划_2018_国务院",
        "year": 2018,
        "type": "规范性文件",
        "authority": "国务院",
        "urls": [
            "https://www.gov.cn/zhengce/content/2018-07/03/content_5303158.htm",
        ],
        "search_keywords": "打赢蓝天保卫战三年行动计划 2018 全文 PDF",
    },
    {
        "id": 30,
        "name": "关于全面加强生态环境保护坚决打好污染防治攻坚战的意见_2018_中共中央国务院",
        "year": 2018,
        "type": "规范性文件",
        "authority": "中共中央 国务院",
        "urls": [
            "https://www.gov.cn/zhengce/2018-06/24/content_5300953.htm",
        ],
        "search_keywords": "全面加强生态环境保护 打好污染防治攻坚战 2018 全文 PDF",
    },
    {
        "id": 31,
        "name": "关于深入打好污染防治攻坚战的意见_2021_中共中央国务院",
        "year": 2021,
        "type": "规范性文件",
        "authority": "中共中央 国务院",
        "urls": [
            "https://www.gov.cn/zhengce/2021-11/07/content_5649656.htm",
        ],
        "search_keywords": "深入打好污染防治攻坚战 2021 全文 PDF",
    },
    {
        "id": 32,
        "name": "2030年前碳达峰行动方案_2021_国务院",
        "year": 2021,
        "type": "规范性文件",
        "authority": "国务院",
        "urls": [
            "https://www.gov.cn/zhengce/content/2021-10/26/content_5644984.htm",
        ],
        "search_keywords": "2030年前碳达峰行动方案 2021 全文 PDF",
    },
    {
        "id": 33,
        "name": "关于完整准确全面贯彻新发展理念做好碳达峰碳中和工作的意见_2021_中共中央国务院",
        "year": 2021,
        "type": "规范性文件",
        "authority": "中共中央 国务院",
        "urls": [
            "https://www.gov.cn/zhengce/2021-10/24/content_5644613.htm",
        ],
        "search_keywords": "碳达峰碳中和意见 2021 全文 PDF",
    },
    {
        "id": 34,
        "name": "生态文明体制改革总体方案_2015_中共中央国务院",
        "year": 2015,
        "type": "规范性文件",
        "authority": "中共中央 国务院",
        "urls": [
            "https://www.gov.cn/guowuyuan/2015-09/21/content_2936327.htm",
        ],
        "search_keywords": "生态文明体制改革总体方案 2015 全文 PDF",
    },
    {
        "id": 35,
        "name": "关于构建现代环境治理体系的指导意见_2020_中办国办",
        "year": 2020,
        "type": "规范性文件",
        "authority": "中共中央办公厅 国务院办公厅",
        "urls": [
            "https://www.gov.cn/zhengce/2020-03/03/content_5486380.htm",
        ],
        "search_keywords": "构建现代环境治理体系 2020 全文 PDF",
    },
    {
        "id": 36,
        "name": "关于加快经济社会发展全面绿色转型的意见_2024_中共中央国务院",
        "year": 2024,
        "type": "规范性文件",
        "authority": "中共中央 国务院",
        "urls": [
            "https://www.gov.cn/zhengce/202408/content_6964484.htm",
        ],
        "search_keywords": "加快经济社会发展全面绿色转型 2024 全文 PDF",
    },
    {
        "id": 37,
        "name": "关于推进污水资源化利用的指导意见_2021_十部门",
        "year": 2021,
        "type": "规范性文件",
        "authority": "国家发改委等十部门",
        "urls": [
            "https://www.gov.cn/zhengce/zhengceku/2021-01/12/content_5579202.htm",
        ],
        "search_keywords": "推进污水资源化利用 2021 全文 PDF",
    },
    {
        "id": 38,
        "name": "空气质量持续改善行动计划_2023_国务院",
        "year": 2023,
        "type": "规范性文件",
        "authority": "国务院",
        "urls": [
            "https://www.gov.cn/zhengce/content/202312/content_6920473.htm",
        ],
        "search_keywords": "空气质量持续改善行动计划 2023 全文 PDF",
    },

    # ═══ 部门规章（生态环境部等）═══
    {
        "id": 39,
        "name": "环境影响评价公众参与办法_2018_生态环境部",
        "year": 2018,
        "type": "部门规章",
        "authority": "生态环境部",
        "urls": [
            "https://www.mee.gov.cn/gkml/sthjbgw/sthjbl/201807/t20180716_446647.htm",
        ],
        "search_keywords": "环境影响评价公众参与办法 2018 全文 PDF",
    },
    {
        "id": 40,
        "name": "排污许可管理办法_2018_生态环境部",
        "year": 2018,
        "type": "部门规章",
        "authority": "生态环境部",
        "urls": [
            "https://www.mee.gov.cn/gkml/hbb/bl/201801/t20180117_430330.htm",
        ],
        "search_keywords": "排污许可管理办法试行 2018 全文 PDF",
    },
    {
        "id": 41,
        "name": "生态环境损害赔偿管理规定_2022_生态环境部",
        "year": 2022,
        "type": "规范性文件",
        "authority": "生态环境部等14部门",
        "urls": [
            "https://www.mee.gov.cn/xxgk2018/xxgk/xxgk03/202205/t20220519_983452.html",
        ],
        "search_keywords": "生态环境损害赔偿管理规定 2022 全文 PDF",
    },
    {
        "id": 42,
        "name": "国家危险废物名录_2021修订_生态环境部",
        "year": 2021,
        "type": "部门规章",
        "authority": "生态环境部 国家发改委 公安部等",
        "urls": [
            "https://www.mee.gov.cn/xxgk2018/xxgk/xxgk02/202011/t20201127_810202.html",
        ],
        "search_keywords": "国家危险废物名录 2021 全文 PDF",
    },
    {
        "id": 43,
        "name": "建设用地土壤污染风险管控和修复管理办法_2019_生态环境部",
        "year": 2019,
        "type": "部门规章",
        "authority": "生态环境部",
        "urls": [
            "https://www.mee.gov.cn/gkml/sthjbgw/sthjbl/201904/t20190401_698430.htm",
        ],
        "search_keywords": "建设用地土壤污染风险管控和修复管理办法 2019 全文 PDF",
    },
    {
        "id": 44,
        "name": "碳排放权登记管理规则_2021_生态环境部",
        "year": 2021,
        "type": "规范性文件",
        "authority": "生态环境部",
        "urls": [
            "https://www.mee.gov.cn/xxgk2018/xxgk/xxgk05/202105/t20210519_834574.html",
        ],
        "search_keywords": "碳排放权登记管理规则 2021 全文 PDF",
    },

    # ═══ 地方性法规 ═══
    {
        "id": 45,
        "name": "上海市环境保护条例_2022修正",
        "year": 2022,
        "type": "地方性法规",
        "authority": "上海市人大常委会",
        "urls": [
            "https://www.shanghai.gov.cn/nw42994/20221129/5efc35d3e81d48e3b7cc35e71b13ee73.html",
        ],
        "search_keywords": "上海市环境保护条例 2022 全文 PDF",
    },
    {
        "id": 46,
        "name": "广东省环境保护条例_2018修正",
        "year": 2018,
        "type": "地方性法规",
        "authority": "广东省人大常委会",
        "urls": [
            "https://www.gd.gov.cn/zwgk/wjk/qbwj/content/post_877233.html",
        ],
        "search_keywords": "广东省环境保护条例 2018 全文 PDF",
    },
    {
        "id": 47,
        "name": "河北省大气污染防治条例_2016",
        "year": 2016,
        "type": "地方性法规",
        "authority": "河北省人大常委会",
        "urls": [
            "https://www.hebei.gov.cn/columns/d13e4e60-9228-4e39-b3c0-ddb84c73b7e0/202001/07/07ed3bea-a6f6-4a2a-a0bb-81cd79bbc4f7.html",
        ],
        "search_keywords": "河北省大气污染防治条例 2016 全文 PDF",
    },
    {
        "id": 48,
        "name": "浙江省生态环境保护条例_2022",
        "year": 2022,
        "type": "地方性法规",
        "authority": "浙江省人大常委会",
        "urls": [
            "https://www.zj.gov.cn/art/2022/5/27/art_1229631291_59061218.html",
        ],
        "search_keywords": "浙江省生态环境保护条例 2022 全文 PDF",
    },
    {
        "id": 49,
        "name": "深圳经济特区生态环境保护条例_2021",
        "year": 2021,
        "type": "地方性法规",
        "authority": "深圳市人大常委会",
        "urls": [
            "https://www.sz.gov.cn/zfgb/2021/gb1212/content/post_9463174.html",
        ],
        "search_keywords": "深圳经济特区生态环境保护条例 2021 全文 PDF",
    },
    {
        "id": 50,
        "name": "江苏省生态环境监测条例_2020",
        "year": 2020,
        "type": "地方性法规",
        "authority": "江苏省人大常委会",
        "urls": [
            "https://www.jiangsu.gov.cn/art/2020/5/1/art_64797_9091993.html",
        ],
        "search_keywords": "江苏省生态环境监测条例 2020 全文 PDF",
    },
]


def download_file(url: str, save_path: str, timeout: int = 30) -> bool:
    """下载单个文件"""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        req = urllib.request.Request(url, headers=headers)

        # 先尝试正常SSL验证
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.URLError as ssl_err:
            if "CERTIFICATE" in str(ssl_err).upper() or "SSL" in str(ssl_err).upper():
                print(f"    ⚠ SSL证书验证失败，降级为不验证模式（部分政府网站证书不标准）")
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
            else:
                raise

        content_type = resp.headers.get("Content-Type", "")
        data = resp.read()

        # 验证是否为有效PDF（检查PDF魔术字节）
        if not data[:5] == b'%PDF-':
            print(f"    ⚠ 文件不是有效PDF（魔术字节不匹配），跳过")
            return False

        if len(data) < 1000:
            print(f"    ⚠ 文件过小({len(data)}字节)，可能不是完整PDF")
            return False

        with open(save_path, "wb") as f:
            f.write(data)
        print(f"    ✓ 下载成功: {len(data)/1024:.0f}KB")
        return True

    except Exception as e:
        print(f"    ✗ 下载失败: {e}")
        return False


def try_download_policy(policy: dict, output_dir: str) -> bool:
    """尝试从多个 URL 下载一份政策文件"""
    idx = policy["id"]
    name = policy["name"]
    filename = f"{idx:02d}_{name}.pdf"
    save_path = os.path.join(output_dir, filename)

    if os.path.exists(save_path):
        size = os.path.getsize(save_path)
        if size > 5000:
            print(f"  [{idx:02d}] 已存在: {filename} ({size/1024:.0f}KB)")
            return True

    print(f"  [{idx:02d}] 下载: {name}")
    for url in policy.get("urls", []):
        print(f"    尝试: {url[:80]}...")
        if download_file(url, save_path):
            return True
        time.sleep(1)

    print(f"    ⚠ 所有URL均失败，请手动下载")
    print(f"    搜索关键词: {policy['search_keywords']}")
    return False


def main():
    """主函数"""
    output_dir = str(Path(__file__).parent.parent / "政策文件")
    os.makedirs(output_dir, exist_ok=True)

    print("═" * 60)
    print("  环境政策文件批量下载")
    print("═" * 60)
    print(f"\n目标目录: {output_dir}")
    print(f"待下载数: {len(POLICY_LIST)} 份\n")

    success = 0
    failed = []

    for policy in POLICY_LIST:
        if try_download_policy(policy, output_dir):
            success += 1
        else:
            failed.append(policy)
        time.sleep(0.5)

    # ─── 汇总报告 ───
    print("\n" + "═" * 60)
    print(f"  下载完成: {success}/{len(POLICY_LIST)} 份成功")
    if failed:
        print(f"\n  以下 {len(failed)} 份需要手动下载：")
        print("  " + "─" * 50)
        for p in failed:
            print(f"  [{p['id']:02d}] {p['name']}")
            print(f"       搜索: {p['search_keywords']}")
            if p.get("urls"):
                print(f"       参考URL: {p['urls'][0]}")
        print()
        print("  手动下载建议：")
        print("  1. 在浏览器中搜索上述关键词")
        print("  2. 优先从以下官方来源下载：")
        print("     - 中国政府网 www.gov.cn")
        print("     - 全国人大法律法规库 flk.npc.gov.cn")
        print("     - 生态环境部 www.mee.gov.cn")
        print("     - 北大法宝 www.pkulaw.com")
        print("  3. 下载后存入 政策文件/ 目录，文件名格式：")
        print("     {编号:02d}_{政策名称}.pdf")
    print("═" * 60)

    # 列出当前目录下所有PDF
    existing = sorted(Path(output_dir).glob("*.pdf"))
    print(f"\n当前共有 {len(existing)} 份PDF文件：")
    for f in existing:
        size = f.stat().st_size / 1024
        print(f"  {f.name} ({size:.0f}KB)")


if __name__ == "__main__":
    main()
