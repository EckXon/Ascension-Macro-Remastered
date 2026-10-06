# Ascension Macro Remastered
A Roblox Macro that checks for the presence of the specified user and, if they
are not in-game, rejoins the provided server link.

Steps:
1. Download the .ZIP from the github repository
2. Right-click the .ZIP and click "extract all"
4. Edit config.json before running: set the user id, a place id or private server URL, and the check and rejoin intervals. If config.json is missing, the script copies it from config.example.json on startup.
5. Run "python AMR.py" in the terminal (or double-click the file)
6. To quit, press F8. To force quit, press F9.

Command for rebuild using PyInstaller:
python -m PyInstaller --noconfirm --clean AscensionMacro.spec