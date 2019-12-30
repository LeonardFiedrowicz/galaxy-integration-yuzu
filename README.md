# Yuzu Plugin for GOG Galaxy 2.0

Requires Yuzu to be installed. This implementation is a modification of the [Citra Plugin](https://github.com/j-selby/galaxy-integration-citra). Using [NX_Game_Info](https://github.com/garoxas/NX_Game_Info) for collecting game meta data.

Requires a `prod.keys` file either in `[path-to-yuzu]\yuzu\yuzu-windows-msvc\user\keys\` or at `%APPDATA%\yuzu\keys` to decode games files (if you've used yuzu before you should already have these).

Doesn't track game time yet.

## Features

* Library: Switch games in your ROM folder
* Launch: Launches games with Yuzu

## Installation

Download the latest release and extract it to:
- (WINDOWS) `%localappdata%\GOG.com\Galaxy\plugins\installed\galaxy-integration-yuzu`
- (MACOS) `~/Library/Application Support/GOG.com/Galaxy/plugins/installed/galaxy-integration-yuzu`

i.e 
`C:\Users\Leonard\AppData\Local\GOG.com\Galaxy\plugins\installed\galaxy-integration-yuzu`

## License

Apache-2.0
