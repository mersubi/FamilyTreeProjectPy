import os
from nicegui import ui
from data import family_data, state, view_state, save_data, imap, initials, get_relations, MEDIA_DIR
from svg_render import generate_tree_svg

view_state = {'mode': 'profile'}  # 'profile' | 'tree'

# ── Диалог добавления/редактирования ──────────────────────
crud_dialog = ui.dialog()

def open_add(*, child_id=None, parent_id=None, sibling_id=None):
    crud_dialog.clear()
    with crud_dialog, ui.card().style(
        'background:#111120;color:#fff;padding:2rem;min-width:480px;max-width:560px;'
        'border:1px solid rgba(0,136,255,.3);border-radius:18px;gap:12px'
    ):
        if child_id: title = 'Новый родитель'
        elif parent_id: title = 'Новый ребёнок'
        elif sibling_id: title = 'Новый брат/сестра'
        else: title = 'Новый родственник'
        ui.label(title).style('font-size:1.4rem;font-weight:900;color:#0088ff;margin-bottom:4px')
        
        n   = ui.input(label='Имя *').props('dark outlined').classes('w-full')
        
        # Умное предзаполнение родителей
        par_val = []
        if parent_id:
            par_val.append(parent_id)
            co_parents = set()
            for p in family_data:
                if parent_id in p.get('parents', []):
                    for pid in p.get('parents', []):
                        if pid != parent_id: co_parents.add(pid)
            if len(co_parents) == 1:
                par_val.append(list(co_parents)[0])
        elif sibling_id:
            sibling = next((p for p in family_data if p['id'] == sibling_id), None)
            if sibling and sibling.get('parents'):
                par_val.extend(sibling['parents'])

        chil_val = [child_id] if child_id else []
        
        par = ui.select({p['id']: p['name'] for p in family_data},
                        label='Родители', multiple=True, clearable=True, value=par_val, with_input=True).props('dark outlined').classes('w-full')
        chil = ui.select({p['id']: p['name'] for p in family_data},
                         label='Дети', multiple=True, clearable=True, value=chil_val, with_input=True).props('dark outlined').classes('w-full')
        bio = ui.textarea(label='Биография').props('dark outlined').classes('w-full')
        photos: list[str] = []

        async def on_up(e):
            os.makedirs(MEDIA_DIR, exist_ok=True)
            if hasattr(e, 'name'):
                name = e.name
                content = e.content.read()
                path = f'{MEDIA_DIR}/{name}'
                with open(path, 'wb') as f: f.write(content)
            else:
                name = e.file.name
                path = f'{MEDIA_DIR}/{name}'
                await e.file.save(path)
            photos.append(path)
            ui.notify(f'📷 {name}', duration=2)

        ui.upload(label='Фото', on_upload=on_up, auto_upload=True, multiple=True).props('dark').classes('w-full')

        def save():
            if not n.value.strip(): ui.notify('Введите имя!', color='negative'); return
            new_id = str(len(family_data)+1)
            p = {'id': new_id, 'name': n.value.strip(),
                 'parents': list(par.value) if par.value else [],
                 'description': bio.value.strip(), 'photos': list(photos)}
            family_data.append(p)

            # Синхронизация детей
            selected_children = list(chil.value) if chil.value else []
            for c_id in selected_children:
                for child in family_data:
                    if child['id'] == c_id:
                        if 'parents' not in child: child['parents'] = []
                        if new_id not in child['parents']: child['parents'].append(new_id)
                        break

            save_data()
            sidebar.refresh(); render_stats.refresh()
            state['selected'] = p['id']
            main_panel.refresh()
            crud_dialog.close()
            ui.notify(f'✅ {p["name"]} добавлен!', color='positive')

        with ui.row().style('width:100%;gap:10px;margin-top:8px'):
            ui.button('Добавить', on_click=save).style(
                'flex:1;background:#0088ff;color:#fff;font-weight:700;border-radius:10px;padding:12px')
            ui.button('Отмена', on_click=crud_dialog.close).props('flat').style(
                'flex:1;border:1px solid rgba(255,255,255,.1);color:#555;border-radius:10px')
    crud_dialog.open()

