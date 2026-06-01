#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# GIMP Plugin Hub & AI Generator - By LeeWAITHIRA
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
import urllib.parse
import shutil
import threading

REGISTRY_URL = "https://raw.githubusercontent.com/LeeWAITHIRA/gimp-plugin-hub/main/registry/plugins.json"
GIMP_PLUGINS_DIR = os.path.join(os.environ.get("APPDATA", ""), "GIMP", "3.2", "plug-ins")
GIMP_PYTHON = os.path.join(os.path.dirname(sys.executable), "python.exe")

plug_in_proc   = "plug-in-gimp-plugin-hub"
plug_in_binary = "hub"


def patch_shebang(filepath):
    """Replace first line with correct GIMP Python path."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        if lines and lines[0].startswith('#!'):
            lines[0] = f'#!{GIMP_PYTHON}\n'
        else:
            lines.insert(0, f'#!{GIMP_PYTHON}\n')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    except Exception:
        pass


def fetch_registry():
    """Fetches the plugin registry with custom headers to prevent CDN timeouts."""
    try:
        req = urllib.request.Request(
            REGISTRY_URL,
            headers={'User-Agent': 'Mozilla/5.0 (GIMP-Plugin-Hub/1.0; Python Plugin)'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
            return data.get("plugins", [])
    except Exception:
        return []


def get_plugin_folder(plugin):
    """Folder name must match .py filename exactly for GIMP 3."""
    filename = plugin["download_url"].split("/")[-1]
    return filename.replace(".py", ""), filename


def install_plugin(plugin):
    """Downloads files over a secure request stream with custom headers."""
    try:
        folder_name, filename = get_plugin_folder(plugin)
        plugin_dir = os.path.join(GIMP_PLUGINS_DIR, folder_name)
        os.makedirs(plugin_dir, exist_ok=True)
        dest = os.path.join(plugin_dir, filename)
        
        req = urllib.request.Request(
            plugin["download_url"],
            headers={'User-Agent': 'Mozilla/5.0 (GIMP-Plugin-Hub/1.0; Python Plugin)'}
        )
        with urllib.request.urlopen(req, timeout=30) as response, open(dest, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
            
        patch_shebang(dest)
        return True, f"✅ {plugin['name']} installed!\nRestart GIMP to use it."
    except Exception as e:
        return False, f"❌ Install failed: {str(e)}"


def uninstall_plugin(plugin):
    try:
        folder_name, _ = get_plugin_folder(plugin)
        plugin_dir = os.path.join(GIMP_PLUGINS_DIR, folder_name)
        if os.path.exists(plugin_dir):
            shutil.rmtree(plugin_dir)
            return True, f"🗑️ {plugin['name']} uninstalled.\nRestart GIMP to apply."
        return False, "Plugin not found on disk."
    except Exception as e:
        return False, str(e)


def is_installed(plugin):
    folder_name, _ = get_plugin_folder(plugin)
    return os.path.exists(os.path.join(GIMP_PLUGINS_DIR, folder_name))


def build_ui():
    GimpUi.init(plug_in_binary)
    win = Gtk.Window(title="GIMP Plugin Hub & AI Suite")
    win.set_default_size(700, 600)
    win.set_border_width(12)
    win.connect("destroy", Gtk.main_quit)

    # Main structural Layout Wrapper
    root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    win.add(root_box)

    # Global Title Header
    header = Gtk.Label()
    header.set_markup("<big><b>🧩 GIMP Creator Toolkit</b></big>\n<small>Plugin Management & Generative AI Hub</small>")
    header.set_justify(Gtk.Justification.CENTER)
    root_box.pack_start(header, False, False, 6)

    # Notebook Container for separating Hub and AI features
    notebook = Gtk.Notebook()
    root_box.pack_start(notebook, True, True, 0)

    # ==========================================
    # TAB 1: PLUGIN HUB CONTAINER SETUP
    # ==========================================
    hub_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    hub_page.set_border_width(10)

    search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    search_label = Gtk.Label(label="🔍 Search:")
    search_entry = Gtk.Entry()
    search_entry.set_placeholder_text("Search by name, tag, or description...")
    search_box.pack_start(search_label, False, False, 0)
    search_box.pack_start(search_entry, True, True, 0)
    hub_page.pack_start(search_box, False, False, 0)

    scroll = Gtk.ScrolledWindow()
    scroll.set_min_content_height(340)
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    plugin_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    scroll.add(plugin_list_box)
    hub_page.pack_start(scroll, True, True, 0)

    status_label = Gtk.Label(label="🔄 Synchronization active: Loading online database...")
    status_label.set_line_wrap(True)
    status_label.set_justify(Gtk.Justification.CENTER)
    hub_page.pack_start(status_label, False, False, 4)

    notebook.append_page(hub_page, Gtk.Label(label="🧩 Plugin Manager"))

    # ==========================================
    # TAB 2: AI GENERATOR CONTAINER SETUP
    # ==========================================
    ai_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    ai_page.set_border_width(14)

    prompt_label = Gtk.Label(label="<b>Describe the image you want to generate:</b>")
    prompt_label.set_use_markup(True)
    prompt_label.set_halign(Gtk.Align.START)
    ai_page.pack_start(prompt_label, False, False, 0)

    prompt_entry = Gtk.Entry()
    prompt_entry.set_placeholder_text("e.g., A surreal landscape with neon clouds, cinematic lighting, 8k resolution...")
    ai_page.pack_start(prompt_entry, False, False, 0)

    # Size adjustment configurations
    dim_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
    
    width_lbl = Gtk.Label(label="Width:")
    width_spin = Gtk.SpinButton.new_with_range(256, 2048, 64)
    width_spin.set_value(1024)
    dim_box.pack_start(width_lbl, False, False, 0)
    dim_box.pack_start(width_spin, False, False, 0)

    height_lbl = Gtk.Label(label="Height:")
    height_spin = Gtk.SpinButton.new_with_range(256, 2048, 64)
    height_spin.set_value(1024)
    dim_box.pack_start(height_lbl, False, False, 0)
    dim_box.pack_start(height_spin, False, False, 0)

    ai_page.pack_start(dim_box, False, False, 4)

    # Model engine preferences selector
    model_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    model_lbl = Gtk.Label(label="AI Model Engine:")
    model_combo = Gtk.ComboBoxText()
    model_combo.append_text("flux")
    model_combo.append_text("turbo")
    model_combo.set_active(0)
    model_box.pack_start(model_lbl, False, False, 0)
    model_box.pack_start(model_combo, False, False, 0)
    ai_page.pack_start(model_box, False, False, 0)

    generate_btn = Gtk.Button(label="✨ Generate AI Image")
    ai_page.pack_start(generate_btn, False, False, 10)

    ai_status_label = Gtk.Label(label="Ready to generate artwork pipeline. No active tasks.")
    ai_status_label.set_line_wrap(True)
    ai_status_label.set_justify(Gtk.Justification.CENTER)
    ai_page.pack_start(ai_status_label, False, False, 4)

    notebook.append_page(ai_page, Gtk.Label(label="✨ AI Text-to-Image"))

    # Global UI variable caching
    all_plugins = []

    # ==========================================
    # LOGIC COMPONENT: PLUGIN MANAGER METHODS
    # ==========================================
    def render_plugins(filter_text=""):
        for child in plugin_list_box.get_children():
            plugin_list_box.remove(child)

        filtered = [
            p for p in all_plugins
            if filter_text.lower() in p["name"].lower()
            or filter_text.lower() in p["description"].lower()
            or any(filter_text.lower() in t for t in p.get("tags", []))
        ] if filter_text else all_plugins

        if not all_plugins and status_label.get_text().startswith("🔄"):
            plugin_list_box.pack_start(Gtk.Label(label="Loading external database asset..."), False, False, 20)
        elif not filtered:
            plugin_list_box.pack_start(Gtk.Label(label="No plugins found matching criteria."), False, False, 20)
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
        if do_install:
            status_label.set_text(f"Installing {plugin['name']}...")
        else:
            status_label.set_text(f"Uninstalling {plugin['name']}...")

        def worker():
            if do_install:
                success, msg = install_plugin(plugin)
            else:
                success, msg = uninstall_plugin(plugin)
            GLib.idle_add(lambda: finish_action(msg))

        def finish_action(msg):
            status_label.set_text(msg)
            render_plugins(search_entry.get_text())
            return False

        threading.Thread(target=worker, daemon=True).start()

    def load_registry_worker():
        nonlocal all_plugins
        plugins = fetch_registry()
        
        def apply_registry():
            nonlocal all_plugins
            if plugins:
                all_plugins = plugins
                status_label.set_text("Registry loaded cleanly.")
            else:
                status_label.set_text("❌ Connection failed. Check internet access.")
            render_plugins(search_entry.get_text())
            return False
            
        GLib.idle_add(apply_registry)

    # ==========================================
    # LOGIC COMPONENT: GENERATIVE AI ENGINE
    # ==========================================
    def run_ai_generation(widget):
        prompt = prompt_entry.get_text().strip()
        if not prompt:
            ai_status_label.set_text("❌ Generation aborted: Prompt field cannot be empty.")
            return

        w = int(width_spin.get_value())
        h = int(height_spin.get_value())
        model = model_combo.get_active_text()

        generate_btn.set_sensitive(False)
        ai_status_label.set_text("🚀 Connecting to Pollinations cluster... Rendering image stream...")

        def ai_worker():
            try:
                # Sanitize the input prompt string into safely structured query components
                encoded_prompt = urllib.parse.quote(prompt)
                target_url = f"https://image.pollinations.ai/p/{encoded_prompt}?width={w}&height={h}&model={model}&nologo=true"
                
                req = urllib.request.Request(
                    target_url,
                    headers={'User-Agent': 'Mozilla/5.0 (GIMP-AI-Suite/1.0; GIMP Plugin)'}
                )
                
                # Determine default save destination directory
                user_home = os.path.expanduser("~")
                save_dir = os.path.join(user_home, "Pictures")
                if not os.path.exists(save_dir):
                    save_dir = user_home
                
                out_filename = f"ai_gen_{int(GLib.get_real_time() / 1000000)}.png"
                destination_path = os.path.join(save_dir, out_filename)

                # Connect directly to stream bytes straight down into a clean file output
                with urllib.request.urlopen(req, timeout=45) as response, open(destination_path, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)

                msg = f"🎉 Success! Image generated and exported to:\n{destination_path}"
                GLib.idle_add(lambda: finalize_ai(True, msg))
            except Exception as error:
                GLib.idle_add(lambda: finalize_ai(False, f"❌ Cloud render engine timed out: {str(error)}"))

        def finalize_ai(success, outcome_text):
            ai_status_label.set_text(outcome_text)
            generate_btn.set_sensitive(True)
            return False

        threading.Thread(target=ai_worker, daemon=True).start()

    # Event binding configurations
    search_entry.connect("changed", lambda e: render_plugins(e.get_text()))
    generate_btn.connect("clicked", run_ai_generation)
    
    render_plugins()
    win.show_all()
    
    # Asynchronously loads the external hub plugin library metadata
    threading.Thread(target=load_registry_worker, daemon=True).start()
    Gtk.main()


def hub_run(procedure, run_mode, image, drawables, config, data):
    build_ui()
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
        procedure.set_menu_label("Plugin Hub & AI Suite")
        procedure.add_menu_path("<Image>/Filters")
        procedure.set_documentation(
            "Browse assets and execute AI tasks inside GIMP",
            "GIMP Plugin Hub & AI Suite by LeeWAITHIRA",
            None
        )
        procedure.set_attribution("LeeWAITHIRA", "LeeWAITHIRA", "2026")
        return procedure


Gimp.main(PluginHub.__gtype__, sys.argv)