from nicegui import ui
import layout
import importlib
importlib.reload(layout)
layout.build_ui()
ui.run(title="Генеалогическое древо", dark=True, favicon="🌳")
