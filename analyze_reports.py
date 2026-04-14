import re, json

content = open('frontend/src/views/ReportsView.vue', encoding='utf-8').read()
ar = json.load(open('frontend/src/locales/ar.json', encoding='utf-8'))
en = json.load(open('frontend/src/locales/en.json', encoding='utf-8'))

def get_key(d, path):
    parts = path.split('.')
    cur = d
    for p in parts:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur

# 1. All $t() keys used
keys_used = sorted(set(re.findall(r'\$t\(["\']([^"\']+)["\']\)', content)))

# 2. Missing in AR or EN
missing_ar = [k for k in keys_used if get_key(ar, k) is None]
missing_en = [k for k in keys_used if get_key(en, k) is None]

# 3. Hardcoded Arabic text (not inside $t())
# Find Arabic unicode chars in template strings
arabic_matches = re.findall(r'(?<!\$t\()["\'][^"\']*[\u0600-\u06FF][^"\']*["\']', content)

# 4. Check for missing kanban.columns keys used
kanban_cols = re.findall(r'kanban\.columns\.(\w+)', content)
kanban_prios = re.findall(r'kanban\.priorities\.(\w+)', content)
kanban_types = re.findall(r'kanban\.issue_types\.(\w+)', content)

print("=" * 50)
print("MISSING TRANSLATION KEYS")
print("=" * 50)
print(f"\nMissing in AR ({len(missing_ar)}):")
for k in missing_ar: print(f"  {k}")
print(f"\nMissing in EN ({len(missing_en)}):")
for k in missing_en: print(f"  {k}")

print("\n" + "=" * 50)
print("HARDCODED ARABIC TEXT IN TEMPLATE")
print("=" * 50)
for a in arabic_matches[:30]:
    a = a.strip()
    if len(a) > 3:
        print(f"  {a[:100]}")

print("\n" + "=" * 50)
print("KANBAN KEYS USED")
print("=" * 50)
print(f"  columns: {set(kanban_cols)}")
print(f"  priorities: {set(kanban_prios)}")
print(f"  issue_types: {set(kanban_types)}")

# 5. Check if kanban.columns.to_do exists
for k in ['kanban.columns.to_do', 'kanban.columns.in_progress', 'kanban.columns.done']:
    ar_val = get_key(ar, k)
    en_val = get_key(en, k)
    print(f"\n  {k}: AR={ar_val!r}, EN={en_val!r}")

# 6. Check reports keys that exist in EN but NOT in AR
print("\n" + "=" * 50)
print("REPORTS KEYS IN EN BUT MISSING IN AR")
print("=" * 50)
en_reports = en.get('reports', {})
ar_reports = ar.get('reports', {})
for k, v in en_reports.items():
    if k not in ar_reports:
        print(f"  reports.{k}: EN={v!r}")

print("\n" + "=" * 50)
print("REPORTS KEYS IN AR BUT MISSING IN EN")
print("=" * 50)
for k, v in ar_reports.items():
    if k not in en_reports:
        print(f"  reports.{k}: AR={v!r}")

print(f"\nTotal keys used in component: {len(keys_used)}")
