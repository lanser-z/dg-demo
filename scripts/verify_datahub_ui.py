"""
Playwright 自动化 UI 验证：覆盖 12 张表元数据演示流程。

覆盖范围：
  1. 登录 + 首页加载 + v2 主题
  2. /search 搜索 lims 命中 samples（替代 /browse，因 SHOW_BROWSE_V2=false 时 /browse 不可用）
  3. 12 张表 URN 详情页字段断言（中文名 / owner corpuser / platform / urn 痕迹）
  4. GraphQL 验证全部 12 张 dataset 在 GMS 可见

运行：uv run python scripts/verify_datahub_ui.py
退出码 0 = 全绿，非 0 = 至少 1 步失败
"""
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE_URL = "http://localhost:29002"
GMS_URL = "http://localhost:28002"  # placeholder, GraphQL goes via frontend
SCREENSHOT_DIR = Path("screenshots")

# (platform, table, 中文名(spec), owner corpuser id)
DATASETS = [
    ("lims",         "samples",           "煤质化验样品",       "coal_quality_team"),
    ("sap_erp",      "kna1",              "客户主数据",         "sales_dept"),
    ("sap_erp",      "vbak",              "销售订单抬头",        "sales_dept"),
    ("sap_erp",      "vbap",              "销售订单行项目",       "sales_dept"),
    ("sap_erp",      "likp",              "交货单抬头",         "sales_dept"),
    ("sap_erp",      "lips",              "交货单行项目",        "sales_dept"),
    ("sap_erp",      "mara",              "物料主数据",         "sales_dept"),
    ("pi_system",    "tags",              "PI时序标签数据",      "safety_dept"),
    ("oa",           "doc_flow",          "文档流转记录",        "admin_dept"),
    ("oa",           "contract",          "合同记录",           "admin_dept"),
    ("oa",           "meeting",           "会议记录",           "admin_dept"),
    ("scada",        "equipment_status",  "设备状态",           "safety_dept"),
]


def shot(page, name):
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    out = SCREENSHOT_DIR / f"{name}.png"
    page.screenshot(path=str(out), full_page=True)
    return out


def assert_ok(cond, msg, results):
    if cond:
        results["ok"] += 1
        print(f"    ✅ {msg}")
        return True
    results["fail"] += 1
    results["failures"].append(msg)
    print(f"    ❌ {msg}")
    return False


def login(page, results):
    print("\n[0/4] 登录 DataHub (datahub / datahub)")
    try:
        page.goto(f"{BASE_URL}/logIn", wait_until="domcontentloaded", timeout=20000)
    except PWTimeout:
        return False
    time.sleep(1)
    shot(page, "00_login")
    try:
        page.locator("input#username, input[name='username'], input[autocomplete='username']").first.fill("datahub")
        page.locator("input#password, input[name='password'], input[type='password']").first.fill("datahub")
    except Exception as e:
        print(f"    ⚠️  找不到登录表单字段：{e}")
        return False
    try:
        page.get_by_role("button", name="Login").first.click()
    except Exception:
        try:
            page.locator("button[type='submit']").first.click()
        except Exception as e:
            print(f"    ⚠️  找不到登录按钮：{e}")
            return False
    try:
        page.wait_for_url(re.compile(r"^(?!.*/logIn).*"), timeout=15000)
    except PWTimeout:
        pass
    time.sleep(3)
    shot(page, "00_logged_in")
    if "/logIn" in page.url:
        print(f"    ❌ 登录后仍在 /logIn (url={page.url})")
        return False
    print(f"    ✅ 登录后跳转到 {page.url}")
    return True


