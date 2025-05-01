import pygame
import pygame_gui
import requests
from pygame_gui.elements import UIWindow, UIButton, UITextBox, UILabel, UITextEntryLine
from pygame_gui.core import UIContainer
from pygame import Rect
from settings import *

  # Adjust as needed

class ReportsWindow(UIWindow):
    def __init__(self, manager, reports, chat_window):
        super().__init__(Rect((100, 100), (600, 400)), manager, window_display_title="Reports Viewer")
        self.chat_window = chat_window
        self.manager = manager
        self.panel = UIContainer(Rect(10, 10, 580, 380), manager=manager, container=self)
        self.reports = reports
        self.y_offset = 0

        for report in reports:
            self.add_report_entry(report)

    def add_report_entry(self, report):
        report_id = report.get("id", "?")
        sender = report.get("sender", "?")
        message = report.get("message", "?")
        timestamp = report.get("timestamp", "?")

        report_text = f"Case #{report_id}\nFrom: {sender}\nTime: {timestamp}\nMessage: {message}"

        UITextBox(
            html_text=report_text,
            relative_rect=Rect(10, self.y_offset, 450, 60),
            manager=self.manager,
            container=self.panel
        )

        resolve_button = UIButton(
            relative_rect=Rect(470, self.y_offset + 15, 100, 30),
            text="Resolve",
            manager=self.manager,
            container=self.panel,
            object_id=f"resolve_button_{report_id}"
        )

        print(resolve_button.get_object_ids())

        self.y_offset += 80

    def process_event(self, event):

        handled = super().process_event(event)
        if event.type == pygame_gui.UI_BUTTON_PRESSED:

            if event.ui_object_id == "resolution_submit":
                print("test submit")

            for part in event.ui_object_id.split("."):
                if part.startswith("resolve_button_"):
                    case_id = int(part.split("_")[-1])
                    if not getattr(self.chat_window, "resolution_popup", None):
                        popup = ResolutionPopup(self.manager, case_id, self.chat_window)
                        self.chat_window.resolution_popup = popup
                    break
        return handled

    def kill(self):
        if hasattr(self.chat_window, "reports_window"):
            self.chat_window.reports_window = None
        super().kill()

class ResolutionPopup(UIWindow):

    def __init__(self, manager, report_id, chat_window):
        super().__init__(pygame.Rect((300, 300), (400, 180)), manager, window_display_title=f"Resolve Case #{report_id}")
        self.manager = manager
        self.report_id = report_id
        self.chat_window = chat_window

        UILabel(Rect(10, 10, 380, 30), f"Resolution for Case #{report_id}:", manager=manager, container=self)
        self.entry = UITextEntryLine(Rect(10, 50, 380, 30), manager=manager, container=self)
        self.submit_button = UIButton(Rect(150, 100, 100, 30), "Submit", manager=manager, container=self, object_id="resolution_submit")

    def process_event(self, event):
        handled = super().process_event(event)
        if event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.submit_button:
            message = self.entry.get_text().strip()
            if message:
                try:
                    response = requests.post(f"{SERVER_URL}/report_resolve", json={
                        "case_id": self.report_id,
                        "resolution": message
                    }, timeout=5)
                    data = response.json()
                    if data.get("success"):
                        self.chat_window.log_message(f"[Resolved] {data.get('message')}", "Admin")
                    else:
                        self.chat_window.log_message(f"[Admin] {data.get('error')}", "System")
                except Exception:
                    self.chat_window.log_message("[Error] Could not contact server.", "System")
            self.kill()  # <- This is enough
        return handled

    def kill(self):
        if hasattr(self.chat_window, "resolution_popup"):
            self.chat_window.resolution_popup = None
        super().kill()
