#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# GIMP Generative Fill - By LeeWAITHIRA
# Photoshop-like generative fill powered by Pollinations AI (free)
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
import tempfile
import shutil
import threading

plug_in_proc   = "plug-in-gimp-gen-fill"
plug_in_binary = "gimp_gen_fill"


def do_set_i18n(self, name):
    return False


def get_selection_bounds(image):
    """Get selection bounds using correct GIMP 3 API."""
    non_empty, x1, y1, x2, y2 = Gimp.Selection.bounds(image)
    if not non_empty or (x2 - x1) < 4 or (y2 - y1) < 4:
        return None
    return x1, y1, x2 - x1, y2 - y1


def show_dialog(procedure, image, drawable):
    GimpUi.init(plug_in_binary)

    dialog = Gtk.Dialog(title="✨ Generative Fill")
    dialog.set_default_size(440, 260)
    dialog.set_border_width(12)

    content = dialog.get_content_area()
    content.set_spacing(10)

    info = Gtk.Label()
    info.set_markup("<big><b>✨ Generative Fill</b></big>\n<small>Powered by Pollinations AI — 100% free, instantaneous pipeline</small>")
    info.set_justify(Gtk.Justification.CENTER)
    content.pack_start(info, False, False, 0)

    sep = Gtk.Separator()
    content.pack_start(sep, False, False, 0)

    prompt_label = Gtk.Label(label="Describe what to generate in the selected area:")
    prompt_label.set_halign(Gtk.Align.START)
    content.pack_start(prompt_label, False, False, 0)

    prompt_entry = Gtk.Entry()
    prompt_entry.set_placeholder_text("e.g. a blue sky with clouds, photorealistic")
    content.pack_start(prompt_entry, False, False, 0)

    status_label = Gtk.Label(label="💡 Tip: Make a selection first using the Rectangle or Lasso tool.")
    status_label.set_line_wrap(True)
    status_label.set_justify(Gtk.Justification.CENTER)
    content.pack_start(status_label, False, False, 0)

    btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    btn_box.set_halign(Gtk.Align.END)
    cancel_btn = Gtk.Button(label="Cancel")
    generate_btn = Gtk.Button(label="✨ Generate")
    btn_box.pack_start(cancel_btn, False, False, 0)
    btn_box.pack_start(generate_btn, False, False, 0)
    content.pack_start(btn_box, False, False, 8)

    dialog.show_all()

    def on_cancel(b):
        dialog.destroy()
        Gtk.main_quit()

    def on_generate(b):
        prompt = prompt_entry.get_text().strip()
        if not prompt:
            status_label.set_text("⚠️ Please enter a prompt first.")
            return

        bounds = get_selection_bounds(image)
        if not bounds:
            status_label.set_text("⚠️ No selection found. Draw a rectangle or lasso selection first.")
            return

        x, y, w, h = bounds
        
        # Clamp generation parameters to safety thresholds optimized for modern base weights
        gen_w = max(256, min(w, 1440))
        gen_h = max(256, min(h, 1440))

        generate_btn.set_sensitive(False)
        cancel_btn.set_sensitive(False)
        status_label.set_text("🚀 Handshaking with cloud render pipeline... Please wait...")

        def network_worker():
            try:
                # Sanitize the textual string into URL-safe UTF-8 format
                encoded_prompt = urllib.parse.quote(prompt)
                target_url = f"https://image.pollinations.ai/p/{encoded_prompt}?width={gen_w}&height={gen_h}&model=flux&nologo=true"
                
                req = urllib.request.Request(
                    target_url,
                    headers={'User-Agent': 'Mozilla/5.0 (GIMP-Gen-Fill/1.0; Python Plugin)'}
                )
                
                # Allocate a clean temporary path file inside the system cache container
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                    tmppath = f.name
                
                # Directly pipe cloud bytes down to disk storage
                with urllib.request.urlopen(req, timeout=45) as response, open(tmppath, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
                
                # Securely pass the downloaded tracking data assets back over to the main UI thread
                GLib.idle_add(lambda: process_gimp_layer(tmppath, x, y, w, h))
                
            except Exception as network_error:
                GLib.idle_add(lambda: display_fault(str(network_error)))

        def process_gimp_layer(tmppath, target_x, target_y, target_w, target_h):
            try:
                status_label.set_text("⬇️ Processing binary data... Constructing new layer element...")
                image.undo_group_start()
                
                # Load temporary file directly via virtual system space context
                tmp_image = Gimp.file_load(
                    Gimp.RunMode.NONINTERACTIVE,
                    Gimp.get_default_comment(),
                    tmppath
                )
                tmp_drawable = tmp_image.get_active_drawable()
                
                # Extract and map raw image data layout objects cleanly onto current document context
                tmp_layer = Gimp.Layer.new_from_drawable(tmp_drawable, image)
                tmp_layer.set_name(f"✨ Gen Fill: {prompt[:15]}")
                image.insert_layer(tmp_layer, None, -1)
                
                # Rescale and align layout constraints precisely to selection boundaries
                tmp_layer.scale(target_w, target_h, False)
                tmp_layer.set_offsets(target_x, target_y)
                
                image.undo_group_end()
                Gimp.displays_flush()
                
                status_label.set_text("✅ Done! Check your layers panel for the new generation.")
                
                # Clear references out of disk cache safely
                os.unlink(tmppath)
                tmp_image.delete()
                
            except Exception as core_error:
                status_label.set_text(f"❌ GIMP Core Pipeline Error: {str(core_error)}")
            finally:
                generate_btn.set_sensitive(True)
                cancel_btn.set_sensitive(True)
            return False

        def display_fault(error_text):
            status_label.set_text(f"❌ Network request dropped: {error_text}")
            generate_btn.set_sensitive(True)
            cancel_btn.set_sensitive(True)
            return False

        # Execute network functions outside the GUI loop inside a daemonized system component
        threading.Thread(target=network_worker, daemon=True).start()

    cancel_btn.connect("clicked", on_cancel)
    generate_btn.connect("clicked", on_generate)
    Gtk.main()


def gen_fill_run(procedure, run_mode, image, drawables, config, data):
    drawable = drawables[0] if drawables else image.get_active_drawable()
    show_dialog(procedure, image, drawable)
    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, None)


class GenFill(Gimp.PlugIn):
    def do_query_procedures(self):
        return [plug_in_proc]

    def do_set_i18n(self, name):
        return False

    def do_create_procedure(self, name):
        procedure = Gimp.ImageProcedure.new(
            self, name, Gimp.PDBProcType.PLUGIN, gen_fill_run, None
        )
        procedure.set_sensitivity_mask(
            Gimp.ProcedureSensitivityMask.DRAWABLE |
            Gimp.ProcedureSensitivityMask.NO_DRAWABLES
        )
        procedure.set_menu_label("✨ Generative Fill")
        procedure.add_menu_path("<Image>/Filters")
        procedure.set_documentation(
            "AI Generative Fill powered by Pollinations AI",
            "Select an area, type a prompt, generate instant AI imagery on a new canvas layer",
            None
        )
        procedure.set_attribution("LeeWAITHIRA", "LeeWAITHIRA", "2026")
        return procedure


Gimp.main(GenFill.__gtype__, sys.argv)