def open_edit(person: dict):
    m = imap()
    crud_dialog.clear()
    with crud_dialog, ui.card().style(
        'background:#111120;color:#fff;padding:2rem;min-width:480px;max-width:560px;'
        'border:1px solid rgba(0,136,255,.3);border-radius:18px;gap:12px'
    ):
        ui.label(f'Редактировать').style('font-size:1.4rem;font-weight:900;color:#0088ff;margin-bottom:4px')
        n   = ui.input(label='Имя', value=person['name']).props('dark outlined').classes('w-full')
        par = ui.select({p['id']: p['name'] for p in family_data if p['id'] != person['id']},
                        label='Родители', multiple=True, clearable=True,
                        value=person.get('parents',[]), with_input=True).props('dark outlined').classes('w-full')
                        
        curr_children = [p['id'] for p in family_data if person['id'] in p.get('parents', [])]
        chil = ui.select({p['id']: p['name'] for p in family_data if p['id'] != person['id']},
                         label='Дети', multiple=True, clearable=True,
                         value=curr_children, with_input=True).props('dark outlined').classes('w-full')
                         
        bio = ui.textarea(label='Биография', value=person.get('description','')).props('dark outlined').classes('w-full')

        photos = person.get('photos', []).copy()

        photo_container = ui.row().style('gap:10px;flex-wrap:wrap;margin-top:8px')
        def render_photos():
            photo_container.clear()
            with photo_container:
                for idx, ph in enumerate(photos):
                    if os.path.exists(ph):
                        with ui.card().style('padding:0;background:transparent;border:none;position:relative;width:80px;height:80px;border-radius:8px;overflow:hidden'):
                            ui.image(ph).style('width:100%;height:100%;object-fit:cover')
                            def del_ph(i=idx):
                                photos.pop(i)
                                render_photos()
                            ui.button('✖', on_click=del_ph).style(
                                'position:absolute;top:4px;right:4px;width:20px;height:20px;min-height:0;padding:0;'
                                'font-size:10px;background:rgba(255,0,0,0.8);color:white;border-radius:50%;cursor:pointer'
                            ).props('flat')
        render_photos()

        async def on_up(e):
            os.makedirs(MEDIA_DIR, exist_ok=True)
            if hasattr(e, 'name'):
                name = e.name
                content = e.content.read()
                path = f'{MEDIA_DIR}/{name}'
                with open(path, 'wb') as f: f.write(content)
            else:
                name = e.file.name
                path = f'{MEDIA_DIR}/{name}'
                await e.file.save(path)
            photos.append(path)
            render_photos()
            ui.notify(f'📷 {name}', duration=2)

        ui.upload(label='Добавить фото', on_upload=on_up, auto_upload=True, multiple=True).props('dark').classes('w-full')

        def save():
            if not n.value.strip(): ui.notify('Введите имя!', color='negative'); return
            person.update(name=n.value.strip(),
                          parents=list(par.value) if par.value else [],
                          description=bio.value.strip(),
                          photos=photos)
                          
            # Обновляем связи детей
            new_children = list(chil.value) if chil.value else []
            for other in family_data:
                # Если убрали из детей
                if other['id'] in curr_children and other['id'] not in new_children:
                    if person['id'] in other.get('parents', []):
                        other['parents'].remove(person['id'])
                # Если добавили в дети
                if other['id'] not in curr_children and other['id'] in new_children:
                    if 'parents' not in other: other['parents'] = []
                    if person['id'] not in other['parents']:
                        other['parents'].append(person['id'])

            save_data(); sidebar.refresh(); main_panel.refresh()
            ui.notify(f'✅ Сохранено', color='positive'); crud_dialog.close()

        with ui.row().style('width:100%;gap:10px;margin-top:8px'):
            ui.button('Сохранить', on_click=save).style(
                'flex:1;background:#0088ff;color:#fff;font-weight:700;border-radius:10px;padding:12px')
            ui.button('Отмена', on_click=crud_dialog.close).props('flat').style(
                'flex:1;border:1px solid rgba(255,255,255,.1);color:#555;border-radius:10px')
    crud_dialog.open()

def do_delete(person: dict):
    with ui.dialog() as d, ui.card().style(
        'background:#111120;color:#fff;padding:2rem;'
        'border:1px solid rgba(255,68,68,.3);border-radius:18px'
    ):
        ui.label(f'Удалить «{person["name"]}»?').style('font-size:1.1rem;font-weight:700;color:#f55;margin-bottom:8px')
        ui.label('Это действие нельзя отменить.').style('color:#555;margin-bottom:20px')
        def go():
            pid = person['id']
            family_data.remove(person)
            for p in family_data:
                if pid in p.get('parents',[]): p['parents'].remove(pid)
            save_data()
            if state['selected'] == pid: state['selected'] = None
            sidebar.refresh(); main_panel.refresh(); render_stats.refresh()
            ui.notify('Удалён', color='warning'); d.close()
        with ui.row().style('gap:10px'):
            ui.button('Удалить', on_click=go).style('background:#f44;color:#fff;font-weight:700;border-radius:10px;flex:1')
            ui.button('Отмена', on_click=d.close).props('flat').style(
                'border:1px solid rgba(255,255,255,.1);color:#555;border-radius:10px;flex:1')
    d.open()

