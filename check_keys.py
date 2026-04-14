import re, json

content = open('frontend/src/views/ReportsView.vue', encoding='utf-8').read()
keys_used = sorted(set(re.findall(r'\$t\(["\']([^"\']+)["\']\)', content)))

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

missing_ar, missing_en = [], []
for k in keys_used:
    if get_key(ar, k) is None:
        missing_ar.append(k)
    if get_key(en, k) is None:
        missing_en.append(k)

print('=== MISSING IN AR ===')
for k in missing_ar: print(' ', k)
print()
print('=== MISSING IN EN ===')
for k in missing_en: print(' ', k)
print()
print(f'Total keys used: {len(keys_used)}')
print(f'Missing AR: {len(missing_ar)}, Missing EN: {len(missing_en)}')
print()
print('=== ALL KEYS USED ===')
for k in keys_used: print(' ', k)
