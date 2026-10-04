#!/usr/bin/env bash
# 按发布快照 (releases/<NAME>.json) 驱动构建:
# 各子仓库被 checkout 到快照锁定的 branch/tag/commit, 再由安装器完成构建。
# 用法:
#   ./build.sh <release-name>          # 例: ./build.sh v0.5.0
#   ./build.sh --list                  # 列出可用发布快照
#   ./build.sh --stage 2 --stage 3 v0.5.0   # 只跑指定阶段
set -eo pipefail
cd "$(dirname "$0")"

usage() { echo "用法: $0 [--stage N]... <release-name> | --list"; exit 1; }

STAGES=()
while [ $# -gt 0 ]; do
  case "$1" in
    --stage) STAGES+=("$2"); shift 2 ;;
    --list) ls -1 releases/*.json 2>/dev/null | sed 's|releases/||; s|\.json$||' || echo "(无发布快照)"; exit 0 ;;
    -h|--help) usage ;;
    -*) usage ;;
    *) REL="$1"; shift ;;
  esac
done
[ -n "${REL:-}" ] || usage
REL_FILE="releases/${REL}.json"
[ -f "$REL_FILE" ] || { echo "发布快照不存在: $REL_FILE (先 ./repo_versions.py --freeze ${REL})"; exit 1; }

echo "== 使用发布快照 ${REL_FILE} =="
python3 - "$REL_FILE" <<'PY'
import json, sys
rel = json.load(open(sys.argv[1]))
print(f"release: {rel.get('release')}  created: {rel.get('created')}")
for k in sorted(rel.get("repos", {})):
    r = rel["repos"][k]
    print(f"  {k:<40} {r.get('kind',''):<7} {r.get('ref','')} @ {r.get('commit','')}")
PY

# 快照驱动: 安装器 REPO_VERSIONS_FILE 指向发布快照, 2.2 会把各仓库切到锁定版本
export REPO_VERSIONS_FILE="$(pwd)/${REL_FILE}"
if [ ${#STAGES[@]} -gt 0 ]; then
  ARGS=(); for s in "${STAGES[@]}"; do ARGS+=(--stage "$s"); done
  exec python3 semantic_installer.py "${ARGS[@]}"
fi
exec python3 semantic_installer.py
