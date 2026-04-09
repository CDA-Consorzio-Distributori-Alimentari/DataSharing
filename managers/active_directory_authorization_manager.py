import ctypes
import csv
import getpass
import subprocess
from ctypes import wintypes

try:
    from .log_manager import LogManager
except ImportError:
    from managers.log_manager import LogManager



from .authorization_error import AuthorizationError


def show_authorization_error_and_exit(message, exit_code=1):
    try:
        import tkinter as tk
        from tkinter import messagebox

        dialog_root = tk.Tk()
        dialog_root.withdraw()
        try:
            messagebox.showerror("DataSharing", str(message), parent=dialog_root)
        finally:
            dialog_root.destroy()
    finally:
        raise SystemExit(exit_code)



# Import Win32 struct definitions
from .ad_structs import _SID_AND_ATTRIBUTES, _TOKEN_GROUPS


class ActiveDirectoryAuthorizationManager:
    DEFAULT_ALLOWED_GROUP = "CDA_IT"
    WHOAMI_TIMEOUT_SECONDS = 4
    POWERSHELL_TIMEOUT_SECONDS = 6
    # OID LDAP di Active Directory per il matching ricorsivo della membership.
    # Permette di verificare se l'utente appartiene a un gruppo anche tramite
    # catene di sottogruppi annidati, non solo membership diretta.
    LDAP_MATCHING_RULE_IN_CHAIN = "1.2.840.113556.1.4.1941"
    TOKEN_QUERY = 0x0008
    TOKEN_GROUPS_CLASS = 2

    def __init__(self, allowed_group=None):
        self.allowed_group = str(allowed_group or self.DEFAULT_ALLOWED_GROUP).strip()
        self._advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.log = LogManager()

    @staticmethod
    def _get_hidden_subprocess_kwargs():
        startupinfo = None
        creationflags = 0

        if hasattr(subprocess, "STARTUPINFO"):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            creationflags = subprocess.CREATE_NO_WINDOW

        return {
            "startupinfo": startupinfo,
            "creationflags": creationflags,
        }

    @staticmethod
    def _normalize_group_name(group_name):
        # Normalizza i nomi gruppo per confrontare sia formati semplici
        # come CDA_IT sia formati completi come DOMINIO\CDA_IT.
        normalized_name = str(group_name or "").strip().upper()
        if "\\" in normalized_name:
            normalized_name = normalized_name.rsplit("\\", 1)[-1]
        if "/" in normalized_name:
            normalized_name = normalized_name.rsplit("/", 1)[-1]
        return normalized_name

    @staticmethod
    def get_current_username():
        return getpass.getuser()

    @staticmethod
    def _escape_powershell_single_quoted_value(value):
        # Escape minimo per valori inseriti in stringhe PowerShell tra apici singoli.
        return str(value or "").replace("'", "''")

    def _read_current_user_groups_from_whoami(self):
        self.log.info("Lettura gruppi utente tramite fallback whoami /groups.")
        try:
            completed_process = subprocess.run(
                ["whoami", "/groups", "/fo", "csv", "/nh"],
                capture_output=True,
                text=True,
                check=True,
                timeout=self.WHOAMI_TIMEOUT_SECONDS,
                **self._get_hidden_subprocess_kwargs(),
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                f"whoami /groups non ha risposto entro {self.WHOAMI_TIMEOUT_SECONDS} secondi"
            ) from exc

        group_names = []
        for row in csv.reader(completed_process.stdout.splitlines()):
            if not row:
                continue
            group_name = str(row[0] or "").strip()
            if group_name:
                group_names.append(group_name)

        self.log.info(f"Fallback whoami completato. Gruppi letti: {len(group_names)}.")
        self.log.debug(f"Gruppi letti da whoami: {group_names}")
        return group_names

    def _open_current_process_token(self):
        # Apre il token Windows del processo corrente. In ambiente SSO questo token
        # rappresenta l'identita' reale dell'utente loggato sulla sessione.
        self.log.debug("Apertura del token Windows del processo corrente.")
        current_process = self._kernel32.GetCurrentProcess()
        process_token = wintypes.HANDLE()

        if not self._advapi32.OpenProcessToken(current_process, self.TOKEN_QUERY, ctypes.byref(process_token)):
            raise ctypes.WinError(ctypes.get_last_error())

        self.log.debug("Token Windows aperto correttamente.")
        return process_token

    def _lookup_account_name_from_sid(self, sid_pointer):
        # Traduce un SID in un nome leggibile del tipo DOMINIO\Gruppo.
        name_size = wintypes.DWORD(0)
        domain_size = wintypes.DWORD(0)
        sid_name_use = wintypes.DWORD(0)

        self._advapi32.LookupAccountSidW(
            None,
            sid_pointer,
            None,
            ctypes.byref(name_size),
            None,
            ctypes.byref(domain_size),
            ctypes.byref(sid_name_use),
        )

        error_code = ctypes.get_last_error()
        if error_code != 122:
            raise ctypes.WinError(error_code)

        name_buffer = ctypes.create_unicode_buffer(name_size.value)
        domain_buffer = ctypes.create_unicode_buffer(domain_size.value)

        if not self._advapi32.LookupAccountSidW(
            None,
            sid_pointer,
            name_buffer,
            ctypes.byref(name_size),
            domain_buffer,
            ctypes.byref(domain_size),
            ctypes.byref(sid_name_use),
        ):
            raise ctypes.WinError(ctypes.get_last_error())

        account_name = name_buffer.value.strip()
        domain_name = domain_buffer.value.strip()
        if domain_name:
            return f"{domain_name}\\{account_name}"
        return account_name

    def _read_current_user_groups_from_token(self):
        self.log.info("Lettura gruppi utente dal token Windows corrente.")
        process_token = self._open_current_process_token()
        try:
            required_size = wintypes.DWORD(0)
            self._advapi32.GetTokenInformation(
                process_token,
                self.TOKEN_GROUPS_CLASS,
                None,
                0,
                ctypes.byref(required_size),
            )

            error_code = ctypes.get_last_error()
            if error_code != 122:
                raise ctypes.WinError(error_code)

            token_buffer = ctypes.create_string_buffer(required_size.value)
            if not self._advapi32.GetTokenInformation(
                process_token,
                self.TOKEN_GROUPS_CLASS,
                token_buffer,
                required_size.value,
                ctypes.byref(required_size),
            ):
                raise ctypes.WinError(ctypes.get_last_error())

            token_groups = ctypes.cast(token_buffer, ctypes.POINTER(_TOKEN_GROUPS)).contents
            groups_array_type = _SID_AND_ATTRIBUTES * token_groups.GroupCount
            groups = ctypes.cast(
                ctypes.addressof(token_groups.Groups),
                ctypes.POINTER(groups_array_type),
            ).contents

            group_names = []
            for group_entry in groups:
                try:
                    group_names.append(self._lookup_account_name_from_sid(group_entry.Sid))
                except OSError:
                    continue

            self.log.info(f"Token Windows letto correttamente. Gruppi trovati: {len(group_names)}.")
            self.log.debug(f"Gruppi presenti nel token Windows: {group_names}")
            return group_names
        finally:
            self._kernel32.CloseHandle(process_token)
            self.log.debug("Handle del token Windows chiuso.")

    def _read_current_user_groups(self):
        try:
            return self._read_current_user_groups_from_token()
        except Exception as exc:
            self.log.warning(
                f"Lettura gruppi dal token Windows non riuscita, attivo fallback whoami. Dettaglio: {exc}"
            )
            return self._read_current_user_groups_from_whoami()

    def _is_group_present_in_token(self, required_group):
        # Primo controllo: membership vista dal token della sessione corrente.
        # E' rapido e riflette l'identita' con cui il processo e' stato avviato.
        self.log.info(
            f"Avvio controllo autorizzazione via token Windows per il gruppo richiesto {self.allowed_group}."
        )
        current_user_groups = self._read_current_user_groups()
        normalized_groups = {self._normalize_group_name(group_name) for group_name in current_user_groups}
        is_authorized = required_group in normalized_groups
        self.log.info(
            f"Esito controllo via token Windows per il gruppo {self.allowed_group}: {'AUTORIZZATO' if is_authorized else 'NON AUTORIZZATO'}."
        )
        return is_authorized

    def _run_powershell_boolean_script(self, script_text, operation_label):
        try:
            completed_process = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-WindowStyle",
                    "Hidden",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    script_text,
                ],
                capture_output=True,
                text=True,
                timeout=self.POWERSHELL_TIMEOUT_SECONDS,
                **self._get_hidden_subprocess_kwargs(),
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                f"{operation_label}: timeout oltre {self.POWERSHELL_TIMEOUT_SECONDS} secondi"
            ) from exc

        stdout_text = str(completed_process.stdout or "").strip()
        stderr_text = str(completed_process.stderr or "").strip()

        if completed_process.returncode != 0:
            error_detail = stderr_text or stdout_text or "Errore PowerShell sconosciuto."
            raise RuntimeError(f"{operation_label}: {error_detail}")

        self.log.debug(f"Output {operation_label}: {stdout_text}")
        return stdout_text.upper() == "TRUE"

    def _is_group_present_in_active_directory_authorization_groups(self):
        # Primo controllo server-side ricorsivo: usa i gruppi autorizzativi AD risolti
        # da .NET, che includono i gruppi annidati realmente validi per l'utente.
        escaped_group = self._escape_powershell_single_quoted_value(self.allowed_group)
        powershell_script = f"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.DirectoryServices.AccountManagement

