# Explicit hosted test plugins

Hosted Term115 SHA28f475cd237037837be20af0cf6289150168e70a Python jobs fail before collection: pytest loads pytest_asyncio.plugin explicitly and also through the asyncio entry point, causing duplicate registration. The runner now disables entry-point autoload before importing pytest, retaining the explicit reviewed plugin, full tests selector and child-executable audit guard. No assertion or test selector was removed.

The new policy test simulates that precise registration conflict without invoking pytest, children, sockets or native tools. It fails before the fix and passes on Python3.11/3.12. Actual hosted full-suite qualification is still required on the eventual aggregate SHA. NO_GO.
