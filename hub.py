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
import urllib.error
import shutil
import re

REGISTRY_URL = "https://raw.githubusercontent.com/LeeWAITHIRA/gimp-plugin-hub/main/registry/plugins.json"
GIMP_PLUGINS_DIR = os.path.join(os.environ.get("APPDATA", ""), "GIMP", "3.2", "plug-ins")
GIMP_PYTHON = os.path.join(os.path.dirname(sys.executable), "python.exe")

plug_in_proc   = "plug-in-gimp-plugin-hub"
plug_in_binary = "hub"


def patch_shebang(filepath):
    """Replace first line with standard python3 shebang - CRITICAL FOR GIMP 3.x!"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Always ensure shebang is first line
        if lines and lines[0].startswith('#!'):
            lines[0] = '#!/usr/bin/env python3\n'
        else:
            lines.insert(0, '#!/usr/bin/env python3\n')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    except Exception as e:
        print(f"Warning: Could not patch shebang: {e}", file=sys.stderr)


def fetch_registry():
    """Fetch plugin registry from GitHub."""
    try:
        with urllib.request.urlopen(REGISTRY_URL, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data.get("plugins", [])
    except Exception:
        return []


def get_plugin_folder(plugin):
    """Folder name must match .py filename exactly for GIMP 3."""
    filename = plugin["download_url"].split("/")[-1]
    return filename.replace(".py", ""), filename


def parse_github_url(url):
    """Parse GitHub URL and extract raw content URL.
    
    Supports:
    - https://github.com/user/repo/blob/branch/path/file.py
    - https://raw.githubusercontent.com/user/repo/branch/path/file.py
    """
    url = url.strip()
    
    # Format: https://github.com/user/repo/blob/branch/path/to/file.py
    blob_pattern = r'https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+\.py)$'
    match = re.match(blob_pattern, url)
    if match:
        user, repo, branch, path = match.groups()
        raw_url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path}"
        return raw_url, user, path.split("/")[-1]
    
    # Format: https://raw.githubusercontent.com/user/repo/branch/path/to/file.py
    if "raw.githubusercontent.com" in url and url.endswith(".py"):
        user = url.split("/")[3]
        filename = url.split("/")[-1]
        return url, user, filename
    
    return None, None, None


def install_plugin_from_url(url, plugin_name=None):
    """Install plugin from a GitHub URL.
    
    Args:
        url: GitHub blob or raw URL
        plugin_name: Optional custom name for the plugin folder
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        raw_url, author, filename = parse_github_url(url)
        
        if not raw_url:
            return False, "❌ Invalid GitHub URL format.\n\nExpected format:\ngithub.com/user/repo/blob/branch/path/file.py\n\nOr:\nraw.githubusercontent.com/user/repo/branch/path/file.py"
        
        if not filename.endswith(".py"):
            return False, "❌ File must be a Python file (.py)"
        
        # Use provided name or derive from filename
        if plugin_name:
            folder_name = plugin_name
        else:
            folder_name = filename.replace(".py", "")
        
        # Create plugin directory structure (CRITICAL: folder name must match .py filename)
        plugin_dir = os.path.join(GIMP_PLUGINS_DIR, folder_name)
        os.makedirs(plugin_dir, exist_ok=True)
        dest = os.path.join(plugin_dir, filename)
        
        # Download plugin
        urllib.request.urlretrieve(raw_url, dest)
        
        # Apply shebang (CRITICAL for GIMP 3.x)
        patch_shebang(dest)
        
        return True, f"✅ Plugin installed successfully!\n\n📁 Location: {plugin_dir}\n👤 Author: {author}\n\n⚠️  Restart GIMP to load the plugin."
        
    except urllib.error.URLError as e:
        return False, f"❌ Download failed.\n\nCheck:\n• URL is correct\n• Internet connection\n• GitHub is accessible\n\nError: {str(e)}"
    except Exception as e:
        return False, f"❌ Installation failed:\n{str(e)}"


