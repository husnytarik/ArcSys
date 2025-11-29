# core/theme.py

"""
Uygulama genel tema ayarları.
Tek bir yerden hem Qt (QSS) hem de harita (CSS değişkenleri) kontrol edilir.
Nötr, düşük kontrastlı gri tema.
"""

THEME = {
    # Font
    "font_main": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    # Genel arka plan ve metin
    "color_bg": "#D8D8D8",
    "color_text": "#222222",
    # Paneller / kartlar
    "panel_bg": "#F2F2F2",
    "panel_border": "#C8C8C8",  # basit renk, QSS için sorunsuz
    "panel_shadow": "0 6px 16px rgba(0, 0, 0, 0.25)",
    "color_accent": "#3A6EA5",
    # Filtre input (harita)
    "filter_bg": "#F0F0F0",
    "filter_border": "#B8B8B8",
    "filter_placeholder": "rgba(0, 0, 0, 0.45)",
    # Zoom buton metin rengi (harita)
    "zoom_text_color": "#222222",
    # Layer listeleri (harita paneli)
    "layer_item_bg": "#EAEAEA",
    "layer_item_hover_bg": "#E0E0E0",
    "layer_item_drag_bg": "rgba(0, 0, 0, 0.08)",
    # Legend / lejant (harita)
    "legend_text": "#222222",
    "legend_header_text": "#222222",
    "legend_scale_title": "#333333",
    "legend_z_text": "#444444",
    # Header (Qt üst bar)
    "header_bg": "#C0C0C0",
    "header_text": "#222222",
    "header_font_size": 15,
    # Tab widget (Qt)
    "tab_bg": "#D2D2D2",
    "tab_text": "#222222",
    "tab_selected_bg": "#E2E2E2",
    "tab_selected_text": "#000000",
    # Status bar / loading bar (Qt)
    "status_bg": "#C8C8C8",
    "status_text": "#222222",
    "progress_bg": "#E0E0E0",
    "progress_chunk": "#3A6EA5",
    # Sol katman paneli (QTreeWidget)
    "tree_bg": "#E5E5E5",
    "tree_text": "#222222",
    "tree_text_hidden": "#888888",
    "tree_border": "#C6C6C6",
    "tree_selected_bg": "#D0D0D0",
}


def build_qt_stylesheet() -> str:
    """
    Uygulama genel QSS (Qt StyleSheet) üretir.
    MainWindow içinde self.setStyleSheet(...) ile kullanılıyor.
    """
    t = THEME
    return f"""
    QWidget {{
        font-family: {t['font_main']};
        color: {t['color_text']};
        background-color: {t['color_bg']};
    }}

    QLabel#HeaderLabel {{
        background-color: {t['header_bg']};
        color: {t['header_text']};
        padding: 8px 12px;
        font-size: {t['header_font_size']}px;
        font-weight: bold;
    }}

    QTabWidget::pane {{
        border: 1px solid {t['panel_border']};
        background: {t['tab_bg']};
    }}

    QTabBar::tab {{
        background: {t['tab_bg']};
        color: {t['tab_text']};
        padding: 6px 12px;
        border: 1px solid {t['panel_border']};
        border-bottom: none;
        margin-right: 2px;
    }}

    QTabBar::tab:selected {{
        background: {t['tab_selected_bg']};
        color: {t['tab_selected_text']};
    }}

    QStatusBar {{
        background: {t['status_bg']};
        color: {t['status_text']};
    }}

    QProgressBar#LoadingProgressBar {{
        background: {t['progress_bg']};
        color: {t['status_text']};
        border: 1px solid {t['panel_border']};
        border-radius: 4px;
        text-align: center;
        min-height: 12px;
        font-size: 10px;
    }}

    QProgressBar#LoadingProgressBar::chunk {{
        background-color: {t['progress_chunk']};
    }}

    /* Sol katman paneli (QTreeWidget) */
    QTreeWidget {{
        background: {t['tree_bg']};
        border: 1px solid {t['tree_border']};
        color: {t['tree_text']};
        font-size: 12px;
    }}

    QTreeWidget::item {{
        padding: 4px 6px;
        color: {t['tree_text']};
    }}

    QTreeWidget::item:selected {{
        background: {t['tree_selected_bg']};
        color: {t['tree_text']};
    }}

    QTreeWidget::item:hover {{
        background: rgba(0, 0, 0, 0.04);
    }}
    """


def build_map_css_vars() -> str:
    """
    map_template.html içindeki :root bloğu için CSS değişkenleri üretir.
    __THEME_CSS_VARS__ placeholder'ına basılacak.
    """
    t = THEME
    lines = [
        f"--font-main: {t['font_main']};",
        f"--color-bg: {t['color_bg']};",
        f"--color-text: {t['color_text']};",
        f"--panel-bg: {t['panel_bg']};",
        f"--panel-border: {t['panel_border']};",
        f"--panel-shadow: {t['panel_shadow']};",
        f"--color-accent: {t['color_accent']};",
        f"--filter-bg: {t['filter_bg']};",
        f"--filter-border: {t['filter_border']};",
        f"--filter-placeholder: {t['filter_placeholder']};",
        f"--zoom-text-color: {t['zoom_text_color']};",
        f"--layer-item-bg: {t['layer_item_bg']};",
        f"--layer-item-hover-bg: {t['layer_item_hover_bg']};",
        f"--layer-item-drag-bg: {t['layer_item_drag_bg']};",
        f"--legend-text: {t['legend_text']};",
        f"--legend-header-text: {t['legend_header_text']};",
        f"--legend-scale-title: {t['legend_scale_title']};",
        f"--legend-z-text: {t['legend_z_text']};",
    ]
    # map_template.html'de düzgün girintili görünmesi için başına 8 boşluk ekleyelim
    return "\n        ".join(lines)
