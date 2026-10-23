# Ascension Macro Remastered
A Roblox Macro that checks for the presence of the specified user and, if they
are not in-game, rejoins the provided server

# Installation

1. Download the .ZIP from the github repository
2. Right-click the .ZIP and click "extract all"
3. Run the executable located in dist/ and wait for the GUI to appear, it should not require admin credentials
4. Under the "Settings" tab, enter all required settings (marked with an asterisk "*")
5. Click "Start", and the macro should start managing the client in the background
6. To stop the macro, simply click the "Stop" button. Alternatively, press F8 to stop the main loop or F9 to force quit the entire program.

# Settings Tab

User ID - The numeric ID of the Roblox user being tracked. Can be obtained from the url of the Roblox profile page for that user (www.roblox.com/users/???/profile).
Private server URL - the URL link to a Roblox private server. The macro will automatically join this link every time it reconnects the user.
Place ID - If no private URL is set, the macro uses this to determine which Roblox experience to connect to. Will join a random public server.
Check interval - the time in seconds between each user presence check (checking if they are offline)
Rejoin interval - the time in seconds

# Join Sequence Tab

Configure a custom input sequence to perform upon joining a game. Includes Wait, Click, Key, and Hotkey operations.
Wait X - Waits X seconds until the next action
Click X Y - Clicks at coordinates X,Y within the active window (Roblox)
Key K - Presses key K once
Hotkey *K - Presses down the key sequence *K in order, then releases each key *K in reverse order

# Log Tab

Reports actions, errors, and more as the macro functions.

Command for rebuild using PyInstaller:
python -m PyInstaller --noconfirm --clean AscensionMacro.spec