$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$userSid = $identity.User.Value
$groupName = '{escaped_group}'

$contextType = [System.DirectoryServices.AccountManagement.ContextType]::Domain
$context = New-Object System.DirectoryServices.AccountManagement.PrincipalContext($contextType)

$user = [System.DirectoryServices.AccountManagement.UserPrincipal]::FindByIdentity(
    $context,
    [System.DirectoryServices.AccountManagement.IdentityType]::Sid,
    $userSid
)
if ($null -eq $user) {{
    throw "Utente Active Directory non trovato per SID $userSid"
}}

$group = [System.DirectoryServices.AccountManagement.GroupPrincipal]::FindByIdentity(
    $context,
    [System.DirectoryServices.AccountManagement.IdentityType]::SamAccountName,
    $groupName
)
if ($null -eq $group) {{
    $group = [System.DirectoryServices.AccountManagement.GroupPrincipal]::FindByIdentity(
        $context,
        [System.DirectoryServices.AccountManagement.IdentityType]::Name,
        $groupName
    )
}}
if ($null -eq $group) {{
    throw "Gruppo Active Directory non trovato: $groupName"
}}

$targetSid = $group.Sid.Value
foreach ($authorizationGroup in $user.GetAuthorizationGroups()) {{
    if ($null -ne $authorizationGroup.Sid -and $authorizationGroup.Sid.Value -eq $targetSid) {{
        Write-Output 'True'
        return
    }}
}}

