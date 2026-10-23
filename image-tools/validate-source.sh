#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "$0")/.." && pwd)

if find "$root" -type f \( -name '*.img' -o -name '*.img.gz' -o -name '*.iso' -o -name '*.pyc' -o -name '*.log' -o -name '*.pid' \) -print -quit | grep -q .; then
  echo 'Arquivo gerado ou privado encontrado.' >&2
  exit 1
fi

python3 - "$root" <<'PY'
from pathlib import Path
import json, sys
root = Path(sys.argv[1])
for path in root.rglob('*.py'):
    compile(path.read_text(encoding='utf-8'), str(path), 'exec')
for path in root.rglob('*.json'):
    json.loads(path.read_text(encoding='utf-8'))
print('Python e JSON: OK')
PY

while IFS= read -r -d '' file; do bash -n "$file"; done < <(find "$root" -type f -name '*.sh' -print0)
echo 'Shell: OK'
