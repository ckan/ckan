`--no-config` / `-C` CLI flag that skips app initialization and config parsing. This means that commands registered via `IClick` interface are not available. It can be used only with the commands registered inside the setup.py as long as such commands do not read config options and do not interact with CKAN application(DB interactions, API calls, etc)

