; Setu POS - Windows installer (Inno Setup 6). Built by .github/workflows/build-exe.yml.
; Installs for the current user (no admin), next to where Install-Aghanya-Devanya-ERP-Setup.bat
; used to put it, so both kinds of install update the same copy. Hotel data lives in
; %LOCALAPPDATA%\AghanyaDevanyaERP\Data and is never touched by install or uninstall.

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{7B3C2E51-5A9D-4C1E-9F0B-2D6A8E4F1C73}
AppName=Setu POS
AppVersion={#AppVersion}
AppVerName=Setu POS {#AppVersion}
AppPublisher=Aghanya Devanya Enterprises
DefaultDirName={localappdata}\Programs\AghanyaDevanyaERP
DisableDirPage=yes
DefaultGroupName=Setu POS
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\Output
OutputBaseFilename=Setu-POS-Setup
SetupIconFile=..\favicon.ico
UninstallDisplayIcon={app}\Aghanya-Devanya-Hotel-ERP.exe
UninstallDisplayName=Setu POS - Restaurant & Hotel POS
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Desktop par Setu POS ka icon banayein"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\Aghanya-Devanya-Hotel-ERP.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\hotel_erp.html"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\manifest.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\sw.js"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\icon-192.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\icon-512.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\logo.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\favicon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: NeedsWebView2

[Icons]
Name: "{group}\Setu POS"; Filename: "{app}\Aghanya-Devanya-Hotel-ERP.exe"; WorkingDir: "{app}"; IconFilename: "{app}\favicon.ico"
Name: "{group}\Uninstall Setu POS"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Setu POS"; Filename: "{app}\Aghanya-Devanya-Hotel-ERP.exe"; WorkingDir: "{app}"; IconFilename: "{app}\favicon.ico"; Tasks: desktopicon

[Run]
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Microsoft WebView2 install ho raha hai (internet chahiye)..."; Check: NeedsWebView2; Flags: waituntilterminated
Filename: "{app}\Aghanya-Devanya-Hotel-ERP.exe"; Description: "Setu POS abhi kholein"; Flags: nowait postinstall skipifsilent

[Code]
const
  WV2 = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function HasWV2(Root: Integer; Key: String): Boolean;
var
  V: String;
begin
  Result := RegQueryStringValue(Root, Key, 'pv', V) and (V <> '') and (V <> '0.0.0.0');
end;

// The Setu window needs the Edge WebView2 runtime (Windows 11 has it, older PCs may not)
function NeedsWebView2(): Boolean;
begin
  Result := not (HasWV2(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\' + WV2) or
                 HasWV2(HKLM, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\' + WV2) or
                 HasWV2(HKCU, 'Software\Microsoft\EdgeUpdate\Clients\' + WV2));
end;