# ── Мини-карточка связи ────────────────────────────────────
def mini_card(person: dict):
    photo = next((ph for ph in person.get('photos',[]) if os.path.exists(ph)), None)
    with ui.card().style(
        'background:#0d0d1e;border:1px solid rgba(0,136,255,.15);border-radius:12px;'
        'cursor:pointer;padding:12px 16px;align-items:center;gap:8px;min-width:110px;'
    ).classes('hover:!border-[#00ffcc]/50 transition-all').on('click', lambda p=person: select(p['id'])):
        if photo:
            ui.image(photo).style('width:3rem;height:3rem;object-fit:cover;border-radius:50%;border:2px solid rgba(0,136,255,.3)')
        else:
            ui.label(initials(person['name'])).style(
                'width:3rem;height:3rem;border-radius:50%;background:rgba(0,136,255,.15);'
                'color:#0088ff;font-weight:900;font-size:.85rem;display:flex;align-items:center;justify-content:center')
        ui.label(person['name'].split()[0]).style('font-size:.75rem;font-weight:600;color:#ccc;text-align:center')

def select(pid: str):
    state['selected'] = pid
    main_panel.refresh()

# ── Реактивные компоненты ──────────────────────────────────
@ui.refreshable
def render_stats():
    total  = len(family_data)
    roots  = sum(1 for p in family_data if not p.get('parents'))
    leaves = sum(1 for p in family_data if not any(p['id'] in q.get('parents',[]) for q in family_data))
    for val, lbl, color in [(total,'человек','#0088ff'),(roots,'предков','#00ffcc'),(leaves,'потомков','#9b59b6')]:
        with ui.column().style('align-items:center;gap:0'):
            ui.label(str(val)).style(f'font-size:1.4rem;font-weight:900;color:{color};line-height:1')
            ui.label(lbl).style('font-size:.65rem;color:#444;line-height:1')

@ui.refreshable
def sidebar():
    for person in family_data:
        photo   = next((ph for ph in person.get('photos',[]) if os.path.exists(ph)), None)
        is_sel  = state['selected'] == person['id']
        border  = 'rgba(0,255,204,.5)' if is_sel else 'rgba(255,255,255,.04)'
        bg      = '#0e0e22' if is_sel else 'transparent'
        with ui.row().style(
            f'width:100%;align-items:center;gap:12px;padding:10px 12px;border-radius:12px;'
            f'cursor:pointer;border:1px solid {border};background:{bg};transition:all .15s'
        ).classes('hover:!bg-[#0e0e22]').on('click', lambda p=person: select(p['id'])):
            if photo:
                ui.image(photo).style('width:2.5rem;height:2.5rem;object-fit:cover;border-radius:50%;flex-shrink:0')
            else:
                ui.label(initials(person['name'])).style(
                    'width:2.5rem;height:2.5rem;border-radius:50%;background:rgba(0,136,255,.15);'
                    'color:#0088ff;font-weight:900;font-size:.8rem;flex-shrink:0;'
                    'display:flex;align-items:center;justify-content:center;min-width:2.5rem')
            with ui.column().style('gap:1px;overflow:hidden'):
                ui.label(person['name']).style('font-size:.85rem;font-weight:600;color:#e0e0e0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis')
                kids = sum(1 for p in family_data if person['id'] in p.get('parents',[]))
                sub  = f'{kids} дет.' if kids else ('Предок' if not person.get('parents') else '')
                if sub: ui.label(sub).style('font-size:.65rem;color:#444')

