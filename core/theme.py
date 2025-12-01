# core/theme.py

"""
Uygulama genel tema ayarları.
Tek bir yerden hem Qt (QSS) hem de harita (CSS değişkenleri) kontrol edilir.
Nötr, düşük kontrastlı gri tema.
"""

THEME = {
    # ======================
    # FONT
    # ======================
    "font_main": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    "font_size_small": 10,
    "font_size_normal": 11,
    "font_size_large": 13,
    # ======================
    # GLOBAL BACKGROUND & TEXT
    # ======================
    # Çok koyu ama saf siyah değil, hafif mavi alt tonlu
    "color_bg": "#101116",
    # Ana metin: yumuşak beyaz
    "color_text": "#ECECF1",
    # İkincil metin: grimsi, göz yormayan
    "color_text_muted": "#9DA0AA",
    # ======================
    # PANEL HIERARCHY
    # ======================
    # HEADER (en üst bar)
    "header_bg": "#181B22",
    "header_text": "#F1F1F5",
    "header_font_size": 12,
    "header_border": "#262A32",
    # ANA PANELLER (sol panel, alt panel vs.)
    # İçerikten bir ton açık, header’dan bir tık koyu → doğal ayrım
    "panel_bg": "#171920",
    "panel_border": "#2A2E38",
    "panel_shadow": "0 4px 16px rgba(0, 0, 0, 0.55)",
    "panel_radius": 8,
    # CONTENT (harita / orta alan)
    "content_bg": "#0D0F14",
    # ======================
    # BUTTON / TOOLBAR
    # ======================
    # Mat, hafif kömür gri butonlar
    "button_bg": "#262A33",
    "button_bg_hover": "#303642",
    "button_bg_pressed": "#1E2229",
    "button_text": "#F4F4F7",
    "button_border": "#343A45",
    # Map toolbar özel
    "toolbar_bg": "#1B1E26",  # header’dan çok az koyu
    "toolbar_border": "#292E38",
    "toolbar_text": "#E6E7EC",
    # ======================
    # FILTER BAR (HARİTA ÜSTÜ)
    # ======================
    # Panel ile content arasında bir ton → bar net seçiliyor
    "filter_bg": "#1E222A",
    "filter_border": "#303541",
    "filter_placeholder": "rgba(230, 231, 236, 0.55)",
    # ======================
    # LAYERS (HARİTA KATMAN LİSTESİ)
    # ======================
    "layer_item_bg": "#20232B",
    "layer_item_hover_bg": "#2A2F39",
    "layer_item_drag_bg": "rgba(255, 255, 255, 0.09)",
    # ======================
    # TREE (SOL KATMAN PANELİ)
    # ======================
    "tree_bg": "#181A21",
    "tree_item_bg": "#1E2027",  # ← NORMAL item arka planı (YENİ)
    "tree_text": "#ECECF1",
    "tree_text_hidden": "#7E828E",
    "tree_border": "#292D37",
    "tree_selected_bg": "#303545",
    "tree_item_hover_bg": "#262A33",
    "tree_item_border": "#262A33",  # item kenarlığı
    "tree_item_border_thin": "1px solid",  # border kalınlığı/stili
    "tree_item_border_bottom": "1px solid #262A33",
    # ======================
    # LEGEND
    # ======================
    "legend_text": "#ECECF1",
    "legend_header_text": "#F8F8FB",
    "legend_scale_title": "#C4C7D2",
    "legend_z_text": "#A5A8B3",
    # ======================
    # TABS (Qt)
    # ======================
    "tab_bg": "#191C23",
    "tab_text": "#DADBE3",
    "tab_selected_bg": "#252A35",
    "tab_selected_text": "#FFFFFF",
    # ======================
    # STATUS / PROGRESS
    # ======================
    "status_bg": "#171921",
    "status_text": "#D6D7E0",
    "progress_bg": "#252A35",
    "progress_chunk": "#4E86D2",
    # ======================
    # ACCENT & ÖZEL
    # ======================
    # Hafif doygun, tok mavi
    "color_accent": "#EDEEF5",
    "color_accent_soft": "#303541",  # %26 opacity
    "zoom_text_color": "#EDEEF5",
    # ======================
    # SPLITTER & SCROLLBAR
    # ======================
    "splitter_handle": "#2B303A",
    "splitter_border": "#161821",
    "scrollbar_bg": "#151720",
    "scrollbar_handle": "#313543",
    "scrollbar_handle_hover": "#3A4050",
}


