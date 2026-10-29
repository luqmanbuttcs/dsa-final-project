"""Application entry point."""
import sys

from PyQt6.QtWidgets import QApplication

from ui import SolitaireWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Klondike Solitaire - DSA Project")
    window = SolitaireWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
