#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# GIMP Generative Fill - By LeeWAITHIRA
# Photoshop-like generative fill powered by Pollinations.AI (free, no key)
# github.com/LeeWAITHIRA/gimp-plugin-hub

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('GimpUi', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gimp, GimpUi, Gtk, GLib, GObject, Gio
import sys
import os
import urllib.request
import urllib.parse
import tempfile
import time

plug_in_proc   = "plug-in-gimp-gen-fill"
plug_in_binary = "gimp_gen_fill"


def get_selection_bounds(image):
    result = Gimp.Selection.bounds(image)
    # GIMP 3.x returns (success, non_empty, x1, y1, x2, y2)
    _, non_empty, x1, y1, x2, y2 = result
    if not non_empty or (x2 - x1) < 4 or (y2 - y1) < 4:
        return None
    return x1, y1, x2 - x1, y2 - y1


def paste_image_as_layer(image, img_bytes, x, y, w, h):
    """Write image bytes to temp file and paste as new layer."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(img_bytes)
        tmppath = f.name

    # GIMP 3.x requires a Gio.File object, not a string path
    gio_file = Gio.File.new_for_path(tmppath)
    tmp_image = Gimp.file_load(
        Gimp.RunMode.NONINTERACTIVE,
        gio_file
    )

    # GIMP 3.x: use get_selected_drawables() which returns a list
    drawables = tmp_image.get_selected_drawables()
    tmp_drawable = drawables[0] if drawables else None
    if tmp_drawable is None:
        os.unlink(tmppath)
        tmp_image.delete()
        raise RuntimeError("Could not get drawable from loaded image")

    new_layer = Gimp.Layer.new_from_drawable(tmp_drawable, image)
    new_layer.set_name("Gen Fill")
    image.insert_layer(new_layer, None, -1)
    new_layer.scale(w, h, False)
    new_layer.set_offsets(x, y)

    os.unlink(tmppath)
    tmp_image.delete()
    return new_layer


def show_dialog(procedure, image, drawable):
    GimpUi.init(plug_in_binary)

    dialog = Gtk.Dialog(title="Generative Fill")
    dialog.set_default_size(460, 300)
    dialog.set_border_width(14)

    content = dialog.get_content_area()
    content.set_spacing(10)

    # Header
    info = Gtk.Label()
    info.set_markup(
        "<big><b>Generative Fill</b></big>\n"
        "<small>Powered by Pollinations.AI (Flux) - 100% free, no account needed</small>"
    )
    info.set_justify(Gtk.Justification.CENTER)
    content.pack_start(info, False, False, 0)

    content.pack_start(Gtk.Separator(), False, False, 0)

    # Instructions
    tip = Gtk.Label()
    tip.set_markup("<small>1. Draw a selection on your image   2. Type a prompt   3. Click Generate</small>")
    tip.set_justify(Gtk.Justification.CENTER)
    content.pack_start(tip, False, False, 0)

    # Prompt
    prompt_label = Gtk.Label(label="Prompt:")
    prompt_label.set_halign(Gtk.Align.START)
    content.pack_start(prompt_label, False, False, 0)

    prompt_entry = Gtk.Entry()
    prompt_entry.set_placeholder_text("e.g. a mountain lake at sunset, photorealistic, 4k")
    content.pack_start(prompt_entry, False, False, 0)

    # Model selector
    model_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    model_label = Gtk.Label(label="Model:")
    model_combo = Gtk.ComboBoxText()
    for m in ["flux", "turbo", "flux-realism", "flux-anime", "flux-3d"]:
        model_combo.append_text(m)
    model_combo.set_active(0)
    model_box.pack_start(model_label, False, False, 0)
    model_box.pack_start(model_combo, False, False, 0)
    content.pack_start(model_box, False, False, 0)

    # Status
    status_label = Gtk.Label(label="Ready. Make a selection and enter a prompt.")
    status_label.set_line_wrap(True)
    status_label.set_justify(Gtk.Justification.CENTER)
    content.pack_start(status_label, False, False, 0)

    # Buttons
    btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    btn_box.set_halign(Gtk.Align.END)
    cancel_btn = Gtk.Button(label="Close")
    generate_btn = Gtk.Button(label="Generate")
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
            status_label.set_text("Please enter a prompt first.")
            return

        bounds = get_selection_bounds(image)
        if not bounds:
            status_label.set_text("No selection found. Use Rectangle or Lasso tool to make a selection.")
            return

        x, y, w, h = bounds
        model = model_combo.get_active_text()
        generate_btn.set_sensitive(False)
        cancel_btn.set_sensitive(False)

        def update(msg):
            status_label.set_text(msg)
            while Gtk.events_pending():
                Gtk.main_iteration()

        try:
            update(f"Generating {w}x{h} image with {model}... (5-15 seconds)")

            seed = int(time.time()) % 99999
            real_w = max(64, (min(w, 1024) // 64) * 64)
            real_h = max(64, (min(h, 1024) // 64) * 64)
            encoded = urllib.parse.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded}?width={real_w}&height={real_h}&model={model}&nologo=true&seed={seed}"

            req = urllib.request.Request(url, headers={"User-Agent": "GIMP-Plugin/1.0"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                img_bytes = resp.read()

            update("Pasting result as new layer...")
            image.undo_group_start()
            paste_image_as_layer(image, img_bytes, x, y, w, h)
            image.undo_group_end()
            Gimp.displays_flush()

            update("Done! New 'Gen Fill' layer added. Use Ctrl+Z to undo.")
            generate_btn.set_sensitive(True)
            cancel_btn.set_sensitive(True)

        except Exception as e:
            update(f"Error: {str(e)}")
            generate_btn.set_sensitive(True)
            cancel_btn.set_sensitive(True)

    cancel_btn.connect("clicked", on_cancel)
    generate_btn.connect("clicked", on_generate)
    Gtk.main()


def gen_fill_run(procedure, run_mode, image, drawables, config, data):
    # GIMP 3.x: drawables is already a list passed by GIMP directly.
    # If empty, fall back to image.get_selected_drawables()
    if drawables:
        drawable = drawables[0]
    else:
        selected = image.get_selected_drawables()
        drawable = selected[0] if selected else None

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
        procedure.set_menu_label("Generative Fill")
        procedure.add_menu_path("<Image>/Filters")
        procedure.set_documentation(
            "AI Generative Fill powered by Pollinations.AI",
            "Select an area, type a prompt, generate AI content instantly",
            None
        )
        procedure.set_attribution("LeeWAITHIRA", "LeeWAITHIRA", "2026")
        return procedure


Gimp.main(GenFill.__gtype__, sys.argv)