@ui.refreshable
def main_panel():
    # Режим «Схема» — SVG-дерево всех людей
    if view_state['mode'] == 'tree':
        if not family_data:
            with ui.column().style('width:100%;align-items:center;justify-content:center;gap:16px;padding:4rem'):
                ui.label('🌳').style('font-size:4rem')
                ui.label('Добавьте первого члена семьи').style('font-size:1.1rem;color:#333')
        else:
            ui.label('СХЕМА СЕМЬИ').style('font-size:.65rem;letter-spacing:.15em;color:#333;margin-bottom:4px')
            ui.label('Цвет рамок и связей зависит от поколения (уровня) в древе').style('font-size:.7rem;color:#2a2a3a;margin-bottom:12px')
            svg = generate_tree_svg(family_data)
            ui.html(f'<div style="width:100%;overflow-x:auto;border-radius:16px">{svg}</div>')
        return

    # Режим «Профиль»
    if not state['selected']:
        with ui.column().style('width:100%;height:100%;align-items:center;justify-content:center;gap:16px'):
            ui.label('🌳').style('font-size:4rem')
            ui.label('Выберите человека').style('font-size:1.2rem;color:#333;font-weight:600')
            ui.label('или добавьте нового').style('font-size:.9rem;color:#2a2a3a')
        return

    m      = imap()
    person = m.get(state['selected'])
    if not person:
        state['selected'] = None; main_panel.refresh(); return

    parents, children, siblings = get_relations(person)
    photo = next((ph for ph in person.get('photos',[]) if os.path.exists(ph)), None)

    def open_photo(path):
        with ui.dialog() as d, ui.card().style('padding:0;background:transparent;border:none;max-width:90vw;max-height:90vh;overflow:hidden;box-shadow:none'):
            ui.image(path).style('max-width:100%;max-height:90vh;object-fit:contain;border-radius:16px')
            ui.button('✖', on_click=d.close).style(
                'position:absolute;top:10px;right:10px;background:rgba(0,0,0,0.5);color:white;'
                'border-radius:50%;width:32px;height:32px;padding:0;min-height:0;cursor:pointer'
            ).props('flat')
        d.open()

    with ui.column().style('width:100%;gap:24px'):

        # ── Профиль ──
        with ui.card().style(
            'width:100%;background:#0b0b1a;border:1px solid rgba(0,136,255,.15);'
            'border-radius:20px;padding:2rem'
        ):
            with ui.row().style('width:100%;align-items:flex-start;gap:24px;flex-wrap:wrap'):
                # Фото или аватар
                if photo:
                    ui.image(photo).style(
                        'width:9rem;height:9rem;object-fit:cover;border-radius:16px;cursor:pointer;'
                        'border:2px solid rgba(0,136,255,.3);flex-shrink:0'
                    ).on('click', lambda: open_photo(photo))
                else:
                    ui.label(initials(person['name'])).style(
                        'width:9rem;height:9rem;border-radius:16px;background:rgba(0,136,255,.1);'
                        'color:#0088ff;font-weight:900;font-size:2rem;flex-shrink:0;'
                        'display:flex;align-items:center;justify-content:center;border:2px solid rgba(0,136,255,.2)')

                with ui.column().style('flex:1;gap:6px;min-width:200px'):
                    ui.label(person['name']).style('font-size:2rem;font-weight:900;color:#fff;line-height:1.1')
                    if parents:
                        ui.label('Родители: ' + ' & '.join(p['name'] for p in parents)).style('color:#0088ff;font-size:.85rem')
                    if person.get('description'):
                        ui.label(person['description']).style('color:#888;font-size:.9rem;line-height:1.6;margin-top:8px')

                with ui.column().style('gap:8px;align-items:flex-end;flex-shrink:0'):
                    ui.button('✏  Изменить', on_click=lambda: open_edit(person)).style(
                        'background:rgba(0,136,255,.15);color:#0088ff;border:1px solid rgba(0,136,255,.3);'
                        'border-radius:10px;padding:8px 16px;font-weight:600;font-size:.85rem')
                    ui.button('🗑  Удалить', on_click=lambda: do_delete(person)).style(
                        'background:rgba(255,68,68,.1);color:#f55;border:1px solid rgba(255,68,68,.25);'
                        'border-radius:10px;padding:8px 16px;font-weight:600;font-size:.85rem')

            # Дополнительные фото
            extra = [ph for ph in person.get('photos',[]) if os.path.exists(ph)]
            if len(extra) > 1:
                ui.separator().style('margin:16px 0;opacity:.1')
                with ui.row().style('gap:10px;flex-wrap:wrap'):
                    for ph in extra:
                        ui.image(ph).style(
                            'width:5rem;height:5rem;object-fit:cover;border-radius:10px;cursor:pointer;'
                            'border:1px solid rgba(255,255,255,.08)'
                        ).on('click', lambda p=ph: open_photo(p))

        # ── Связи ──
        def relation_section(title, people, color, on_add=None):
            if not people and not on_add: return
            with ui.column().style('gap:10px'):
                with ui.row().style('align-items:center;gap:12px'):
                    ui.label(title).style(f'font-size:.65rem;letter-spacing:.15em;color:{color};font-weight:700')
                    if on_add:
                        ui.button('➕ Добавить', on_click=on_add).style(
                            f'font-size:.6rem;padding:2px 8px;border-radius:6px;min-height:0;'
                            f'background:rgba(255,255,255,.05);color:{color};cursor:pointer'
                        ).props('flat')
                if people:
                    with ui.row().style('gap:10px;flex-wrap:wrap'):
                        for p in people: mini_card(p)
                else:
                    ui.label('Пока нет').style('font-size:.8rem;color:#444')

        relation_section('РОДИТЕЛИ',  parents,  '#00ffcc', on_add=lambda: open_add(child_id=person['id']))
        relation_section('ДЕТИ',      children, '#0088ff', on_add=lambda: open_add(parent_id=person['id']))
        relation_section('БРАТЬЯ И СЁСТРЫ', siblings, '#9b59b6', on_add=lambda: open_add(sibling_id=person['id']))

