#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# GIMP Generative Fill - By LeeWAITHIRA
# Photoshop-like generative fill powered by Stable Horde (free)
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
import tempfile
import time

HORDE_API     = "https://stablehorde.net/api/v2"
HORDE_API_KEY = "0000000000"

plug_in_proc   = "plug-in-gimp-gen-fill"
plug_in_binary = "gimp_gen_fill"


def do_set_i18n(self, name):
    return False


def get_selection_bounds(image):
    result = Gimp.Selection.bounds(image)
    # returns (success, non_empty, x1, y1, x2, y2)
    _, non_empty, x1, y1, x2, y2 = result
    if not non_empty or (x2 - x1) < 4 or (y2 - y1) < 4:
        return None
    return x1, y1, x2 - x1, y2 - y1
def submit_horde_job(prompt, width, height):
    """Submit generation job to Stable Horde."""
    w = max(64, (min(width,  512) // 64) * 64)
    h = max(64, (min(height, 512) // 64) * 64)
    payload = {
        "prompt": prompt,
        "params": {
            "width": w,
            "height": h,
            "steps": 25,
            "cfg_scale": 7.5,
            "sampler_name": "k_euler_a",
            "n": 1
        },
        "models": ["stable_diffusion"],
        "r2": True
    }
    req = urllib.request.Request(
        f"{HORDE_API}/generate/async",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "apikey": HORDE_API_KEY
        }
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["id"]


def poll_horde_job(job_id, status_callback):
    """Poll until job done, return image URL."""
    for i in range(120):
        time.sleep(3)
        with urllib.request.urlopen(
            f"{HORDE_API}/generate/check/{job_id}", timeout=10
        ) as resp:
            data = json.loads(resp.read())
        qp = data.get('queue_position', '?')
        wt = data.get('wait_time', '?')
        status_callback(f"Generating... queue: {qp} | wait: ~{wt}s")
        if data.get("done"):
            break

    with urllib.request.urlopen(
        f"{HORDE_API}/generate/status/{job_id}", timeout=10
    ) as resp:
        result = json.loads(resp.read())

    generations = result.get("generations", [])
    if not generations:
        return None
    return generations[0].get("img")


def download_image_to_layer(image, img_url, x, y, w, h):
    """Download result and paste as new layer."""
    with tempfile.NamedTemporaryFile(suffix=".webp", delete=False) as f:
        tmppath = f.name
    urllib.request.urlretrieve(img_url, tmppath)

    tmp_image = Gimp.file_load(
        Gimp.RunMode.NONINTERACTIVE,
        Gimp.get_default_comment(),
        tmppath
    )
    tmp_drawable = tmp_image.get_active_drawable()
    tmp_layer = Gimp.Layer.new_from_drawable(tmp_drawable, image)
    tmp_layer.set_name("✨ Gen Fill")
    image.insert_layer(tmp_layer, None, -1)
    tmp_layer.scale(w, h, False)
    tmp_layer.set_offsets(x, y)

    os.unlink(tmppath)
    tmp_image.delete()
    return tmp_layer


def show_dialog(procedure, image, drawable):
    GimpUi.init(plug_in_binary)

    dialog = Gtk.Dialog(title="✨ Generative Fill")
    dialog.set_default_size(440, 260)
    dialog.set_border_width(12)

    content = dialog.get_content_area()
    content.set_spacing(10)

    info = Gtk.Label()
    info.set_markup("<big><b>✨ Generative Fill</b></big>\n<small>Powered by Stable Horde — 100% free, no account needed</small>")
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
        generate_btn.set_sensitive(False)
        cancel_btn.set_sensitive(False)
        status_label.set_text(f"Selection: {w}x{h}px at ({x},{y})")

        def update_status(msg):
            status_label.set_text(msg)
            while Gtk.events_pending():
                Gtk.main_iteration()

        try:
            update_status("📤 Submitting to Stable Horde...")
            job_id = submit_horde_job(prompt, w, h)
            update_status(f"✅ Job submitted! Waiting for worker...")

            img_url = poll_horde_job(job_id, update_status)

            if not img_url:
                update_status("❌ Generation failed — no result returned. Try again.")
                generate_btn.set_sensitive(True)
                cancel_btn.set_sensitive(True)
                return

            update_status("⬇️ Downloading result...")
            image.undo_group_start()
            download_image_to_layer(image, img_url, x, y, w, h)
            image.undo_group_end()
            Gimp.displays_flush()
            update_status("✅ Done! Check the new '✨ Gen Fill' layer in your layers panel.")

        except Exception as e:
            update_status(f"❌ Error: {str(e)}")
            generate_btn.set_sensitive(True)
            cancel_btn.set_sensitive(True)

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
            "AI Generative Fill powered by Stable Horde",
            "Select an area, type a prompt, generate AI content",
            None
        )
        procedure.set_attribution("LeeWAITHIRA", "LeeWAITHIRA", "2026")
        return procedure


Gimp.main(GenFill.__gtype__, sys.argv)