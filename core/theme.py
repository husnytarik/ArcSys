# core/theme.py

"""
Uygulama genel tema ayarları.
Nötr, gri tonlu, açık ve okunaklı bir tema.
Hem Qt hem Leaflet arayüzü tek yerden yönetilir.
"""

THEME = {
    # Font
    "font_main": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    # Çok açık nötr gri arka plan
    "color_bg": "#F3F3F3",  # nötr açık gri
    "color_text": "#1A1A1A",  # koyu gri, saf nötr (siyah değil)
    # Paneller
    "panel_bg": "#FFFFFF",  # beyaz
    "panel_border": "rgba(0, 0, 0, 0.12)",
    "panel_shadow": "0 8px 22px rgba(0, 0, 0, 0.10)",
    # Accent (nötr orta gri — sıfır renk)
    "color_accent": "#5A5A5A",  # tamamen nötr gri
    # Input / filtre
    "filter_bg": "#E5E5E5",  # açık gri
    "filter_border": "rgba(0, 0, 0, 0.18)",
    "filter_placeholder": "rgba(40, 40, 40, 0.50)",
    # Zoom butonları → text rengi gibi
    "zoom_text_color": "#1A1A1A",
    # Layer listesi
    "layer_item_bg": "#F6F6F6",  # nötr gri
    "layer_item_hover_bg": "#E0E0E0",
    "layer_item_drag_bg": "rgba(90, 90, 90, 0.18)",
    # Legend
    "legend_text": "#2A2A2A",
    "legend_header_text": "#0F0F0F",
    "legend_scale_title": "#3A3A3A",
    "legend_z_text": "#6A6A6A",
    # Header
    "header_bg": "#E4E4E4",
    "header_text": "#1A1A1A",
    "header_font_size": 15,
    # Tabs
    "tab_bg": "#E7E7E7",
    "tab_text": "#1F1F1F",
    "tab_selected_bg": "#FFFFFF",
    "tab_selected_text": "#111111",
    # Status bar
    "status_bg": "#E3E3E3",
    "status_text": "#1A1A1A",
    # Progress bar
    "progress_bg": "#D0D0D0",
    "progress_chunk": "#5A5A5A",  # nötr gri accent ile aynı
}


def build_qt_stylesheet() -> str:
    """Qt için genel uygulama stylesheet oluşturur."""
    t = THEME
    return f"""
    QWidget {{
        font-family: {t["font_main"]};
        color: {t["color_text"]};
        background-color: {t["color_bg"]};
    }}

    QLabel#HeaderLabel {{
        background-color: {t["header_bg"]};
        color: {t["header_text"]};
        padding: 8px 12px;
        font-size: {t["header_font_size"]}px;
        font-weight: bold;
    }}

    /* TABLAR */
    QTabWidget::pane {{
        border: 1px solid {t["panel_border"]};
        background: {t["tab_bg"]};
    }}

    QTabBar::tab {{
        background: {t["tab_bg"]};
        color: {t["tab_text"]};
        padding: 6px 12px;
        border: 1px solid {t["panel_border"]};
        border-bottom: none;
        margin-right: 2px;
    }}

    QTabBar::tab:selected {{
        background: {t["tab_selected_bg"]};
        color: {t["tab_selected_text"]};
    }}

    /* STATUS BAR + LOADING */
    QStatusBar {{
        background: {t["status_bg"]};
        color: {t["status_text"]};
    }}

    QProgressBar#LoadingProgressBar {{
        background: {t["progress_bg"]};
        color: {t["status_text"]};
        border: 1px solid {t["panel_border"]};
        border-radius: 4px;
        text-align: center;
        min-height: 12px;
        font-size: 10px;
    }}

    QProgressBar#LoadingProgressBar::chunk {{
        background-color: {t["progress_chunk"]};
    }}

    /* SOLDKİ KATMAN PANELİ TİPİ WIDGET'LAR */

    /* Eğer o panel QGroupBox ise başlık ve gövde */
    QGroupBox {{
        background-color: {t["panel_bg"]};
        border: 1px solid {t["panel_border"]};
        border-radius: 4px;
        margin-top: 6px;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 6px;
        padding: 0 4px;
        color: {t["color_text"]};
        background: transparent;
    }}

    /* QTreeWidget / QTreeView + içindeki viewport'u da boya */
    QTreeWidget, QTreeView {{
        background-color: {t["panel_bg"]};
        alternate-background-color: {t["layer_item_bg"]};
        border: 1px solid {t["panel_border"]};
        show-decoration-selected: 1;
    }}

    QTreeWidget::viewport, QTreeView::viewport {{
        background-color: {t["panel_bg"]};
    }}

    QTreeWidget::item, QTreeView::item {{
        height: 18px;
    }}

    QTreeWidget::item:selected, QTreeView::item:selected {{
        background: {t["layer_item_hover_bg"]};
        color: {t["color_text"]};
    }}

    QTreeWidget::item:hover, QTreeView::item:hover {{
        background: {t["layer_item_hover_bg"]};
    }}
    """


def build_map_css_vars() -> str:
    """Leaflet map_template.html için CSS değişkenleri üretir."""
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
        f"--panel-radius: 2px;",
    ]
    return "\n        ".join(lines)