def build_qt_stylesheet() -> str:
    """
    Uygulama genel QSS (Qt StyleSheet) üretir.
    MainWindow içinde self.setStyleSheet(...) ile kullanılıyor.
    """
    t = THEME
    return f"""
    /* =======================
       GLOBAL
       ======================= */
    QWidget {{
        font-family: {t['font_main']};
        color: {t['color_text']};
        background-color: {t['color_bg']};
        font-size: {t['font_size_normal']}px;
    }}

    /* Ana header label'i */
    QLabel#HeaderLabel {{
        background-color: {t['header_bg']};
        color: {t['header_text']};
        padding: 8px 12px;
        font-size: {t['header_font_size']}px;
        font-weight: bold;
        border-bottom: 1px solid {t['header_border']};
    }}

    /* =======================
       TABS
       ======================= */
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

    /* =======================
       STATUS BAR & PROGRESS
       ======================= */
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

    /* =======================
       GENEL BUTONLAR
       ======================= */
    QPushButton {{
        background-color: {t['button_bg']};
        color: {t['button_text']};
        border: 1px solid {t['button_border']};
        border-radius: 4px;
        padding: 4px 10px;
    }}

    QPushButton:hover {{
        background-color: {t['button_bg_hover']};
    }}

    QPushButton:pressed {{
        background-color: {t['button_bg_pressed']};
    }}

    QPushButton:disabled {{
        background-color: {t['panel_bg']};
        color: {t['color_text_muted']};
        border-color: {t['panel_border']};
    }}

    /* Map toolbar özel – istersen ayrı renklendirebilirsin */
    QWidget#MapToolbar {{
        background-color: {t['toolbar_bg']};
        border-bottom: 1px solid {t['toolbar_border']};
    }}

    QPushButton#MapToolbarButtonOffline,
    QPushButton#MapToolbarButtonGeotiff {{
        font-size: {t['font_size_small']}px;
    }}

    /* =======================
       MAP PANEL & LAYER TREE
       ======================= */
    QWidget#MapPanel {{
        background-color: {t['content_bg']};
    }}

    QTreeWidget#MapLayersTree {{
        background: {t['tree_bg']};
        border: 1px solid {t['tree_border']};
        color: {t['tree_text']};
        font-size: {t['font_size_normal']}px;
    }}

    QTreeWidget#MapLayersTree::item {{
        background: {t['tree_item_bg']};
        padding: 6px 8px;
        color: {t['tree_text']};
        border-bottom: 1px solid {t['tree_item_border']};
    }}
 
    QTreeWidget#MapLayersTree::item:selected {{
        background: {t['tree_selected_bg']};  /* ← Seçili BG */
        color: {t['tree_text']};
    }}

    QTreeWidget#MapLayersTree::item:hover {{
        background: {t['tree_item_hover_bg']};  /* ← Hover BG */
    }}

    /* Web harita görünümü */
    QWebEngineView#MapWebView {{
        background: {t['content_bg']};
        border-left: 1px solid {t['panel_border']};
    }}

    /* Splitter */
    QSplitter#MapSplitter::handle {{
        background: {t['splitter_handle']};
        width: 5px;
        margin: 0;
    }}

    QSplitter#MapSplitter::handle:hover {{
        background: {t['button_bg_hover']};
    }}

    /* =======================
       SCROLLBARS
       ======================= */
    QScrollBar:vertical {{
        background: {t['scrollbar_bg']};
        width: 12px;
        margin: 0;
    }}

    QScrollBar::handle:vertical {{
        background: {t['scrollbar_handle']};
        min-height: 20px;
        border-radius: 6px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {t['scrollbar_handle_hover']};
    }}

    QScrollBar:horizontal {{
        background: {t['scrollbar_bg']};
        height: 12px;
        margin: 0;
    }}

    QScrollBar::handle:horizontal {{
        background: {t['scrollbar_handle']};
        min-width: 20px;
        border-radius: 6px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background: {t['scrollbar_handle_hover']};
    }}

    QScrollBar::add-line, QScrollBar::sub-line {{
        background: transparent;
        border: none;
        width: 0;
        height: 0;
    }}
        /* =======================
       ÜST BAR (HEADER BÖLÜMÜ)
       ======================= */
    QWidget#TopBar {{
        background-color: {t['tab_bg']};                  /* Tab zeminine uyumlu */
        border-bottom: 1px solid {t['tree_item_border']}; /* Aşağı ince çizgi */
    }}

    QLabel#HeaderLabel {{
        background: transparent;                          /* Ayrı bir kutu gibi durmasın */
        color: {t['header_text']};
        font-size: {t['header_font_size']}px;
        font-weight: bold;
    }}
    /* Proje combobox – çukur değil, düz kart gibi */
    QComboBox#ProjectCombo {{
        background-color: {t['tab_bg']};
        color: {t['color_text']};
        border: 1px solid {t['tree_item_border']};
        border-radius: 4px;
        padding: 2px 8px;
    }}

    QComboBox#ProjectCombo::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: right center;
        width: 18px;
        border-left: 1px solid {t['tree_item_border']};
        background: {t['tab_bg']};
    }}

    QComboBox#ProjectCombo::down-arrow {{
        image: none;  /* default ikon yok, sadece küçük alan */
        width: 0;
        height: 0;
        margin-right: 0;
    }}

    QComboBox#ProjectCombo:on,
    QComboBox#ProjectCombo:focus {{
        border: 1px solid {t['color_accent']};
        outline: none;
    }}

    QComboBox QAbstractItemView {{
        background-color: {t['panel_bg']};
        border: 1px solid {t['panel_border']};
        color: {t['color_text']};
        selection-background-color: {t['tree_selected_bg']};
        selection-color: {t['color_text']};
    }}

    """


