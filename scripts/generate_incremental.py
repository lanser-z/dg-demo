# scripts/generate_incremental.py
"""
每日增量数据生成脚本

用法：
  python scripts/generate_incremental.py                          # 生成今天
  python scripts/generate_incremental.py 2024-01-15             # 生成指定日期
  python scripts/generate_incremental.py 2024-01-01 2024-01-31  # 生成日期范围
"""
import sys
sys.path.insert(0, '/home/szs/Playground/dg-demo')

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.dg_simulator.sap_incremental import SAPIncrementalGenerator
from src.dg_simulator.pi_incremental import PIIncrementalGenerator
from src.dg_simulator.lims_incremental import LIMSIncrementalGenerator
from src.dg_simulator.oa_incremental import OAIncrementalGenerator


def parse_args():
    parser = argparse.ArgumentParser(description='A公司增量数据生成器')
    parser.add_argument('start_date', nargs='?', default=None, help='开始日期 YYYY-MM-DD')
    parser.add_argument('end_date', nargs='?', default=None, help='结束日期 YYYY-MM-DD（不包含）')
    parser.add_argument('--parallel', action='store_true', help='多系统并行生成（当前串行）')
    parser.add_argument('--workers', type=int, default=4, help='并行worker数')
    return parser.parse_args()


def generate_single_day(date_str: str, output_base: str) -> dict:
    """生成单日增量数据（串行执行各系统）"""
    print(f"\n{'=' * 60}")
    print(f"日期: {date_str}")
    print('=' * 60)

    results = {'date': date_str, 'systems': []}

    generators = [
        ('SAP_ERP', SAPIncrementalGenerator({}, output_base)),
        ('PI_System', PIIncrementalGenerator({}, output_base)),
        ('LIMS', LIMSIncrementalGenerator({}, output_base)),
        ('OA', OAIncrementalGenerator({}, output_base)),
    ]

    total_rows = 0

    for sys_name, gen in generators:
        try:
            start = datetime.now()
            result = gen.generate(date_str)
            elapsed = (datetime.now() - start).total_seconds()

            for rec in result.get('records', []):
                rows = rec.get('rows', 0)
                total_rows += rows
                print(f"  [{sys_name}] {rec['table']}: {rows:,} 行 ({elapsed:.1f}s)")

            results['systems'].append({
                'system': sys_name,
                'result': result,
            })

        except Exception as e:
            print(f"  [{sys_name}] ERROR: {e}")
            results['systems'].append({
                'system': sys_name,
                'error': str(e),
            })

    print(f"\n  >> 当日合计: {total_rows:,} 行")

    # 更新每日汇总
    summary_path = Path(output_base) / date_str / '_summary.json'
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, 'w') as f:
        json.dump({
            'date': date_str,
            'total_rows': total_rows,
            'generated_at': datetime.now().isoformat(),
        }, f, indent=2)

    return results


def main():
    args = parse_args()

    # 确定日期范围
    if args.start_date:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now()

    if args.end_date:
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    else:
        end_date = start_date + timedelta(days=1)

    output_base = '/home/szs/Playground/dg-demo/data/incremental'

    # 统计汇总
    all_results = []
    current = start_date

    print("=" * 60)
    print("A公司 每日增量数据生成器")
    print(f"日期范围: {start_date.date()} ~ {end_date.date()}")
    print("=" * 60)

    while current < end_date:
        date_str = current.strftime('%Y-%m-%d')
        result = generate_single_day(date_str, output_base)
        all_results.append(result)
        current += timedelta(days=1)

    # 汇总报告
    print("\n" + "=" * 60)
    print("生成汇总")
    print("=" * 60)

    total_all = 0
    for r in all_results:
        d = r['date']
        sys_count = len(r.get('systems', []))
        success = sum(1 for s in r.get('systems', []) if 'error' not in s)
        rows = sum(
            rec.get('rows', 0)
            for s in r.get('systems', [])
            for rec in s.get('result', {}).get('records', [])
        )
        total_all += rows
        print(f"  {d}: {rows:>12,} 行 | {success}/{sys_count} 系统成功")

    print(f"\n  总计: {total_all:,} 行")


if __name__ == '__main__':
    main()
