' ============================================================
' BotSport — Detener el bot
' ============================================================

Dim WMI, Procesos, Proceso, Detenidos
Detenidos = 0

Set WMI = GetObject("winmgmts:\\.\root\cimv2")
Set Procesos = WMI.ExecQuery("SELECT * FROM Win32_Process WHERE Name='python.exe'")

For Each Proceso In Procesos
    If InStr(Proceso.CommandLine, "opportunity_finder.py") > 0 Then
        Proceso.Terminate()
        Detenidos = Detenidos + 1
    End If
Next

If Detenidos > 0 Then
    MsgBox "BotSport detenido correctamente (" & Detenidos & " proceso/s).", 64, "BotSport"
Else
    MsgBox "El bot no estaba corriendo.", 48, "BotSport"
End If
