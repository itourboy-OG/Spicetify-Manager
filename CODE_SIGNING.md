# Code signing

`build-installer.bat` can Authenticode-sign both the packaged application and
the final Setup installer. Signing is optional; normal local builds remain
unsigned.

## Requirements

1. Obtain a trusted Windows code-signing certificate from a commercial
   certificate authority.
2. Install the certificate in the current Windows user's Personal certificate
   store.
3. Install SignTool through the Windows SDK, or set `SIGNTOOL_PATH` to the full
   path of `signtool.exe`.
4. Find the certificate's SHA-1 thumbprint in Windows Certificate Manager.

## Signed build

In PowerShell:

```powershell
$env:SIGN_CERT_SHA1 = "YOUR_CERTIFICATE_THUMBPRINT"
$env:SIGN_TIMESTAMP_URL = "http://timestamp.digicert.com"
.\build-installer.bat
```

The script signs and verifies:

- `dist\Spicetify Manager\Spicetify Manager.exe`
- `installer-output\Spicetify-Manager-v2.4.0-Setup.exe`

Never commit a `.pfx`, `.p12`, private key, certificate password, or other
signing secret. Those certificate file extensions are excluded by `.gitignore`.

Code signing identifies the publisher and protects file integrity. Microsoft
Defender SmartScreen reputation can still take time to develop after a new
certificate begins distributing applications.

References:

- [Microsoft SignTool documentation](https://learn.microsoft.com/windows/win32/seccrypto/signtool)
- [Microsoft Authenticode timestamping guidance](https://learn.microsoft.com/windows/win32/seccrypto/time-stamping-authenticode-signatures)
