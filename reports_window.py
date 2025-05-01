import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UITextBox, UIScrollingContainer

class ReportsWindow(UIWindow):
    def __init__(self, manager, reports, width=500, height=400):
        super().__init__(
            pygame.Rect((100, 100), (width, height)),
            manager,
            window_display_title="Open Reports",
            object_id="#reports_window"
        )

        self.scroll_container = UIScrollingContainer(
            pygame.Rect(10, 10, width - 20, height - 20),
            manager=manager,
            container=self,
        )

        y_offset = 0
        for report in reports:
            case_id = report.get("id", "???")
            sender = report.get("sender", "???")
            timestamp = report.get("timestamp", "")
            message = report.get("message", "")

            report_text = f"<b>Case #{case_id}</b> - {timestamp}<br><b>{sender}</b>: {message}<br><br>"

            UITextBox(
                html_text=report_text,
                relative_rect=pygame.Rect(0, y_offset, width - 40, 100),
                manager=manager,
                container=self.scroll_container
            )

            y_offset += 110

        self.scroll_container.set_scrollable_area_dimensions((width - 40, y_offset + 10))
