
import tkinter as tk
from tkinter import messagebox, ttk

from datetime import datetime
from UI.data_sharing_windows_app import DataSharingWindowsApp


from managers.active_directory_authorization_manager import ActiveDirectoryAuthorizationManager, AuthorizationError



def _show_startup_error(message):
    dialog_root = tk.Tk()
    dialog_root.withdraw()
    try:
        messagebox.showerror("DataSharing", message, parent=dialog_root)
    finally:
        dialog_root.destroy()


def main():
    try:
        ActiveDirectoryAuthorizationManager().ensure_current_user_is_authorized()
    except AuthorizationError as exc:
        _show_startup_error(str(exc))
        return

    app = DataSharingWindowsApp()
    app.run()


if __name__ == "__main__":
    main()