def install_plugin(plugin):
    """Install plugin from registry entry."""
    try:
        folder_name, filename = get_plugin_folder(plugin)
        plugin_dir = os.path.join(GIMP_PLUGINS_DIR, folder_name)
        os.makedirs(plugin_dir, exist_ok=True)
        dest = os.path.join(plugin_dir, filename)
        urllib.request.urlretrieve(plugin["download_url"], dest)
        
        # Apply shebang (CRITICAL for GIMP 3.x)
        patch_shebang(dest)
        
        return True, f"✅ {plugin['name']} installed!\n\nRestart GIMP to use it."
    except Exception as e:
        return False, f"❌ Install failed: {str(e)}"


def uninstall_plugin(plugin):
    """Uninstall plugin from disk."""
    try:
        folder_name, _ = get_plugin_folder(plugin)
        plugin_dir = os.path.join(GIMP_PLUGINS_DIR, folder_name)
        if os.path.exists(plugin_dir):
            shutil.rmtree(plugin_dir)
            return True, f"🗑️ {plugin['name']} uninstalled.\n\nRestart GIMP to apply."
        return False, "Plugin not found on disk."
    except Exception as e:
        return False, str(e)


def is_installed(plugin):
    """Check if plugin is installed."""
    folder_name, _ = get_plugin_folder(plugin)
    return os.path.exists(os.path.join(GIMP_PLUGINS_DIR, folder_name))


