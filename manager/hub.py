#!/usr/bin/env python3
# GIMP Plugin Hub - Manager
# By LeeWAITHIRA | github.com/LeeWAITHIRA/gimp-plugin-hub

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('GimpUi', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gimp, GimpUi, Gtk, GLib
import sys
import os
import json
import urllib.request
import shutil

REGISTRY_URL = "https://raw.githubusercontent.com/LeeWAITHIRA/gimp-plugin-hub/main/registry/plugins.json"
GIMP_PLUGINS_DIR = os.path.join(os.environ.get("APPDATA", ""), "GIMP", "3.0", "plug-ins")


def fetch_registry():
    try:
        with urllib.request.urlopen(REGISTRY_URL, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data.get("plugins", [])
    except Exception as e:
        return None, str(e)


def install_plugin(plugin):
    try:
        plugin_dir = os.path.join(GIMP_PLUGINS_DIR, plugin["id"])
        os.makedirs(plugin_dir, exist_ok=True)
        filename = plugin["download_url"].split("/")[-1]
        dest = os.path.join(plugin_dir, filename)
        urllib.request.urlretrieve(plugin["download_url"], dest)
        return True, f"{plugin['name']} installed successfully!\nRestart GIMP to use it."
    except Exception as e:
        return False, str(e)


def uninstall_plugin(plugin):
    try:
        plugin_dir = os.path.join(GIMP_PLUGINS_DIR, plugin["id"])
        if os.path.exists(plugin_dir):
            shutil.rmtree(plugin_dir)
            return True, f"{plugin['name']} uninstalled.\nRestart GIMP to apply."
        return False, "Plugin not found on disk."
    except Exception as e:
        return False, str(e)


def is_installed(plugin):
    plugin_dir = os.path.join(GIMP_PLUGINS_DIR, plugin["id"])
    return os.path.exists(plugin_dir)


def build_ui(plugins, procedure, config):
    GimpUi.init("gimp-plugin-hub")
    win = Gtk.Window(title="GIMP Plugin Hub")
    win.set_default_size(600, 500)
    win.set_border_width(10)
    win.connect("destroy", Gtk.main_quit)

    # Main layout
    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    win.add(main_box)

    # Header
    header = Gtk.Label()
    header.set_markup("<big><b>🧩 GIMP Plugin Hub</b></big>\n<small>by LeeWAITHIRA</small>")
    header.set_justify(Gtk.Justification.CENTER)
    main_box.pack_start(header, False, False, 10)

    # Search bar
    search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
    search_label = Gtk.Label(label="Search:")
    search_entry = Gtk.Entry()
    search_entry.set_placeholder_text("e.g. ai, stable-diffusion...")
    search_box.pack_start(search_label, False, False, 0)
    search_box.pack_start(search_entry, True, True, 0)
    main_box.pack_start(search_box, False, False, 0)

    # Scrollable plugin list
    scroll = Gtk.ScrolledWindow()
    scroll.set_min_content_height(300)
    plugin_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    scroll.add(plugin_list_box)
    main_box.pack_start(scroll, True, True, 0)

    # Status bar
    status_label = Gtk.Label(label="")
    status_label.set_line_wrap(True)
    main_box.pack_start(status_label, False, False, 5)

    def render_plugins(filter_text=""):
        for child in plugin_list_box.get_children():
            plugin_list_box.remove(child)

        filtered = [
            p for p in plugins
            if filter_text.lower() in p["name"].lower()
            or filter_text.lower() in p["description"].lower()
            or any(filter_text.lower() in t for t in p.get("tags", []))
        ] if filter_text else plugins

        for plugin in filtered:
            card = Gtk.Frame()
            card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            card_box.set_border_width(8)
            card.add(card_box)

            # Plugin name + version
            name_label = Gtk.Label()
            name_label.set_markup(f"<b>{plugin['name']}</b>  <small>v{plugin['version']}</small>")
            name_label.set_halign(Gtk.Align.START)
            card_box.pack_start(name_label, False, False, 0)

            # Description
            desc_label = Gtk.Label(label=plugin["description"])
            desc_label.set_line_wrap(True)
            desc_label.set_halign(Gtk.Align.START)
            card_box.pack_start(desc_label, False, False, 0)

            # Tags
            tags_label = Gtk.Label()
            tags = " ".join([f"#{t}" for t in plugin.get("tags", [])])
            tags_label.set_markup(f"<small><i>{tags}</i></small>")
            tags_label.set_halign(Gtk.Align.START)
            card_box.pack_start(tags_label, False, False, 0)

            # Author + license
            meta_label = Gtk.Label()
            meta_label.set_markup(f"<small>by {plugin['author']} · {plugin['license']}</small>")
            meta_label.set_halign(Gtk.Align.START)
            card_box.pack_start(meta_label, False, False, 0)

            # Buttons
            btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            card_box.pack_start(btn_box, False, False, 4)

            installed = is_installed(plugin)

            if installed:
                status_badge = Gtk.Label()
                status_badge.set_markup("<small><b>✅ Installed</b></small>")
                btn_box.pack_start(status_badge, False, False, 0)

                uninstall_btn = Gtk.Button(label="Uninstall")
                uninstall_btn.connect("clicked", lambda b, p=plugin: on_uninstall(p))
                btn_box.pack_end(uninstall_btn, False, False, 0)
            else:
                install_btn = Gtk.Button(label="Install")
                install_btn.get_style_context().add_class("suggested-action")
                install_btn.connect("clicked", lambda b, p=plugin: on_install(p))
                btn_box.pack_end(install_btn, False, False, 0)

            plugin_list_box.pack_start(card, False, False, 0)

        plugin_list_box.show_all()

    def on_install(plugin):
        status_label.set_text(f"Installing {plugin['name']}...")
        success, msg = install_plugin(plugin)
        status_label.set_text(msg)
        render_plugins(search_entry.get_text())

    def on_uninstall(plugin):
        status_label.set_text(f"Uninstalling {plugin['name']}...")
        success, msg = uninstall_plugin(plugin)
        status_label.set_text(msg)
        render_plugins(search_entry.get_text())

    search_entry.connect("changed", lambda e: render_plugins(e.get_text()))

    render_plugins()
    win.show_all()
    Gtk.main()


def run_hub(procedure, run_mode, image, drawables, config, run_data):
    status_label_ref = []
    plugins = fetch_registry()

    if plugins is None or not isinstance(plugins, list):
        dialog = Gtk.MessageDialog(
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Could not fetch plugin registry. Check your internet connection."
        )
        dialog.run()
        dialog.destroy()
        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

    build_ui(plugins, procedure, config)
    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())


class PluginHub(Gimp.PlugIn):
    def do_query_procedures(self):
        return ["gimp-plugin-hub"]

    def do_create_procedure(self, name):
        proc = Gimp.ImageProcedure.new(
            self, name, Gimp.PDBProcType.PLUGIN, run_hub, None
        )
        proc.set_image_types("*")
        proc.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.ALWAYS)
        proc.set_menu_label("Plugin Hub")
        proc.add_menu_path("<Image>/Filters")
        proc.set_documentation(
            "GIMP Plugin Hub",
            "Browse, install and manage GIMP plugins",
            name
        )
        proc.set_attribution("LeeWAITHIRA", "LeeWAITHIRA", "2026")
        return proc


Gimp.main(PluginHub.__gtype__, sys.argv)