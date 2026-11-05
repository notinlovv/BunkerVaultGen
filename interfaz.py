"""Compatibility wrapper redirecting legacy entry point to the modern application."""

import main


def crear_ventana() -> None:
    """Launches the modern Zero-Knowledge password manager application."""
    main.main()


if __name__ == "__main__":
    main.main()
