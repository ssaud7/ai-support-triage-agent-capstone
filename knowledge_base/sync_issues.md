# Data Not Syncing Between Devices

Sync issues are usually caused by one of the following:

1. **Offline changes conflict** — if a customer edited the same record on two devices
   while offline, the system keeps the most recently saved version and stores the
   other as a conflict copy labeled "(conflicted copy)". Both versions are never
   silently merged.
2. **Sync paused due to storage limit** — if an account exceeds its storage quota,
   sync pauses automatically until the customer frees up space or upgrades their
   plan. This shows a small warning icon in the app's sync status bar.
3. **Stale session on one device** — if a device hasn't synced in more than 14 days,
   it may need the customer to log out and back in to refresh its sync token.
4. **Regional server delay** — during regional outages, sync can lag by up to 15
   minutes; check the status page before assuming it's account-specific.

Full resync (Settings > Sync > Force Resync) re-downloads all data from the server
and can take several minutes for large accounts — warn the customer before running it
that any unsynced local-only changes will be lost.
