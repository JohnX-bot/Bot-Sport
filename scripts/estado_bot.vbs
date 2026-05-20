' ============================================================
' BotSport — Ver estado del bot
' ============================================================

Dim WMI, Procesos, Proceso, Corriendo, Info
Corriendo = False
Info = ""

Set WMI = GetObject("winmgmts:\\.\root\cimv2")
Set Procesos = WMI.ExecQuery("SELECT * FROM Win32_Process WHERE Name='python.exe'")

For Each Proceso In Procesos
    If InStr(Proceso.CommandLine, "opportunity_finder.py") > 0 Then
        Corriendo = True
        Info = "PID: " & Proceso.ProcessId
    End If
Next

' Leer ultima linea del log
Dim FSO, LogPath, Ultima
LogPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\logs\bot_output.log"
Ultima = ""
Set FSO = CreateObject("Scripting.FileSystemObject")
If FSO.FileExists(LogPath) Then
    Dim Stream
    Set Stream = FSO.OpenTextFile(LogPath, 1)
    Do While Not Stream.AtEndOfStream
        Ultima = Stream.ReadLine
    Loop
    Stream.Close
    ' Limpiar ANSI
    Dim RE : Set RE = CreateObject("VBScript.RegExp")
    RE.Pattern = "\x1B\[[0-9;]*m"
    RE.Global = True
    Ultima = RE.Replace(Ultima, "")
End If

If Corriendo Then
    MsgBox "Estado: CORRIENDO" & Chr(13) & Info & Chr(13) & Chr(13) & _
           "Ultimo log:" & Chr(13) & Ultima, 64, "BotSport"
Else
    MsgBox "Estado: DETENIDO" & Chr(13) & Chr(13) & _
           "Ejecuta iniciar_oculto.vbs para arrancar.", 48, "BotSport"
End If
