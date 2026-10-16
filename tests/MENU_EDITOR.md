# Customer Display browser regression

Requires the project's Python environment, Playwright (NODE_PATH may point to the bundled Node packages), and installed Chrome.

From the project root, start `python tests/menu_editor_fixture.py`, then run `node tests/test_menu_editor.cjs` in another terminal. Stop the fixture server after the check.

The fixture uses port 8011 and a temporary SQLite database and upload directory. It never modifies the restaurant database. Test tokens and the phone screenshot are written to the OS temporary directory under `restaurant-menu-editor-check`.

Checks cover uploads, invalid image rejection, media replacement/removal, preview versus publish, appearance persistence, compact colors, section separation, upload above 40 MB and hosting rejection messages, video unmute/play/pause, QR rendering, 320/390/768/1440px layout, menu CRUD, ordering, authentication and cashier API access. The existing billing and network tests should also be run.
