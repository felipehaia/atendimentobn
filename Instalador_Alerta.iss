[Setup]
AppName=Sistema de Alerta de Atendimento
AppVersion=1.0
DefaultDirName={autopf}\Alerta Atendimento
DefaultGroupName=Alerta Atendimento
OutputDir=Output
OutputBaseFilename=Instalador_Alerta_Atendimento
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin

[Types]
Name: "custom"; Description: "Instalação Personalizada"; Flags: iscustom

[Components]
Name: "recepcao"; Description: "Módulo Recepção (Painel de Chamadas)"; Types: custom
Name: "colaborador"; Description: "Módulo Colaborador (Notificador de Sala)"; Types: custom
Name: "servidor"; Description: "Módulo Servidor (Central de Conexões)"; Types: custom

[Files]
; Módulo Recepção
Source: "dist\Recepcao.exe"; DestDir: "{app}"; Components: recepcao; Flags: ignoreversion
; Módulo Colaborador
Source: "dist\Colaborador.exe"; DestDir: "{app}"; Components: colaborador; Flags: ignoreversion
; Módulo Servidor
Source: "dist\AlertaServidor.exe"; DestDir: "{app}"; Components: servidor; Flags: ignoreversion

[Icons]
; Atalhos no Menu Iniciar e Área de Trabalho
Name: "{group}\Alerta Recepção"; Filename: "{app}\Recepcao.exe"; Components: recepcao
Name: "{autodesktop}\Alerta Recepção"; Filename: "{app}\Recepcao.exe"; Components: recepcao

Name: "{group}\Alerta Colaborador"; Filename: "{app}\Colaborador.exe"; Components: colaborador
Name: "{autodesktop}\Alerta Colaborador"; Filename: "{app}\Colaborador.exe"; Components: colaborador

Name: "{group}\Alerta Servidor"; Filename: "{app}\AlertaServidor.exe"; Components: servidor

[Run]
; Configurações ao finalizar a instalação
; 1. Se instalar o Colaborador, adiciona ao Registro do Windows para arrancar no Login
Filename: "reg"; Parameters: "add ""HKCU\Software\Microsoft\Windows\CurrentVersion\Run"" /v ""AlertaColaborador"" /t REG_SZ /d ""\""{app}\Colaborador.exe\"""" /f"; Components: colaborador; Flags: runhidden

; 2. Se instalar o Servidor, regista e inicia como Tarefa Agendada em segundo plano
Filename: "schtasks"; Parameters: "/create /tn ""AlertaServidorService"" /tr ""\""{app}\AlertaServidor.exe\"""" /sc onstart /ru SYSTEM /F"; Components: servidor; Flags: runhidden
Filename: "schtasks"; Parameters: "/run /tn ""AlertaServidorService"""; Components: servidor; Flags: runhidden

; Opção de abrir as aplicações ao concluir a instalação
Filename: "{app}\Recepcao.exe"; Description: "Iniciar Alerta Recepção"; Flags: nowait postinstall skipifsilent; Components: recepcao
Filename: "{app}\Colaborador.exe"; Description: "Iniciar Alerta Colaborador"; Flags: nowait postinstall skipifsilent; Components: colaborador