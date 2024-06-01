fix profile cli, add --cold and --best-of options.

By default cli profile will now run the request once (cold), then give the
best of the next 3 (hot) runs. Use --cold --best-of=1 for the old cli profile
behavior.
