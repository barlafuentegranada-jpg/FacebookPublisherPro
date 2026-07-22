from app.ui.theme import colors, fonts


class Spacing:
    XS = 3
    SM = 6
    MD = 10
    LG = 12
    XL = 14
    XXL = 16
    SECTION = 20
    PAGE = 24


class Radius:
    NONE = 0
    SM = 6
    MD = 8
    LG = 10


class Padding:
    FRAME_X = 16
    FRAME_Y = 12
    PAGE_X = 24
    PAGE_Y = 24
    CONTROL_X = 12
    CONTROL_Y = 8


BUTTON_HEIGHT = 38
INPUT_HEIGHT = 38
STATUS_BAR_HEIGHT = 34
BORDER_WIDTH = 1
ROW_HEIGHT = 42
SIDEBAR_WIDTH = 230
MIN_WINDOW_WIDTH = 1100
MIN_WINDOW_HEIGHT = 700
WINDOW_WIDTH = 1500
WINDOW_HEIGHT = 900
CARD_RADIUS = Radius.MD

GROUP_TABLE_COLUMNS = [
    ("selected", 56),
    ("name", 320),
    ("members", 120),
    ("privacy", 110),
    ("category", 150),
    ("last_scan", 160),
    ("status", 120),
]


PRIMARY_BUTTON = {
    "height": BUTTON_HEIGHT,
    "corner_radius": Radius.SM,
    "font": fonts.BODY_BOLD,
    "fg_color": colors.PRIMARY,
    "hover_color": colors.PRIMARY_HOVER,
    "text_color": colors.TEXT_ON_ACCENT,
}

SECONDARY_BUTTON = {
    "height": BUTTON_HEIGHT,
    "corner_radius": Radius.SM,
    "font": fonts.BODY_BOLD,
    "fg_color": colors.SECONDARY,
    "hover_color": colors.SECONDARY_HOVER,
    "text_color": colors.TEXT,
}

DANGER_BUTTON = {
    "height": BUTTON_HEIGHT,
    "corner_radius": Radius.SM,
    "font": fonts.BODY_BOLD,
    "fg_color": colors.DANGER,
    "hover_color": colors.DANGER_HOVER,
    "text_color": colors.TEXT_ON_ACCENT,
}

NAV_BUTTON = {
    "height": BUTTON_HEIGHT,
    "corner_radius": Radius.SM,
    "font": fonts.BODY_BOLD,
    "fg_color": colors.TRANSPARENT,
    "hover_color": colors.SECONDARY_HOVER,
    "text_color": colors.TEXT,
}

NAV_BUTTON_ACTIVE = {
    "fg_color": colors.SURFACE_ACTIVE,
    "text_color": colors.TEXT,
}

NAV_BUTTON_INACTIVE = {
    "fg_color": colors.TRANSPARENT,
    "text_color": colors.TEXT,
}

SEARCH_BOX = {
    "height": INPUT_HEIGHT,
    "corner_radius": Radius.SM,
    "border_color": colors.BORDER,
    "fg_color": colors.SURFACE,
    "text_color": colors.TEXT,
    "placeholder_text_color": colors.TEXT_MUTED,
}

TEXT_INPUT = SEARCH_BOX.copy()

SELECT_BOX = {
    "height": INPUT_HEIGHT,
    "corner_radius": Radius.SM,
    "font": fonts.BODY,
    "fg_color": colors.SURFACE,
    "button_color": colors.SECONDARY,
    "button_hover_color": colors.SECONDARY_HOVER,
    "text_color": colors.TEXT,
    "dropdown_fg_color": colors.SURFACE,
    "dropdown_hover_color": colors.SECONDARY_HOVER,
    "dropdown_text_color": colors.TEXT,
}

CHECKBOX = {
    "corner_radius": Radius.SM,
    "font": fonts.BODY,
    "fg_color": colors.PRIMARY,
    "hover_color": colors.PRIMARY_HOVER,
    "border_color": colors.BORDER,
    "text_color": colors.TEXT,
}

SECTION_PANEL = {
    "corner_radius": Radius.MD,
    "fg_color": colors.SURFACE,
    "border_color": colors.BORDER,
    "border_width": BORDER_WIDTH,
}

TABLE_ROW = {
    "height": ROW_HEIGHT,
    "corner_radius": Radius.SM,
    "fg_color": colors.SURFACE,
}

TABLE_ROW_HIGHLIGHT = {
    "fg_color": colors.SURFACE_ACTIVE,
}

STATUS_BADGES = {
    "success": {
        "fg_color": colors.SUCCESS_SURFACE,
        "text_color": colors.SUCCESS,
    },
    "warning": {
        "fg_color": colors.WARNING_SURFACE,
        "text_color": colors.WARNING,
    },
    "danger": {
        "fg_color": colors.ERROR_SURFACE,
        "text_color": colors.ERROR,
    },
    "info": {
        "fg_color": colors.INFO_SURFACE,
        "text_color": colors.INFO,
    },
    "neutral": {
        "fg_color": colors.SURFACE_MUTED,
        "text_color": colors.TEXT_MUTED,
    },
}
