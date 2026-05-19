' ============================================================
' BotSport — Iniciar en segundo plano (sin ventana CMD)
' Doble clic para arrancar el bot y abrir el reporte.
' ============================================================

Dim WShell, BotSportDir, PythonCmd, LogFile

Set WShell = CreateObject("WScript.Shell")

' Directorio del bot (mismo lugar que este .vbs)
BotSportDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

LogFile = BotSportDir & "\logs\bot_output.log"

' Crear carpeta logs si no existe
If Not CreateObject("Scripting.FileSystemObject").FolderExists(BotSportDir & "\logs") Then
    CreateObject("Scripting.FileSystemObject").CreateFolder(BotSportDir & "\logs")
End If

' ── Verificar si ya está corriendo ──────────────────────────
Dim WMI, Procesos, Proceso, YaCorre
YaCorre = False
Set WMI = GetObject("winmgmts:\\.\root\cimv2")
Set Procesos = WMI.ExecQuery("SELECT * FROM Win32_Process WHERE Name='python.exe'")
For Each Proceso In Procesos
    If InStr(Proceso.CommandLine, "opportunity_finder.py") > 0 Then
        YaCorre = True
    End If
Next

If YaCorre Then
    ' Ya está corriendo → solo abrir el HTML en el navegador
    WShell.Run "explorer.exe """ & BotSportDir & "\report.html""", 1, False
    WScript.Quit
End If

' ── Generar el primer reporte antes de abrir el navegador ──
' (corre UNA VEZ de forma visible para el primer fetch)
WShell.CurrentDirectory = BotSportDir
WShell.Run "cmd /c python opportunity_finder.py --once --html --min-edge 0.05 > """ & LogFile & """ 2>&1", 0, True

' ── Arrancar el bot en loop (oculto, sin ventana) ──────────
PythonCmd = "python opportunity_finder.py --html --min-edge 0.05 >> """ & LogFile & """ 2>&1"
WShell.CurrentDirectory = BotSportDir
WShell.Run "cmd /c " & PythonCmd, 0, False

' ── Abrir el HTML en el navegador ──────────────────────────
WScript.Sleep 500
WShell.Run "explorer.exe """ & BotSportDir & "\report.html""", 1, False

' ── Notificacion en bandeja (opcional) ─────────────────────
WShell.Popup "BotSport iniciado correctamente." & Chr(13) & _
             "El reporte se actualiza cada 5 min." & Chr(13) & _
             "Para detener: ejecuta detener_bot.vbs", _
             4, "BotSport", 64