Write-Output 'False'
""".strip()

        return self._run_powershell_boolean_script(
            powershell_script,
            "controllo Active Directory tramite gruppi autorizzativi ricorsivi",
        )

    def _is_group_present_in_active_directory_ldap(self):
        # Secondo controllo server-side ricorsivo: query LDAP con matching rule IN_CHAIN.
        # Rimane come fallback per coprire ambienti dove AccountManagement non risolve bene.
        escaped_group = self._escape_powershell_single_quoted_value(self.allowed_group)
        matching_rule = self.LDAP_MATCHING_RULE_IN_CHAIN
        powershell_script = f"""
$ErrorActionPreference = 'Stop'

function Escape-LdapFilterValue([string]$value) {{
    if ($null -eq $value) {{
        return ''
    }}

    return $value.Replace('\\', '\\5c').Replace('*', '\\2a').Replace('(', '\\28').Replace(')', '\\29').Replace([char]0, '\\00')
}}

$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$samAccountName = $identity.Name.Split('\\')[-1]

$rootDse = [ADSI]'LDAP://RootDSE'
$defaultNamingContext = [string]$rootDse.defaultNamingContext
if ([string]::IsNullOrWhiteSpace($defaultNamingContext)) {{
    throw 'Default naming context non disponibile.'
}}

$searchRoot = [ADSI]("LDAP://" + $defaultNamingContext)

$userSearcher = New-Object System.DirectoryServices.DirectorySearcher($searchRoot)
$userSearcher.PageSize = 1
$userSearcher.SearchScope = [System.DirectoryServices.SearchScope]::Subtree
$escapedSamAccountName = Escape-LdapFilterValue($samAccountName)
$userSearcher.Filter = "(&(objectCategory=person)(objectClass=user)(sAMAccountName=$escapedSamAccountName))"
$null = $userSearcher.PropertiesToLoad.Add('distinguishedName')
$userResult = $userSearcher.FindOne()
if ($null -eq $userResult) {{
    throw "Utente Active Directory non trovato: $samAccountName"
}}

$userDistinguishedName = [string]$userResult.Properties['distinguishedname'][0]
$escapedGroupName = Escape-LdapFilterValue('{escaped_group}')

