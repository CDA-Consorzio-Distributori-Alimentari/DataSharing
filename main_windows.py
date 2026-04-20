import os
import sys
import shutil

RELEASE_DIR = r"\\192.168.105.200\DataSharing\release"
LOCAL_VERSION_PATH = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "VERSION")
REMOTE_VERSION_PATH = os.path.join(RELEASE_DIR, "VERSION")
FILES_TO_UPDATE = ["datasharing.exe", "datasharing_windows.exe", "config.json", "config.template.json", "GUIDA_UTENTE_DATASHARING.md", "VERSION"]

def check_and_update_from_release():
    current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    if os.path.normcase(os.path.abspath(current_dir)) == os.path.normcase(os.path.abspath(RELEASE_DIR)):
        return  # Siamo già nella release
    try:
        if not os.path.exists(REMOTE_VERSION_PATH):
            return
        if not os.path.exists(LOCAL_VERSION_PATH):
            local_version = None
        else:
            with open(LOCAL_VERSION_PATH, "r", encoding="utf-8") as f:
                local_version = f.read().strip()
        with open(REMOTE_VERSION_PATH, "r", encoding="utf-8") as f:
            remote_version = f.read().strip()
        if local_version != remote_version:
            # Notifica grafica all'utente
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showinfo("Aggiornamento DataSharing", "È disponibile una nuova versione. Il programma verrà aggiornato e riavviato.", parent=root)
                root.destroy()
            except Exception:
                pass
            # Avvia updater.py per aggiornare anche l'eseguibile in uso
            updater_path = os.path.join(current_dir, "updater.bat")
            # Ricava dinamicamente la cartella release accanto all'eseguibile, altrimenti usa una share di default
            local_release = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "release")
            if os.path.isdir(local_release):
                release_dir_hardcoded = local_release
            else:
                release_dir_hardcoded = r"\\192.168.105.200\DataSharing\release"
            updater_content = (
                f"@echo off\r\nsetlocal\r\n"
                f"set \"RELEASE_DIR={release_dir_hardcoded}\"\r\n"
                f"set \"TARGET_DIR={current_dir}\"\r\n"
                "REM Copia i file aggiornati\r\nfor %%F in (datasharing.exe datasharing_windows.exe config.json config.template.json GUIDA_UTENTE_DATASHARING.md VERSION) do (\r\n    echo Copio \"%RELEASE_DIR%\\%%F\" su \"%TARGET_DIR%\\%%F\"\r\n    if exist \"%RELEASE_DIR%\\%%F\" copy /Y \"%RELEASE_DIR%\\%%F\" \"%TARGET_DIR%\\%%F\"\r\n)\r\n"
                "REM Riavvia sempre datasharing_windows.exe\r\nif exist \"%TARGET_DIR%datasharing_windows.exe\" (\r\n    echo Avvio datasharing_windows.exe...\r\n    start \"\" \"%TARGET_DIR%datasharing_windows.exe\"\r\n) else (\r\n    echo ERRORE: %TARGET_DIR%datasharing_windows.exe non trovato!\r\n)\r\n"
                "echo Operazione completata. Premi un tasto per chiudere.\r\npause >nul\r\nexit /b 0\r\n"
            )
            with open(updater_path, "w", encoding="utf-8") as f:
                f.write(updater_content)
            import subprocess
            subprocess.Popen([updater_path], shell=True)
            sys.exit(0)
    except Exception as e:
        print(f"Errore controllo aggiornamento automatico: {e}")


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
    check_and_update_from_release()
    try:
        ActiveDirectoryAuthorizationManager().ensure_current_user_is_authorized()
    except AuthorizationError as exc:
        _show_startup_error(str(exc))
        return

    app = DataSharingWindowsApp()
    app.run()


if __name__ == "__main__":
    main()