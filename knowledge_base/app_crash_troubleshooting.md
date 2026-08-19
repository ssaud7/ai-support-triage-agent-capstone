# App Crash Troubleshooting

When a customer reports the app crashing, gather these details first: platform
(iOS/Android/Web/Desktop), app version, and what action was happening right before
the crash (e.g., opening a report, uploading a file).

Common known causes, in order of frequency:

1. **Outdated app version** — crashes are most common on versions more than 2 minor
   releases behind current. Ask the customer to update via their app store first.
2. **Large file uploads on mobile** — uploading files over 50MB on the mobile app can
   cause an out-of-memory crash on older devices. Recommend using the web app for
   large uploads instead.
3. **Corrupted local cache** — clearing the app's local cache (Settings > Storage >
   Clear Cache, not "Clear Data") resolves most repeated crashes on the same screen.
4. **Third-party plugin conflicts** — only relevant for the desktop app; disabling
   all plugins and re-enabling them one at a time isolates the culprit.

If crashes persist after these steps, request the crash log (Settings > About >
Export Diagnostic Log) and escalate to engineering with the app version and OS
version included.
