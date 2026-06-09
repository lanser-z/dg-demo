#!/usr/bin/env bash
# validate.sh — static checks for draft-CLAUDE.md
set -u
DRAFT="/home/szs/Playground/dg-demo/openspec/changes/claude-md-vibe-coding/draft-CLAUDE.md"

echo "=== 2.1 行数预算 ==="
TOTAL=$(wc -l < "$DRAFT")
echo "总行数: $TOTAL (预算 ≤ 50)"

KERNEL_START=$(grep -n '^## Kernel' "$DRAFT" | head -1 | cut -d: -f1)
KERNEL_END=$(grep -n '^## Index' "$DRAFT" | head -1 | cut -d: -f1)
KERNEL_LINES=$((KERNEL_END - KERNEL_START))
echo "Kernel 行数: $KERNEL_LINES (预算 ≤ 20)"

INDEX_ROWS=$(awk '/^## Index/{flag=1; next} flag && /^\|/{count++} END{print count-2}' "$DRAFT")
echo "Index 表格数据行（不含表头/分隔）: $INDEX_ROWS (预算 ≤ 15)"

echo ""
echo "=== 2.2 路径可达 ==="
PATHS=$(grep -oE '`[a-zA-Z_/.]+\.(py|md|yaml|yml|sh)`' "$DRAFT" | tr -d '`' | sort -u)
for p in $PATHS; do
  if git ls-files --error-unmatch "$p" >/dev/null 2>&1; then
    echo "  OK  $p"
  else
    echo "  FAIL $p"
  fi
done

echo ""
echo "=== 2.3 Kernel 无 shell/Python/SQL 代码块 ==="
KERNEL_BLOCK=$(awk '/^## Kernel/{flag=1} /^## Index/{flag=0} flag' "$DRAFT")
if echo "$KERNEL_BLOCK" | grep -qE '```|^    [a-z]'; then
  echo "  FAIL: Kernel 含代码块"
else
  echo "  OK: 无代码块"
fi

echo ""
echo "=== 2.4 硬约束措辞（每条须以否定词或禁令开头）==="
awk '/^## Kernel/{flag=1} /^## Index/{flag=0} flag && /^- /' "$DRAFT" | while read -r line; do
  if echo "$line" | grep -qE '^- (不得|禁止|不能|别)'; then
    echo "  OK  $line"
  else
    echo "  FAIL $line"
  fi
done