$groupSearcher = New-Object System.DirectoryServices.DirectorySearcher($searchRoot)
$groupSearcher.PageSize = 1
$groupSearcher.SearchScope = [System.DirectoryServices.SearchScope]::Subtree
$groupSearcher.Filter = "(&(objectClass=group)(|(cn=$escapedGroupName)(sAMAccountName=$escapedGroupName))(member:{matching_rule}:=$userDistinguishedName))"
$groupResult = $groupSearcher.FindOne()

if ($null -ne $groupResult) {{
    Write-Output 'True'
}} else {{
    Write-Output 'False'
}}
""".strip()

        return self._run_powershell_boolean_script(
            powershell_script,
            "controllo Active Directory tramite query LDAP ricorsiva",
        )

    def _is_group_present_in_active_directory(self, required_group):
        # Secondo livello complessivo: query diretta ad Active Directory.
        # Prima prova i gruppi autorizzativi ricorsivi di .NET, poi fa fallback
        # sulla query LDAP con matching rule IN_CHAIN.
        self.log.info(
            f"Avvio controllo autorizzazione via Active Directory ricorsiva per il gruppo {self.allowed_group}."
        )
        authorization_groups_error = None
        ldap_error = None

        try:
            is_authorized = self._is_group_present_in_active_directory_authorization_groups()
            self.log.info(
                f"Esito controllo Active Directory ricorsivo tramite gruppi autorizzativi per il gruppo {self.allowed_group}: {'AUTORIZZATO' if is_authorized else 'NON AUTORIZZATO'}."
            )
            if is_authorized:
                return True
        except Exception as exc:
            authorization_groups_error = exc
            self.log.warning(
                f"Controllo ricorsivo tramite gruppi autorizzativi non riuscito per il gruppo {self.allowed_group}: {exc}"
            )

        try:
            is_authorized = self._is_group_present_in_active_directory_ldap()
        except Exception as exc:
            ldap_error = exc
            error_parts = []
            if authorization_groups_error is not None:
                error_parts.append(f"gruppi autorizzativi: {authorization_groups_error}")
            error_parts.append(f"LDAP: {ldap_error}")
            raise RuntimeError("; ".join(error_parts)) from exc

        self.log.info(
            f"Esito controllo Active Directory ricorsivo per il gruppo {self.allowed_group}: {'AUTORIZZATO' if is_authorized else 'NON AUTORIZZATO'}."
        )
        return is_authorized

    def ensure_current_user_is_authorized(self):
        # Strategia complessiva:
        # 1. Controllo veloce sul token Windows della sessione corrente.
        # 2. Se il token non conferma l'accesso, controllo direttamente in AD
        #    con navigazione ricorsiva dei sottogruppi.
        # 3. Se nessuno dei due controlli autorizza l'utente, il run viene bloccato.
        username = self.get_current_username()
        required_group = self._normalize_group_name(self.allowed_group)

        token_check_error = None
        ad_check_error = None

        self.log.info(
            f"Inizio verifica autorizzazione Active Directory per utente {username} sul gruppo {self.allowed_group}."
        )

        try:
            if self._is_group_present_in_token(required_group):
                self.log.info(
                    f"Utente {username} autorizzato tramite token Windows per il gruppo {self.allowed_group}."
                )
                return True
        except Exception as exc:
            token_check_error = exc
            self.log.warning(f"Controllo via token Windows fallito per utente {username}: {exc}")

        try:
            if self._is_group_present_in_active_directory(required_group):
                self.log.info(
                    f"Utente {username} autorizzato tramite verifica Active Directory ricorsiva per il gruppo {self.allowed_group}."
                )
                return True
        except Exception as exc:
            ad_check_error = exc
            self.log.warning(f"Controllo via Active Directory ricorsiva fallito per utente {username}: {exc}")

        if token_check_error is not None and ad_check_error is not None:
            self.log.error(
                f"Verifica autorizzazione impossibile per utente {username}. Errore token: {token_check_error}. Errore directory: {ad_check_error}"
            )
            raise AuthorizationError(
                f"Impossibile verificare l'appartenenza al gruppo Active Directory {self.allowed_group} per l'utente {username}. "
                f"Controllo token: {token_check_error}. Controllo directory: {ad_check_error}"
            ) from ad_check_error

        self.log.warning(
            f"Utente {username} non autorizzato. Il gruppo richiesto e' {self.allowed_group}, anche tramite sottogruppi."
        )
        raise AuthorizationError(
            f"Utente non autorizzato: {username}. E' richiesta l'appartenenza al gruppo Active Directory {self.allowed_group}, anche tramite sottogruppi."
        )


