# ── SVG-визуализация древа ────────────────────────────────
def calculate_levels(data: list) -> dict:
    if not data: return {}
    # строим граф связей: если A родитель B, то разница уровней L(B) - L(A) = 1
    graph = {p['id']: [] for p in data}
    for p in data:
        for pid in p.get('parents', []):
            if pid in graph:
                graph[pid].append((p['id'], 1))
                graph[p['id']].append((pid, -1))
                
    levels = {}
    for p in data:
        start_id = p['id']
        if start_id in levels: continue
        
        # Обход (BFS) для синхронизации уровней (муж и жена будут на одном уровне)
        queue = [start_id]
        comp_levels = {start_id: 0}
        
        while queue:
            curr = queue.pop(0)
            curr_lv = comp_levels[curr]
            for neighbor, delta in graph[curr]:
                if neighbor not in levels and neighbor not in comp_levels:
                    comp_levels[neighbor] = curr_lv + delta
                    queue.append(neighbor)
                    
        # Нормализуем ветвь: предки всегда сверху (уровень 0)
        mn = min(comp_levels.values())
        for k, v in comp_levels.items():
            levels[k] = v - mn
            
    return levels

def generate_tree_svg(data: list) -> str:
    W, H, HG, VG = 180, 64, 36, 90
    EMPTY = ('<svg width="500" height="200" xmlns="http://www.w3.org/2000/svg">'
             '<rect width="500" height="200" fill="#08080f"/>'
             '<text x="250" y="110" text-anchor="middle" fill="#333" '
             'font-size="15" font-family="Inter,sans-serif">'
             'Добавьте первого члена семьи</text></svg>')
    if not data: return EMPTY
    levels = calculate_levels(data)
    by_lv: dict = {}
    for p in data:
        lv = levels.get(p['id'], 0); by_lv.setdefault(lv, []).append(p)
        
    # Группируем мужей и жён (сортируем по общим детям), чтобы они стояли рядом
    def get_child_ids(p):
        return tuple(sorted([c['id'] for c in data if p['id'] in c.get('parents', [])]))
    for lv in by_lv:
        by_lv[lv].sort(key=get_child_ids)
    max_lv  = max(levels.values())
    max_cnt = max(len(v) for v in by_lv.values())
    svg_w   = max(600, max_cnt * (W + HG) + 80)
    svg_h   = (max_lv + 1) * (H + VG) + 60
    positions: dict[str, tuple] = {}
    for lv in range(max_lv + 1):
        people = by_lv.get(lv, [])
        total  = len(people) * W + (len(people) - 1) * HG
        sx     = (svg_w - total) / 2
        for i, p in enumerate(people):
            positions[p['id']] = (sx + i * (W + HG), 30 + lv * (H + VG))
    parts = [
        f'<svg width="{svg_w}" height="{svg_h}" xmlns="http://www.w3.org/2000/svg" '
        f'style="max-width:100%;height:auto">',
        f'<rect width="{svg_w}" height="{svg_h}" fill="#08080f" rx="16"/>'
    ]
    COLORS = [
        '#00ffcc', '#0088ff', '#9b59b6', '#ff3366', '#ff9933',
        '#f1c40f', '#2ecc71', '#1abc9c', '#e67e22', '#e74c3c'
    ]
    
    # Кривые Безье
    for p in data:
        if p['id'] not in positions: continue
        px, py = positions[p['id']]
        cx2, cy2 = px + W/2, py
        for pid in p.get('parents', []):
            if pid not in positions: continue
            ppx, ppy = positions[pid]
            cx1, cy1 = ppx + W/2, ppy + H
            midy = (cy1 + cy2) / 2
            parent_lv = levels.get(pid, 0)
            edge_color = COLORS[parent_lv % len(COLORS)]
            parts.append(
                f'<path d="M {cx1:.1f} {cy1:.1f} C {cx1:.1f} {midy:.1f}, '
                f'{cx2:.1f} {midy:.1f}, {cx2:.1f} {cy2:.1f}" '
                f'stroke="{edge_color}" stroke-width="1.5" fill="none" opacity="0.4" stroke-dasharray="4,3"/>'
            )
    # Узлы
    for p in data:
        if p['id'] not in positions: continue
        x, y   = positions[p['id']]
        is_root = not p.get('parents')
        lv = levels.get(p['id'], 0)
        stroke = COLORS[lv % len(COLORS)]
        name    = p['name'] if len(p['name']) <= 20 else p['name'][:18] + '…'
        parts += [
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{W}" height="{H}" rx="10" '
            f'fill="#0d0d1e" stroke="{stroke}" stroke-width="1.8"/>',
            f'<text x="{x+W/2:.1f}" y="{y+H/2-6:.1f}" text-anchor="middle" '
            f'fill="{stroke}" font-size="12" font-weight="700" font-family="Inter,sans-serif">{name}</text>',
        ]
        # Подпись: дети или «Предок»
        kids = sum(1 for q in data if p['id'] in q.get('parents', []))
        sub  = f'{kids} дет.' if kids else ('предок' if is_root else '')
        if sub:
            parts.append(
                f'<text x="{x+W/2:.1f}" y="{y+H/2+10:.1f}" text-anchor="middle" '
                f'fill="#555" font-size="10" font-family="Inter,sans-serif">{sub}</text>'
            )
    parts.append('</svg>')
    return ''.join(parts)

