import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.gui.main_window import MainWindow


class DocumentNavigationTests(unittest.TestCase):
    def test_attention_title_uses_correct_singular_and_plural(self):
        self.assertEqual(
            MainWindow._attention_title(1),
            "1 Dokument braucht deine Aufmerksamkeit",
        )
        self.assertEqual(
            MainWindow._attention_title(2),
            "2 Dokumente brauchen deine Aufmerksamkeit",
        )

    def test_attention_prefers_manual_review_then_errors(self):
        self.assertEqual(
            MainWindow._attention_tab({"manual": 1, "error": 4}),
            "Zu prüfen",
        )
        self.assertEqual(
            MainWindow._attention_tab({"manual": 0, "error": 1}),
            "Fehler",
        )
        self.assertEqual(
            MainWindow._attention_tab({"manual": 0, "error": 0}),
            "Neu",
        )

    def test_folder_change_refreshes_overview_and_document_lists(self):
        class Window:
            def __init__(self):
                self.overview_refreshes = 0
                self.document_refreshes = 0

            def _refresh_overview_stats(self):
                self.overview_refreshes += 1

            def _refresh_document_lists(self):
                self.document_refreshes += 1

        window = Window()

        MainWindow._refresh_changed_document_views(window)

        self.assertEqual(window.overview_refreshes, 1)
        self.assertEqual(window.document_refreshes, 1)

    def test_overview_only_says_everything_is_done_when_all_queues_are_empty(self):
        title, _subtitle, count = MainWindow._overview_summary(
            {"incoming": 27, "manual": 0, "error": 0}
        )
        self.assertEqual(title, "27 Dokumente warten auf Verarbeitung")
        self.assertEqual(count, 27)

        title, _subtitle, count = MainWindow._overview_summary(
            {"incoming": 0, "manual": 0, "error": 0}
        )
        self.assertEqual(title, "Alles erledigt")
        self.assertEqual(count, 0)

    def test_live_status_prioritizes_processing_configuration_and_documents(self):
        decide = MainWindow._live_status_decision
        self.assertEqual(decide(True, 1, 2, 0, ["Fehler"])[1], "running")
        self.assertEqual(decide(False, 1, 2, 0, ["Fehler"])[1], "configuration")
        self.assertEqual(decide(False, 1, 2, 0, [])[1], "attention")
        self.assertEqual(decide(False, 1, 0, 0, [])[1], "incoming")
        self.assertEqual(decide(False, 0, 0, 0, [])[0], "Sorterino ist einsatzbereit")

    def test_additional_single_documents_are_queued_once(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first = Path(temp_dir) / "eins.pdf"
            second = Path(temp_dir) / "zwei.pdf"
            first.write_bytes(b"1")
            second.write_bytes(b"2")

            class Window:
                _same_document_path = staticmethod(MainWindow._same_document_path)
                _single_queue_position = MainWindow._single_queue_position
                _processing_status_text = MainWindow._processing_status_text
                _run_single_document = MainWindow._run_single_document

                def __init__(self):
                    self._thread_running = True
                    self._active_single_document = first
                    self._single_document_queue = []
                    self._document_snapshot = None
                    self.refreshes = 0

                def _refresh_document_lists(self):
                    self.refreshes += 1

                def _set_live_status(self, *_args):
                    pass

                def _start_next_single_document(self):
                    pass

            window = Window()
            window._run_single_document(second)
            window._run_single_document(second)

            self.assertEqual(window._single_document_queue, [second])
            self.assertEqual(window._single_queue_position(second), 1)
            self.assertEqual(window.refreshes, 1)
            self.assertEqual(
                window._processing_status_text(),
                "Verarbeite eins.pdf · 1 in Warteschlange",
            )

    def test_path_comparison_handles_equivalent_document_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "Dokument.pdf"
            path.write_bytes(b"pdf")
            equivalent = path.parent / "." / path.name
            self.assertTrue(MainWindow._same_document_path(path, equivalent))
            self.assertFalse(MainWindow._same_document_path(path, path.parent / "anderes.pdf"))

    def test_new_document_row_keeps_open_process_and_discard_actions(self):
        created_buttons = []

        class Widget:
            def __init__(self, master=None, text="", **_kwargs):
                self.master = master
                self.text = text
                self.children = []
                if master is not None:
                    master.children.append(self)

            def pack(self, **_kwargs):
                return None

            def configure(self, **kwargs):
                self.text = kwargs.get("text", self.text)

            def winfo_children(self):
                return list(self.children)

            def destroy(self):
                pass

        class Button(Widget):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                created_buttons.append(self)

        class Window:
            TEXT_COLOR = "black"
            SIDEBAR_HOVER = "gray"
            _active_single_document = None
            _single_document_queue = []
            config = SimpleNamespace()
            _same_document_path = staticmethod(MainWindow._same_document_path)
            _single_queue_position = MainWindow._single_queue_position

            @staticmethod
            def _files(_folder):
                return [Path("Dokument.pdf")]

            def _run_single_document(self, *_args):
                pass

            def _open_path(self, *_args):
                pass

            def _discard_incoming_document(self, *_args):
                pass

        mail_state = SimpleNamespace(file_info=lambda _path: None)
        with (
            patch("src.gui.main_window.ctk.CTkFrame", Widget),
            patch("src.gui.main_window.ctk.CTkLabel", Widget),
            patch("src.gui.main_window.ctk.CTkButton", Button),
            patch("src.mail_fetcher.MailImportState", return_value=mail_state),
        ):
            MainWindow._populate_file_list(Window(), Widget(), Path("."), "leer")

        self.assertEqual(
            {button.text for button in created_buttons},
            {"Verarbeiten", "Öffnen", "Verwerfen"},
        )

        created_buttons.clear()

        class ActiveWindow(Window):
            _active_single_document = Path("Dokument.pdf")

        with (
            patch("src.gui.main_window.ctk.CTkFrame", Widget),
            patch("src.gui.main_window.ctk.CTkLabel", Widget),
            patch("src.gui.main_window.ctk.CTkButton", Button),
            patch("src.mail_fetcher.MailImportState", return_value=mail_state),
        ):
            MainWindow._populate_file_list(
                ActiveWindow(), Widget(), Path("."), "leer"
            )

        self.assertEqual(
            {button.text for button in created_buttons},
            {"Öffnen", "Verwerfen"},
        )


if __name__ == "__main__":
    unittest.main()