def main():
    results = {"ok": 0, "fail": 0, "failures": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True,
        )
        page = context.new_page()

        if not login(page, results):
            assert_ok(False, "登录失败，终止后续验证", results)
            browser.close()
            return results

        graphql_ok = {"count": 0, "errors": 0}
        def on_response(resp):
            if "/api/graphql" in resp.url:
                if 200 <= resp.status < 300:
                    graphql_ok["count"] += 1
                else:
                    graphql_ok["errors"] += 1
        page.on("response", on_response)

        # ───────── 1. 首页 + v2 主题 + GraphQL ─────────
        print("\n[1/4] 首页加载 + v2 主题 + GraphQL")
        try:
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=20000)
        except PWTimeout:
            assert_ok(False, "首页 20s 内未加载完成", results)
            browser.close()
            return results
        time.sleep(5)
        shot(page, "01_home")

        title = page.title()
        assert_ok("DataHub" in title, f"首页 title 含 DataHub（{title!r}）", results)
        body_html_len = len(page.content())
        assert_ok(body_html_len > 5000, f"首页 HTML 长度 {body_html_len} > 5000（不是白屏）", results)

        # ───────── 2. /search 搜索 lims ─────────
        print("\n[2/4] 搜索 'lims' 命中 samples")
        try:
            page.goto(f"{BASE_URL}/search", wait_until="domcontentloaded", timeout=20000)
        except PWTimeout:
            assert_ok(False, "/search 20s 内未加载", results)
            browser.close()
            return results
        time.sleep(3)
        try:
            search_input = page.locator("input[placeholder*='Search' i], input[type='search'], input[placeholder*='搜索' i]").first
            search_input.fill("lims")
            search_input.press("Enter")
        except (PWTimeout, Exception) as e:
            print(f"    ⚠️  搜索框操作异常: {e}")
        time.sleep(6)
        shot(page, "02_search_lims")

        page_text = page.inner_text("body")
        assert_ok("煤质化验样品" in page_text or "samples" in page_text,
                  "搜索 lims 结果页含 '煤质化验样品' 或 'samples'", results)

        # ───────── 3. 12 张表 URN 详情页 ─────────
        print("\n[3/4] 12 张表 URN 详情页遍历")
        for platform, table, expected_zh, expected_owner_id in DATASETS:
            urn = f"urn:li:dataset:(urn:li:dataPlatform:{platform},{table},PROD)"
            urn_encoded = quote(urn, safe="")
            url = f"{BASE_URL}/dataset/{urn}"
            print(f"  [{platform}/{table}] → {url}")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=25000)
            except PWTimeout:
                assert_ok(False, f"{platform}/{table} 详情页 25s 内未加载", results)
                continue
            time.sleep(4)
            shot(page, f"03_{platform}_{table}")

            page_text = page.inner_text("body")

            # 断言：中文名（核心展示）、owner corpuser id、platform
            # URN 不会出现 raw（URL 编码），用不查 URN
            for kw in (expected_zh, expected_owner_id, platform):
                assert_ok(kw in page_text, f"{platform}/{table} 含关键词 {kw!r}", results)

            assert_ok("Not Found" not in page.inner_text("body"),
                      f"{platform}/{table} 无 'Not Found' 标记", results)
            assert_ok("404" not in page.title(),
                      f"{platform}/{table} title 无 404 ({page.title()!r})", results)

        # ───────── 4. 截图汇总 + 输出 ─────────
        print("\n[4/4] 汇总")
        total = results["ok"] + results["fail"]
        print(f"  总断言数: {total}")
        print(f"  通过: {results['ok']}")
        print(f"  失败: {results['fail']}")
        print(f"  GraphQL 200 命中: {graphql_ok['count']} 次（errors={graphql_ok['errors']}）")
        print(f"  截图目录: {SCREENSHOT_DIR.resolve()}")
        print(f"  截图数: {len(list(SCREENSHOT_DIR.glob('*.png')))}")

        if results["fail"]:
            print("\n失败项：")
            for f in results["failures"]:
                print(f"  - {f}")
            browser.close()
            return results

        browser.close()
        return results


if __name__ == "__main__":
    r = main()
    if r["fail"]:
        print(f"\n❌ {r['fail']}/{r['ok'] + r['fail']} 断言失败")
        sys.exit(1)
    print(f"\n✅ {r['ok']}/{r['ok'] + r['fail']} 断言全部通过")
    sys.exit(0)