def build_ui(plugins):
    """Build and display the main UI with Registry and Custom URL tabs."""
    GimpUi.init(plug_in_binary)
    win = Gtk.Window(title="GIMP Plugin Hub")
    win.set_default_size(700, 700)
    win.set_border_width(12)
    win.connect("destroy", Gtk.main_quit)

    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    win.add(main_box)

    # Header
    header = Gtk.Label()
    header.set_markup("<big><b>🧩 GIMP Plugin Hub</b></big>\n<small>by LeeWAITHIRA · github.com/LeeWAITHIRA/gimp-plugin-hub</small>")
    header.set_justify(Gtk.Justification.CENTER)
    main_box.pack_start(header, False, False, 8)

    # Create notebook (tabs)
    notebook = Gtk.Notebook()
    main_box.pack_start(notebook, True, True, 0)

    # ===== TAB 1: Registry =====
    registry_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    registry_box.set_border_width(10)
    
    search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    search_label = Gtk.Label(label="🔍 Search:")
    search_entry = Gtk.Entry()
    search_entry.set_placeholder_text("Search by name, tag, or description...")
    search_box.pack_start(search_label, False, False, 0)
    search_box.pack_start(search_entry, True, True, 0)
    registry_box.pack_start(search_box, False, False, 0)

    scroll = Gtk.ScrolledWindow()
    scroll.set_min_content_height(300)
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    plugin_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    scroll.add(plugin_list_box)
    registry_box.pack_start(scroll, True, True, 0)

    status_label = Gtk.Label(label="")
    status_label.set_line_wrap(True)
    status_label.set_justify(Gtk.Justification.CENTER)
    registry_box.pack_start(status_label, False, False, 4)

    notebook.append_page(registry_box, Gtk.Label(label="📦 Registry"))

    # ===== TAB 2: Install from GitHub URL =====
    custom_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    custom_box.set_border_width(20)
    
    url_title = Gtk.Label()
    url_title.set_markup("<big><b>🔗 Install from GitHub</b></big>")
    url_title.set_justify(Gtk.Justification.CENTER)
    custom_box.pack_start(url_title, False, False, 0)

    instruction = Gtk.Label()
    instruction.set_markup("<small>Paste the GitHub URL of a Python plugin file</small>")
    instruction.set_justify(Gtk.Justification.CENTER)
    custom_box.pack_start(instruction, False, False, 0)

    url_label = Gtk.Label(label="GitHub URL:")
    url_label.set_halign(Gtk.Align.START)
    custom_box.pack_start(url_label, False, False, 0)

    url_entry = Gtk.Entry()
    url_entry.set_placeholder_text("https://github.com/user/repo/blob/branch/path/plugin.py")
    custom_box.pack_start(url_entry, False, False, 0)

    name_label = Gtk.Label(label="Plugin Name (optional):")
    name_label.set_halign(Gtk.Align.START)
    custom_box.pack_start(name_label, False, False, 0)

    name_entry = Gtk.Entry()
    name_entry.set_placeholder_text("Leave empty to use filename")
    custom_box.pack_start(name_entry, False, False, 0)

    url_status_label = Gtk.Label(label="")
    url_status_label.set_line_wrap(True)
    url_status_label.set_justify(Gtk.Justification.CENTER)
    custom_box.pack_start(url_status_label, False, False, 10)

    install_custom_btn = Gtk.Button(label="Install from URL")
    install_custom_btn.set_size_request(200, -1)
    btn_align = Gtk.Alignment(xalign=0.5)
    btn_align.add(install_custom_btn)
    custom_box.pack_start(btn_align, False, False, 0)

    notebook.append_page(custom_box, Gtk.Label(label="🔗 Custom URL"))

    def render_plugins(filter_text=""):
        """Render filtered plugin list."""
        for child in plugin_list_box.get_children():
            plugin_list_box.remove(child)

        filtered = [
            p for p in plugins
            if filter_text.lower() in p["name"].lower()
            or filter_text.lower() in p["description"].lower()
            or any(filter_text.lower() in t for t in p.get("tags", []))
        ] if filter_text else plugins

        if not filtered:
            plugin_list_box.pack_start(Gtk.Label(label="No plugins found."), False, False, 20)
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

                tags = "  ".join([f"#{t}" for t in plugin.get("tags", [])])
                if tags:
                    tags_label = Gtk.Label()
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
        """Handle install/uninstall action."""
        if do_install:
            status_label.set_text(f"Installing {plugin['name']}...")
            success, msg = install_plugin(plugin)
        else:
            status_label.set_text(f"Uninstalling {plugin['name']}...")
            success, msg = uninstall_plugin(plugin)
        status_label.set_text(msg)
        render_plugins(search_entry.get_text())

    def on_install_custom():
        """Handle custom URL installation."""
        url = url_entry.get_text().strip()
        name = name_entry.get_text().strip() or None
        
        if not url:
            url_status_label.set_text("❌ Please enter a GitHub URL")
            return
        
        url_status_label.set_text("⏳ Installing from URL...")
        success, msg = install_plugin_from_url(url, name)
        url_status_label.set_text(msg)
        
        if success:
            url_entry.set_text("")
            name_entry.set_text("")

    # Connect signals
    search_entry.connect("changed", lambda e: render_plugins(e.get_text()))
    install_custom_btn.connect("clicked", lambda b: on_install_custom())
    
    render_plugins()
    win.show_all()
    Gtk.main()


def hub_run(procedure, run_mode, image, drawables, config, data):
    """Main plugin entry point."""
    plugins = fetch_registry()
    if not plugins:
        GimpUi.init(plug_in_binary)
        dialog = Gtk.MessageDialog(
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Could not load plugin registry.\nCheck your internet connection."
        )
        dialog.run()
        dialog.destroy()
    else:
        build_ui(plugins)
    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, None)


class PluginHub(Gimp.PlugIn):
    """GIMP Plugin Hub main class."""
    
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
            "Browse and install GIMP plugins from registry or custom GitHub URLs",
            "GIMP Plugin Hub - Manage your GIMP plugins with ease",
            None
        )
        procedure.set_attribution("LeeWAITHIRA", "LeeWAITHIRA", "2026")
        return procedure


Gimp.main(PluginHub.__gtype__, sys.argv)
