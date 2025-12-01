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
    "panel_bg": "#252730",
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
    # MAP TOOLBAR (ÜSTTEKİ ÇUBUK)
    # ======================
    "map_toolbar_bg": "#1C1F24",
    "map_toolbar_border": "#292D37",
    "map_toolbar_text": "#E5E5E7",
    "map_toolbar_button_bg": "#23262F",
    "map_toolbar_button_text": "#E5E5E7",
    "map_toolbar_button_border": "#323542",
    "map_toolbar_button_hover_bg": "#2E3240",
    "map_toolbar_button_pressed_bg": "#252835",
    # ======================
    # FILTER BAR (HARİTA ÜSTÜ)
    # ======================
    # Panel ile content arasında bir ton → bar net seçiliyor
    "filter_bg": "#1E222A",
    "filter_border": "#303541",
    "filter_placeholder": "rgba(230, 231, 236, 0.55)",
    "color_text_muted": "#A0A4AE",
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
    "tab_page_bg": "#14161B",
    "tab_page_border": "#292D37",
    # Sol listeler (Açmalar listesi, Buluntular listesi, rapor listeleri)
    "tab_list_bg": "#181A21",
    "tab_list_border": "#292D37",
    "tab_list_text": "#E5E5F1",
    "tab_list_selected_bg": "#303545",
    "tab_list_selected_text": "#FFFFFF",
    "tab_list_hover_bg": "#252834",
    # Sağ detay alanları (QTextEdit vs.)
    "tab_detail_bg": "#181A21",
    "tab_detail_border": "#292D37",
    "tab_detail_text": "#E5E5F1",
    "tab_detail_placeholder": "#7E828E",
    # Splitter (iki panel arasındaki tutacak çizgi)
    "tab_splitter_handle_bg": "#20232C",
    "tab_splitter_handle_hover_bg": "#2C313D",
    # ======================
    # STATUS / PROGRESS
    # ======================
    "status_bg": "#171921",
    "status_text": "#D6D7E0",
    "progress_bg": "#252A35",
    "progress_chunk": "#91E4CB",
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

    /* TAB ÇUBUĞU VE PANE (üstte sekmeler + altındaki alan) */
    QTabWidget::pane {{
        border: 1px solid {t['tab_page_border']};
        background: {t['tab_page_bg']};
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
    
        /* ==========================
       MAP TOOLBAR (ÜST ÇUBUK)
       ========================== */

    QWidget#MapToolbar {{
        background-color: {t['map_toolbar_bg']};
        border-bottom: 1px solid {t['map_toolbar_border']};
    }}

    QWidget#MapToolbar QPushButton {{
        background-color: {t['map_toolbar_button_bg']};
        color: {t['map_toolbar_button_text']};
        border: 1px solid {t['map_toolbar_button_border']};
        padding: 4px 10px;
        font-size: {t['font_size_normal']}px;
    }}

    QWidget#MapToolbar QPushButton:hover {{
        background-color: {t['map_toolbar_button_hover_bg']};
    }}

    QWidget#MapToolbar QPushButton:pressed {{
        background-color: {t['map_toolbar_button_pressed_bg']};
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
        min-height: 11px;
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
        font-size: 11px;
    }}

    QTreeWidget::item {{
        padding: 4px 6px;
        color: {t['tree_text']};
        border-bottom: 1px solid {t['tree_item_border']};
    }}

    QTreeWidget::item:selected {{
        background: {t['tree_selected_bg']};
        color: {t['tree_text']};
    }}

    QTreeWidget::item:hover {{
        background: rgba(0, 0, 0, 0.04);
    }}

    /* ==========================
       TAB İÇERİKLERİ (LISTE + DETAY)
       ========================== */

    /* QSplitter: sekmeler içindeki bölücü */
    QSplitter {{
        background-color: {t['tab_page_bg']};
    }}

    QSplitter::handle {{
        background-color: {t['tab_splitter_handle_bg']};
    }}

    QSplitter::handle:hover {{
        background-color: {t['tab_splitter_handle_hover_bg']};
    }}

    /* Sol listeler (Açmalar listesi, Buluntular listesi, rapor grupları) */
    QListWidget {{
        background: {t['tab_list_bg']};
        border: 1px solid {t['tab_list_border']};
        color: {t['tab_list_text']};
        outline: none;
    }}

    QListWidget::item {{
        padding: 4px 6px;
    }}

    QListWidget::item:selected {{
        background: {t['tab_list_selected_bg']};
        color: {t['tab_list_selected_text']};
    }}

    QListWidget::item:hover {{
        background: {t['tab_list_hover_bg']};
    }}

    /* Sağ detay alanları (QTextEdit – proje info, açma detay, buluntu detay, rapor metni) */
    QTextEdit {{
        background: {t['tab_detail_bg']};
        border: 1px solid {t['tab_detail_border']};
        color: {t['tab_detail_text']};
        selection-background-color: {t['tab_list_selected_bg']};
        selection-color: {t['tab_list_selected_text']};
    }}

    QTextEdit[placeholderText] {{
        color: {t['tab_detail_placeholder']};
    }}

    /* Proje seçim combobox'ı (üst bilgi alanı) */
    QComboBox#ProjectCombo {{
        background: {t['tab_list_bg']};
        border: 1px solid {t['tab_list_border']};
        color: {t['tab_list_text']};
        padding: 2px 6px;
    }}

    QComboBox#ProjectCombo QAbstractItemView {{
        background: {t['tab_list_bg']};
        border: 1px solid {t['tab_list_border']};
        color: {t['tab_list_text']};
        selection-background-color: {t['tab_list_selected_bg']};
        selection-color: {t['tab_list_selected_text']};
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
        f"--zoom-text-color: {t.get('zoom_text_color', t['color_text'])};",
        f"--layer-item-bg: {t['layer_item_bg']};",
        f"--layer-item-hover-bg: {t['layer_item_hover_bg']};",
        f"--layer-item-drag-bg: {t['layer_item_drag_bg']};",
        f"--legend-text: {t['legend_text']};",
        f"--legend-header-text: {t['legend_header_text']};",
        f"--legend-scale-title: {t['legend_scale_title']};",
        f"--legend-z-text: {t['legend_z_text']};",
        f"--color-text-muted: {t['color_text_muted']};",
    ]
    # map_template.html'de düzgün girintili görünmesi için başına 8 boşluk ekleyelim
    return "\n        ".join(lines)
