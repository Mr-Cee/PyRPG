import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UILabel, UIButton, UITextBox, UIScrollingContainer
from datetime import datetime

class MyReportsWindow(UIWindow):
    def __init__(self, manager, reports, player_name):
        super().__init__(pygame.Rect(100, 100, 600, 400), manager, window_display_title="My Reports")
        self.reports = reports
        self.player_name = player_name

        self.scroll_container = UIScrollingContainer(
            pygame.Rect(10, 10, 580, 340), self, manager
        )

        self.scroll_container.set_scrollable_area_dimensions((550, max(len(self.reports) * 120, 340)))

        self.labels = []
        y = 0
        for report in self.reports:
            timestamp_str = datetime.fromtimestamp(report['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
            status = "Resolved" if report['status'] == "resolved" else "Open"
            resolution = report.get("resolution") or "(No resolution provided)"

            message = (
                f"Case #{report['case_number']}\n"
                f"Sent: {timestamp_str}\n"
                f"Message: {report['message']}\n"
                f"Status: {status}\n"
                f"Resolution: {resolution}"
            )

            label = UITextBox(message, pygame.Rect(0, y, 530, 110), self.scroll_container, manager)
            self.labels.append(label)
            y += 120

        self.close_button = UIButton(
            relative_rect=pygame.Rect((500, 360), (80, 30)),
            text='Close',
            manager=manager,
            container=self,
            object_id="#close_my_reports"
        )

    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_object_id == "#close_my_reports":
                self.kill()
                return True
        return super().process_event(event)
