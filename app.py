"""GMod PM Proportion Tool — GUI Application

A standalone tool for generating CaptainBigButt's Proportion Trick
files for Garry's Mod playermodels.

Select a decompiled QC file, click Generate, paste the QC snippet,
recompile. No Blender required.
"""

import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from generator import __version__, analyze_qc, generate_files, AnalysisResult


# ------------------------------------------------------------------
# Application
# ------------------------------------------------------------------

class ProportionToolApp(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title(f"GMod PM Proportion Tool v{__version__}")
        self.geometry("820x720")
        self.minsize(650, 550)

        # State
        self._qc_path = tk.StringVar()
        self._output_dir = tk.StringVar()
        self._analysis: AnalysisResult | None = None
        self._last_browse_dir = None

        self._build_ui()
        self._set_status("Ready — select a decompiled QC file to begin.")

    # ---- UI construction ----

    def _build_ui(self):
        # Main container with padding
        main = ttk.Frame(self, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        self._build_input_section(main)
        self._build_analysis_section(main)
        self._build_buttons(main)
        self._build_log_section(main)
        self._build_status_bar()

    def _build_input_section(self, parent):
        frame = ttk.LabelFrame(parent, text=" Model ", padding=(10, 6))
        frame.pack(fill=tk.X, pady=(0, 8))

        # QC file row
        ttk.Label(frame, text="QC File:").grid(row=0, column=0, sticky=tk.W, padx=(0, 8))
        qc_entry = ttk.Entry(frame, textvariable=self._qc_path)
        qc_entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 6))
        ttk.Button(frame, text="Browse...", width=10, command=self._browse_qc).grid(row=0, column=2)

        # Output dir row
        ttk.Label(frame, text="Output:").grid(row=1, column=0, sticky=tk.W, padx=(0, 8), pady=(6, 0))
        out_entry = ttk.Entry(frame, textvariable=self._output_dir)
        out_entry.grid(row=1, column=1, sticky=tk.EW, padx=(0, 6), pady=(6, 0))
        ttk.Button(frame, text="Browse...", width=10, command=self._browse_output).grid(row=1, column=2, pady=(6, 0))

        frame.columnconfigure(1, weight=1)

    def _build_analysis_section(self, parent):
        frame = ttk.LabelFrame(parent, text=" Skeleton Analysis ", padding=(10, 6))
        frame.pack(fill=tk.BOTH, pady=(0, 8))

        self._analysis_text = tk.Text(
            frame, height=8, wrap=tk.WORD, state=tk.DISABLED,
            font=("Consolas", 9), bg="#f8f8f8", relief=tk.FLAT,
            borderwidth=1,
        )
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self._analysis_text.yview)
        self._analysis_text.configure(yscrollcommand=scrollbar.set)

        self._analysis_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Tag styles
        self._analysis_text.tag_configure("header", font=("Consolas", 9, "bold"))
        self._analysis_text.tag_configure("good", foreground="#2e7d32")
        self._analysis_text.tag_configure("warn", foreground="#e65100")
        self._analysis_text.tag_configure("dim", foreground="#757575")

    def _build_buttons(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(0, 8))

        self._gen_btn = ttk.Button(
            frame, text="  Generate Proportion Files  ",
            command=self._generate, state=tk.DISABLED,
        )
        self._gen_btn.pack(side=tk.LEFT)

        self._copy_btn = ttk.Button(
            frame, text="  Copy QC Snippet  ",
            command=self._copy_snippet, state=tk.DISABLED,
        )
        self._copy_btn.pack(side=tk.LEFT, padx=(8, 0))

        self._open_btn = ttk.Button(
            frame, text="  Open Output Folder  ",
            command=self._open_output, state=tk.DISABLED,
        )
        self._open_btn.pack(side=tk.LEFT, padx=(8, 0))

    def _build_log_section(self, parent):
        frame = ttk.LabelFrame(parent, text=" Log ", padding=(10, 6))
        frame.pack(fill=tk.BOTH, expand=True)

        self._log_text = tk.Text(
            frame, height=10, wrap=tk.WORD, state=tk.DISABLED,
            font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4",
            insertbackground="#d4d4d4", relief=tk.FLAT, borderwidth=1,
        )
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=scrollbar.set)

        self._log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Tag styles for colored log
        self._log_text.tag_configure("info", foreground="#9cdcfe")
        self._log_text.tag_configure("done", foreground="#6a9955")
        self._log_text.tag_configure("warn", foreground="#ce9178")
        self._log_text.tag_configure("error", foreground="#f44747")

    def _build_status_bar(self):
        self._status = ttk.Label(
            self, text="", relief=tk.SUNKEN, anchor=tk.W, padding=(8, 4),
        )
        self._status.pack(side=tk.BOTTOM, fill=tk.X)

    # ---- Actions ----

    def _browse_qc(self):
        initial = self._last_browse_dir or os.path.expanduser("~\\Desktop")
        path = filedialog.askopenfilename(
            title="Select Decompiled QC File",
            initialdir=initial,
            filetypes=[("QC Files", "*.qc"), ("All Files", "*.*")],
        )
        if not path:
            return

        self._qc_path.set(path)
        self._output_dir.set(os.path.dirname(path))
        self._last_browse_dir = os.path.dirname(path)
        self._snippet_text = None
        self._copy_btn.configure(state=tk.DISABLED)
        self._open_btn.configure(state=tk.DISABLED)
        self._analyze()

    def _browse_output(self):
        initial = self._output_dir.get() or os.path.expanduser("~\\Desktop")
        d = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=initial,
        )
        if d:
            self._output_dir.set(d)

    def _analyze(self):
        qc = self._qc_path.get().strip()
        if not qc:
            return

        self._set_status("Analyzing...")
        self._clear_analysis()
        self._clear_log()

        try:
            self._analysis = analyze_qc(qc)
        except FileNotFoundError as e:
            self._write_analysis(str(e), "warn")
            self._gen_btn.configure(state=tk.DISABLED)
            self._set_status("Error: QC file not found.")
            return
        except ValueError as e:
            self._write_analysis(str(e), "warn")
            self._gen_btn.configure(state=tk.DISABLED)
            self._set_status("Error: no $definebone lines in QC.")
            return

        a = self._analysis

        self._write_analysis(f"Model: {a.model_name}\n", "header")
        self._write_analysis(f"Total bones: {a.total_bones}\n")
        self._write_analysis(f"Matched ValveBiped: {a.matched_count}\n",
                             "good" if a.matched_count > 0 else "warn")
        self._write_analysis(f"Custom bones: {a.custom_count}\n")
        self._write_analysis(f"IK Chains: {'detected' if a.has_ikchains else 'not found'}\n",
                             "dim")

        if a.matched_count > 0:
            self._write_analysis(f"\nMatched bones:\n", "header")
            for name in a.matched_bones:
                self._write_analysis(f"  {name}\n", "good")

        if a.custom_count > 0:
            self._write_analysis(f"\nCustom bones (not in proportion trick):\n", "header")
            for name in a.custom_bones:
                self._write_analysis(f"  {name}\n", "dim")

        self._gen_btn.configure(state=tk.NORMAL)
        self._set_status(
            f"Analysis complete — {a.matched_count} matched, "
            f"{a.custom_count} custom. Ready to generate."
        )

    def _generate(self):
        qc = self._qc_path.get().strip()
        output = self._output_dir.get().strip()

        if not qc or not output:
            messagebox.showwarning("Missing Input", "Please select a QC file and output directory.")
            return

        self._clear_log()
        self._set_status("Generating...")
        self._gen_btn.configure(state=tk.DISABLED)
        self.update_idletasks()

        try:
            result = generate_files(qc, output, log_callback=self._log)
        except Exception as e:
            self._log(f'[ERROR] {e}')
            self._set_status(f"Error: {e}")
            self._gen_btn.configure(state=tk.NORMAL)
            return

        self._snippet_text = result.snippet_text
        self._gen_btn.configure(state=tk.NORMAL)
        self._copy_btn.configure(state=tk.NORMAL)
        self._open_btn.configure(state=tk.NORMAL)
        self._set_status(
            f"Done! {result.bone_count} bones — files saved to {output}"
        )

    def _copy_snippet(self):
        if not getattr(self, '_snippet_text', None):
            return
        self.clipboard_clear()
        self.clipboard_append(self._snippet_text)
        self._set_status("QC snippet copied to clipboard.")

    def _open_output(self):
        output = self._output_dir.get().strip()
        if output and os.path.isdir(output):
            if sys.platform == 'win32':
                os.startfile(output)
            elif sys.platform == 'darwin':
                subprocess.run(['open', output])
            else:
                subprocess.run(['xdg-open', output])

    # ---- Helpers ----

    def _log(self, msg: str):
        """Append a line to the log with color coding."""
        tag = None
        if msg.startswith('[DONE]'):
            tag = 'done'
        elif msg.startswith('[INFO]'):
            tag = 'info'
        elif msg.startswith('[WARN]'):
            tag = 'warn'
        elif msg.startswith('[ERROR]'):
            tag = 'error'

        self._log_text.configure(state=tk.NORMAL)
        self._log_text.insert(tk.END, msg + '\n', tag or ())
        self._log_text.see(tk.END)
        self._log_text.configure(state=tk.DISABLED)
        self.update_idletasks()

    def _clear_log(self):
        self._log_text.configure(state=tk.NORMAL)
        self._log_text.delete('1.0', tk.END)
        self._log_text.configure(state=tk.DISABLED)

    def _write_analysis(self, text: str, tag: str = None):
        self._analysis_text.configure(state=tk.NORMAL)
        self._analysis_text.insert(tk.END, text, tag or ())
        self._analysis_text.configure(state=tk.DISABLED)

    def _clear_analysis(self):
        self._analysis_text.configure(state=tk.NORMAL)
        self._analysis_text.delete('1.0', tk.END)
        self._analysis_text.configure(state=tk.DISABLED)

    def _set_status(self, msg: str):
        self._status.configure(text=msg)


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def main():
    app = ProportionToolApp()
    app.mainloop()


if __name__ == '__main__':
    main()
