import os


if os.name == 'posix':
    import pamela
    authentication_type = 'PAM'

    def authenticate(username: str, password: str, **kwargs) -> bool:
        try:
            pamela.authenticate(username, password)
            return True
        except pamela.PAMError:
            return False


elif os.name == 'nt':
    import pywintypes
    import win32security
    import win32con

    authentication_type = 'WINDOWS'

    def authenticate(username: str, password: str, domain: str = '.', logon_type=win32con.LOGON32_LOGON_BATCH,
                     logon_provider=win32con.LOGON32_PROVIDER_DEFAULT) -> bool:
        try:
            win32security.LogonUser(username, domain, password, logon_type, logon_provider)
            return True
        except pywintypes.error:
            return False
