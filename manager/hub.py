#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# GIMP Plugin Hub - By LeeWAITHIRA
# github.com/LeeWAITHIRA/gimp-plugin-hub

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('GimpUi', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gimp, GimpUi, Gtk, GLib, GObject
import sys
import os
import json
import urllib.request
import shutil

REGISTRY_URL = "https://raw.githubusercontent.com/LeeWAITHIRA/gimp-plugin-hub/main/registry/plugins.json"
GIMP_PLUGINS_DIR = os.path.join(os.environ.get("APPDATA", ""), "GIMP", "3.2", "plug-ins")

plug_in_proc   = "plug-in-gimp-plugin-hub"
plug_in_binary = "hub"

def fetch_registry():
    try:
        with urllib.request.urlopen(REGISTRY_URL, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data.get("plugins", [])
    except Exception as e:
        return []

def install_plugin(plugin):
    try:
        plugin_dir = os.path.join(GIMP_PLUGINS_DIR, plugin["id"])
        os.makedirs(plugin_dir, exist_ok=True)
        filename = plugin["download_url"].split("/")[-1]
        dest = os.path.join(plugin_dir, filename)
        urllib.request.urlretrieve(plugin["download_url"], dest)
        return True, f"{plugin['name']} installed!\nRestart GIMP to use it."
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
    return os.path.exists(os.path.join(GIMP_PLUGINS_DIR, plugin["id"]))

def build_ui(plugins):
    GimpUi.init(plug_in_binary)
    win = Gtk.Window(title="GIMP Plugin Hub")
    win.set_default_size(620, 520)
    win.set_border_width(12)
    win.connect("destroy", Gtk.main_quit)

    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    win.add(main_box)

    # Header
    header = Gtk.Label()
    header.set_markup("<big><b>🧩 GIMP Plugin Hub</b></big>\n<small>by LeeWAITHIRA · github.com/LeeWAITHIRA/gimp-plugin-hub</small>")
    header.set_justify(Gtk.Justification.CENTER)
    main_box.pack_start(header, False, False, 8)

    # Search
    search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    search_label = Gtk.Label(label="🔍 Search:")
    search_entry = Gtk.Entry()
    search_entry.set_placeholder_text("Search by name, tag, or description...")
    search_box.pack_start(search_label, False, False, 0)
    search_box.pack_start(search_entry, True, True, 0)
    main_box.pack_start(search_box, False, False, 0)

    # Plugin list
    scroll = Gtk.ScrolledWindow()
    scroll.set_min_content_height(320)
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    plugin_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    scroll.add(plugin_list_box)
    main_box.pack_start(scroll, True, True, 0)

    # Status
    status_label = Gtk.Label(label="")
    status_label.set_line_wrap(True)
    status_label.set_justify(Gtk.Justification.CENTER)
    main_box.pack_start(status_label, False, False, 4)

    def render_plugins(filter_text=""):
        for child in plugin_list_box.get_children():
            plugin_list_box.remove(child)

        filtered = [
            p for p in plugins
            if filter_text.lower() in p["name"].lower()
            or filter_text.lower() in p["description"].lower()
            or any(filter_text.lower() in t for t in p.get("tags", []))
        ] if filter_text else plugins

        if not filtered:
            empty = Gtk.Label(label="No plugins found.")
            plugin_list_box.pack_start(empty, False, False, 20)
        else:
            for plugin in filtered:
                card = Gtk.Frame()
                card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                card_box.set_border_width(10)
                card.add(card_box)

                name_label = Gtk.Label()
                name_label.set_markup(f"<b>{plugin['name']}</b>  <small>v{plugin['version']} · GIMP {plugin['gimp_version']}</small>")
                name_label.set_halign(Gtk.Align.START)
                card_box.pack_start(name_label, False, False, 0)

                desc_label = Gtk.Label(label=plugin["description"])
                desc_label.set_line_wrap(True)
                desc_label.set_halign(Gtk.Align.START)
                card_box.pack_start(desc_label, False, False, 0)

                tags_label = Gtk.Label()
                tags = "  ".join([f"#{t}" for t in plugin.get("tags", [])])
                tags_label.set_markup(f"<small><i>{tags}</i></small>")
                tags_label.set_halign(Gtk.Align.START)
                card_box.pack_start(tags_label, False, False, 0)

                meta_label = Gtk.Label()
                meta_label.set_markup(f"<small>by {plugin['author']} · {plugin['license']}</small>")
                meta_label.set_halign(Gtk.Align.START)
                card_box.pack_start(meta_label, False, False, 0)

                btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                card_box.pack_start(btn_box, False, False, 4)

                installed = is_installed(plugin)
                if installed:
                    badge = Gtk.Label()
                    badge.set_markup("<small><b>✅ Installed</b></small>")
                    btn_box.pack_start(badge, False, False, 0)
                    uninstall_btn = Gtk.Button(label="Uninstall")
                    uninstall_btn.connect("clicked", lambda b, p=plugin: on_action(p, False))
                    btn_box.pack_end(uninstall_btn, False, False, 0)
                else:
                    install_btn = Gtk.Button(label="Install")
                    install_btn.connect("clicked", lambda b, p=plugin: on_action(p, True))
                    btn_box.pack_end(install_btn, False, False, 0)

                plugin_list_box.pack_start(card, False, False, 0)

        plugin_list_box.show_all()

    def on_action(plugin, do_install):
        if do_install:
            status_label.set_text(f"Installing {plugin['name']}...")
            success, msg = install_plugin(plugin)
        else:
            status_label.set_text(f"Uninstalling {plugin['name']}...")
            success, msg = uninstall_plugin(plugin)
        status_label.set_text(msg)
        render_plugins(search_entry.get_text())

    search_entry.connect("changed", lambda e: render_plugins(e.get_text()))
    render_plugins()
    win.show_all()
    Gtk.main()


def hub_run(procedure, run_mode, image, drawables, config, data):
    plugins = fetch_registry()
    if not plugins:
        GimpUi.init(plug_in_binary)
        dialog = Gtk.MessageDialog(
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Could not load plugin registry. Check your internet connection."
        )
        dialog.run()
        dialog.destroy()
    else:
        build_ui(plugins)
    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, None)


class PluginHub(Gimp.PlugIn):
    def do_query_procedures(self):
        return [plug_in_proc]

    def do_create_procedure(self, name):
        procedure = Gimp.ImageProcedure.new(
            self, name, Gimp.PDBProcType.PLUGIN, hub_run, None
        )
        procedure.set_sensitivity_mask(
            Gimp.ProcedureSensitivityMask.DRAWABLE |
            Gimp.ProcedureSensitivityMask.NO_DRAWABLES
        )
        procedure.set_menu_label("Plugin Hub")
        procedure.add_menu_path("<Image>/Filters")
        procedure.set_documentation(
            "Browse and install GIMP plugins",
            "GIMP Plugin Hub by LeeWAITHIRA",
            None
        )
        procedure.set_attribution("LeeWAITHIRA", "LeeWAITHIRA", "2026")
        return procedure


Gimp.main(PluginHub.__gtype__, sys.argv)