# ── Стили ─────────────────────────────────────────────────
def build_ui():
    ui.dark_mode().enable()
    ui.add_head_html('''
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap" rel="stylesheet">
    <style>
      /* Скрываем сломанные текстовые иконки Material Icons */
      .material-icons {
        color: transparent !important;
        font-size: 0 !important;
        display: none !important;
      }
      
      /* Добавляем свои простые текстовые иконки */
      .q-select__dropdown-icon::after {
        content: "▼";
        font-size: 12px;
        color: #888;
        display: block;
      }
      .q-uploader__title::before {
        content: "➕ ";
        font-size: 14px;
      }
    
      *, *::before, *::after { font-family: "Inter", sans-serif !important; box-sizing: border-box; }
      html, body { background: #08080f !important; margin: 0; padding: 0; overflow: hidden; height: 100vh; }
      ::-webkit-scrollbar { width: 4px; }
      ::-webkit-scrollbar-thumb { background: rgba(0,136,255,.2); border-radius: 4px; }
    </style>
    ''')
    
    # ── Layout ─────────────────────────────────────────────────
    with ui.column().style('width:100%;height:100vh;gap:0;background:#08080f'):
    
        # Шапка
        with ui.row().style(
            'width:100%;align-items:center;padding:12px 24px;gap:20px;flex-shrink:0;'
            'background:#060610;border-bottom:1px solid rgba(255,255,255,.05)'
        ):
            ui.label('🌳 Генеалогическое древо').style('font-size:1.1rem;font-weight:900;color:#fff')
            ui.space()
            render_stats()
            ui.space()
    
        # Тело
        with ui.row().style('flex:1;width:100%;gap:0;overflow:hidden'):
    
            # Сайдбар
            with ui.column().style(
                'width:280px;min-width:280px;height:100%;background:#060610;'
                'border-right:1px solid rgba(255,255,255,.05);gap:0;flex-shrink:0'
            ):
                with ui.row().style('padding:16px;align-items:center;border-bottom:1px solid rgba(255,255,255,.04)'):
                    ui.button('➕ Добавить человека', on_click=lambda: open_add()).style(
                        'background:#0088ff;color:#fff;font-weight:700;border-radius:10px;'
                        'width:100%;height:36px;font-size:.9rem;flex-shrink:0;padding:0')
    
                # Список
                with ui.scroll_area().style('flex:1;width:100%;height:0;flex:1'):
                    with ui.column().style('padding:12px;gap:4px;width:100%'):
                        sidebar()
    
            # Основная панель
            with ui.column().style('flex:1;height:100%;gap:0;overflow:hidden'):
                # Переключатель вид
                with ui.row().style(
                    'padding:10px 28px;gap:8px;border-bottom:1px solid rgba(255,255,255,.04);'
                    'background:#060610;flex-shrink:0'
                ):
                    def _to_profile():
                        view_state['mode'] = 'profile'; main_panel.refresh()
                    def _to_tree():
                        view_state['mode'] = 'tree'; main_panel.refresh()
                    ui.button('👤  Профиль', on_click=_to_profile).style(
                        'font-size:.8rem;font-weight:700;border-radius:8px;padding:6px 14px;'
                        'background:rgba(0,136,255,.15);color:#0088ff;border:1px solid rgba(0,136,255,.3)')
                    ui.button('🌳  Схема', on_click=_to_tree).style(
                        'font-size:.8rem;font-weight:700;border-radius:8px;padding:6px 14px;'
                        'background:rgba(0,255,204,.08);color:#00ffcc;border:1px solid rgba(0,255,204,.2)')
    
                with ui.scroll_area().style('flex:1;width:100%;height:0;flex:1'):
                    with ui.column().style('padding:28px;gap:20px;min-height:100%'):
                        main_panel()
    