def build_map_css_vars() -> str:
    """
    map_template.html içindeki :root bloğu için CSS değişkenleri üretir.
    __THEME_CSS_VARS__ placeholder'ına basılacak.
    """
    t = THEME
    lines = [
        # Font & temel
        f"--font-main: {t['font_main']};",
        f"--color-bg: {t['color_bg']};",
        f"--color-text: {t['color_text']};",
        f"--color-text-muted: {t['color_text_muted']};",
        # Panel & kartlar
        f"--panel-bg: {t['panel_bg']};",
        f"--panel-border: {t['panel_border']};",
        f"--panel-shadow: {t['panel_shadow']};",
        f"--panel-radius: {t['panel_radius']}px;",
        # Accent
        f"--color-accent: {t['color_accent']};",
        f"--color-accent-soft: {t['color_accent_soft']};",
        # Filter bar
        f"--filter-bg: {t['filter_bg']};",
        f"--filter-border: {t['filter_border']};",
        f"--filter-placeholder: {t['filter_placeholder']};",
        # Zoom text (harita sağ alt kısım vs.)
        f"--zoom-text-color: {t['zoom_text_color']};",
        # Layer list
        f"--layer-item-bg: {t['layer_item_bg']};",
        f"--layer-item-hover-bg: {t['layer_item_hover_bg']};",
        f"--layer-item-drag-bg: {t['layer_item_drag_bg']};",
        # Legend
        f"--legend-text: {t['legend_text']};",
        f"--legend-header-text: {t['legend_header_text']};",
        f"--legend-scale-title: {t['legend_scale_title']};",
        f"--legend-z-text: {t['legend_z_text']};",
    ]
    # map_template.html'de düzgün girintili görünmesi için başına 8 boşluk ekleyelim
    return "\n        ".join(lines)
