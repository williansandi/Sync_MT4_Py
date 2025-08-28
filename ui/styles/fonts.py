# ui/styles/fonts.py
class AppFonts:
    def __init__(self, font_family="Arial"):
        self.FAMILY = font_family
        
        self.HEADER_TITLE = (self.FAMILY, 20, "bold")
        self.PAGE_TITLE = (self.FAMILY, 18, "bold")
        self.CARD_TITLE = (self.FAMILY, 11, "bold")
        self.CARD_VALUE = (self.FAMILY, 24, "bold")
        self.CARD_SUBTITLE = (self.FAMILY, 11)
        self.SIDEBAR_LOGO = (self.FAMILY, 20, "bold")
        self.SIDEBAR_BUTTON = (self.FAMILY, 14, "bold")
        self.BUTTON = (self.FAMILY, 12, "bold")
        self.BODY_NORMAL = (self.FAMILY, 14, "normal")
        self.BODY_BOLD = (self.FAMILY, 14, "bold")
        self.BODY_SMALL = (self.FAMILY, 12, "normal")
        self.CONSOLE = ("Consolas", 12)