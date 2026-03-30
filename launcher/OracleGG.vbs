Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\.."
WshShell.Run "cmd /c uv run uvicorn oraclegg.main:app --host 127.0.0.1 --port 8000", 0, False
WScript.Sleep 4000
WshShell.Run "http://127.0.0.1:8000", 0, False
