import os
import pandas as pd
import time
from tkinter import Tk, Label, Entry, Button, Canvas, filedialog, StringVar
from tkinter import ttk
from PIL import Image, ImageTk

class ImageApp:
    def __init__(self, master):
        self.master = master
        self.master.title("IHM Classification d'Images LaPoste")
        self.master.geometry("1200x800")
        self.master.configure(bg="white")

        self.image_folder = None
        self.excel_file = None
        self.df = None
        self.image_files = []
        self.current_index = 0
        self.rotation_angle = 0
        self.canvas_image = None
        self.entry_vars = {}
        self.entries = []
        self.zoom_factor= 1.0
        self.flipped = False
        self.counter_var = StringVar()

        self.date = None
        self.filter_value= None
        self.filtered_indices = []
        self.start_time = time.time()
        self.time_spent = []
        self.last_time = time.time()

        self.create_widgets()
        self.bind_keys()

    def create_widgets(self):
        # Zone image (gauche)
        self.image_frame = ttk.LabelFrame(self.master, text="Image à classer", padding=10)
        self.image_frame.grid(row=0, column=0, rowspan=4, padx=10, pady=10, sticky="nsew")

        self.canvas = Canvas(self.image_frame, width=900, height=600, bg="gray")
        self.canvas.pack()
        self.canvas.config(xscrollincrement=1, yscrollincrement=1)

        # Instructions clavier
        self.info_frame = ttk.LabelFrame(self.master, text="Commandes clavier", padding=10)
        self.info_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")

        instructions = (
            "← Image précédente\n"
            "→ Image suivante\n"
            "↑ Rotation droite\n"
            "↓ Rotation gauche\n"
            "ESPACE : Inverser l'image horizontalement\n"
            "Touches : Ajouter commentaire et passer à l'image suivante\n"
            "a : présent\n"
            "z : absent\n"

        )
        Label(self.info_frame, text=instructions, justify="left").pack(anchor="w")

        # Données associées
        self.data_frame = ttk.LabelFrame(self.master, text="Données associées", padding=10)
        self.data_frame.grid(row=2, column=1, padx=10, pady=5, sticky="nsew")

        # Stats
        self.stats_frame = ttk.LabelFrame(self.master, text="Statistiques", padding=10)
        self.stats_frame.grid(row=3, column=1, padx=10, pady=5, sticky="nsew")

        self.stats_label = Label(self.stats_frame, text="", justify="left")
        self.stats_label.pack(anchor="w")

        # menu filtre + stats combiné
        filter_combined_frame = ttk.LabelFrame(self.master, text="Filtre (par commentaire)", padding=10)
        filter_combined_frame.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        self.filter_var = StringVar(value="Tous")
        self.filter_menu = ttk.OptionMenu(filter_combined_frame, self.filter_var, "Tous", command=self.apply_filter)
        self.filter_menu.grid(row=0, column=0, sticky="w")

        # Compteur avec total
        counter_frame = ttk.Frame(self.master)
        counter_frame.grid(row=3, column=1, pady=10)

        self.counter_var = StringVar()
        self.counter_entry = Entry(counter_frame, textvariable=self.counter_var, width=6, justify="center",
                                   font=("Arial", 10))
        self.counter_entry.pack(side="left")
        self.counter_entry.bind("<Return>", self.goto_image_by_number)

        self.total_label_var = StringVar(value="/0")
        self.total_label = Label(counter_frame, textvariable=self.total_label_var, font=("Arial", 10))
        self.total_label.pack(side="left", padx=(5, 0))

        #bind pour le zoom
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<ButtonPress-1>",self.start_pan)
        self.canvas.bind("<B1-Motion>",self.do_pan)

        # Configuration grille
        self.master.columnconfigure(0, weight=2)
        self.master.columnconfigure(1, weight=1)
        for i in range(4):
            self.master.rowconfigure(i, weight=1)

        self.image_offset_x = 0
        self.image_offset_y = 0


    def bind_keys(self):
        self.master.bind("<Left>", self.prev_image)
        self.master.bind("<Right>", self.next_image)
        self.master.bind("<Up>", self.rotate_left)
        self.master.bind("<Down>", self.rotate_right)
        self.master.bind("<space>", self.flip_image)
        self.master.bind("<Return>", self.goto_image_by_number)
        self.master.bind("a", lambda e: self.set_comment_and_next("present"))
        self.master.bind("z", lambda e: self.set_comment_and_next("absent"))
        #self.master.bind("e", lambda e: self.set_comment_and_next("meca"))


    def goto_image_by_number(self, event=None):
        try:
            number = int(self.counter_var.get())
            if self.filter_value and self.filtered_indices:
                if 1 <= number <= len(self.filtered_indices):
                    self.current_index = number - 1
                else:
                    return
            else:
                if 1 <= number <= len(self.image_files):
                    self.current_index = number - 1
                else:
                    return
            self.rotation_angle = 0
            self.flipped = False
            self.display_image()
        except ValueError:
            pass
        finally:
            self.master.focus_set()

    def flip_image(self, event=None):
        self.flipped = not self.flipped
        self.display_image()

    def set_comment_and_next(self, comment):
        if "commentaire" in self.entry_vars:
            self.entry_vars["commentaire"].set(comment)
            self.next_image()

    def apply_filter(self, value):
        if value == "Tous":
            self.filter_value = None
        else:
            self.filter_value = value
        if self.filter_value:
            self.filtered_indices = [
                i for i, f in enumerate(self.image_files)
                if not self.df[self.df["filename"] == f.split("ù")[-1]].empty and
                   self.df[self.df["filename"] == f.split("ù")[-1]].iloc[0].get("commentaire") == self.filter_value
            ]
        else:
            self.filtered_indices = list(range(len(self.image_files)))
        self.current_index = 0
        self.display_image()

    def update_stats(self):
        total = len(self.image_files)
        completed = self.df["commentaire"].notna().sum()
        percent = (completed / total) * 100 if total else 0
        ras_count = (self.df["commentaire"] == "present").sum()

        avg_time = sum(self.time_spent) / len(self.time_spent) if self.time_spent else 0

        stats_text = (
            f"Images classées : {completed}/{total} ({percent:.1f}%)\n"
            f"present : {ras_count}\n"
            f"Temps moyen/image : {avg_time:.1f} sec"
        )
        self.stats_label.config(text=stats_text)
        commentaire_counts = self.df["commentaire"].value_counts(dropna=True).to_dict()
        options = [("Tous", None)] + [(f"{key} ({value})", key) for key, value in commentaire_counts.items()]

        menu = self.filter_menu["menu"]
        menu.delete(0, "end") 

        for label, value in options:
            menu.add_command(label=label, command=lambda v=value: self.apply_filter(v))

        
        current = self.filter_var.get()
        if current not in [label for label, _ in options]:
            self.filter_var.set("Tous")

    def on_mousewheel(self, event):
        # Position curseur
        mouse_x = self.canvas.canvasx(event.x)
        mouse_y = self.canvas.canvasy(event.y)

        if self.canvas.bbox("all"):
            bbox = self.canvas.bbox("all")
            rel_x = (mouse_x - bbox[0]) / (bbox[2] - bbox[0])
            rel_y = (mouse_y - bbox[1]) / (bbox[3] - bbox[1])
        else:
            rel_x, rel_y = 0.5, 0.5

        # Appliquer zoom
        if event.delta > 0:
            scale = 1.3
        else:
            scale = 0.9

        old_zoom = self.zoom_factor
        self.zoom_factor *= scale
        self.zoom_factor = max(0.2, min(self.zoom_factor, 5))

        # Calculer offset pour conserver point sous curseur
        zoom_diff = self.zoom_factor / old_zoom
        self.image_offset_x = (self.image_offset_x + mouse_x) * zoom_diff - mouse_x
        self.image_offset_y = (self.image_offset_y + mouse_y) * zoom_diff - mouse_y

        self.display_image()

    def start_pan(self, event):
        self.pan_start_x = event.x
        self.pan_start_y = event.y

    def do_pan(self, event):
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y

        self.image_offset_x -= dx
        self.image_offset_y -= dy

        self.pan_start_x = event.x
        self.pan_start_y = event.y

        self.display_image()

    def load_data(self, root_folder, image_folder, excel_file):
        self.image_folder = image_folder
        self.image_files = [f for f in os.listdir(image_folder) if f.lower().endswith(('png', 'jpg', 'jpeg', 'tif', '.tiff'))]
        self.excel_file = excel_file
        self.df = pd.read_excel(excel_file, dtype=str)
        self.df.columns = [c.strip().lower() for c in self.df.columns]
        if 'filename' not in self.df.columns:
            raise ValueError("Le fichier Excel ne contient pas de colonne 'filename'.")
        if 'commentaire' not in self.df.columns:
            self.df['commentaire'] = ""

        self.df['filename'] = (
            self.df['filename']
            .astype(str)
            .apply(lambda s: os.path.basename(s).strip())
        )
        print(f"Images trouvées dans {image_folder} : {self.image_files}")
        self.display_image()

    def display_info(self, row):
        for entry in self.entries:
            entry.destroy()
        self.entries.clear()
        self.entry_vars.clear()

        for i, (col, val) in enumerate(row.items()):
            if col in ["filename", "commentaire"]:
                Label(self.data_frame, text=col + ":", anchor="w").grid(row=i, column=0, sticky="w")
                var = StringVar(value=val)

                if col == "commentaire":
                    options = ["present", "absent"]
                    current = val if val in options and isinstance(val, str) else options[0]
                    var.set(current)
                    widget = ttk.OptionMenu(self.data_frame, var, current, *options)
                else:
                    widget = Entry(self.data_frame, textvariable=var, width=25)


                widget.grid(row=i, column=1, sticky="w", pady=2)
                self.entries.append(widget)
                self.entry_vars[col] = var

    def display_image(self):
        if not self.image_files:
            return

        # Choisir image à afficher
        if self.filter_value and self.filtered_indices:
            index = self.filtered_indices[self.current_index % len(self.filtered_indices)]
        else:
            index = self.current_index % len(self.image_files)

        image_name = self.image_files[index]
        image_path = os.path.join(self.image_folder, image_name)
        image = Image.open(image_path).rotate(self.rotation_angle, expand=True)

        if self.flipped:
            image = image.transpose(Image.FLIP_LEFT_RIGHT)

        base_width, base_height = 900, 650
        new_width = int(base_width * self.zoom_factor)
        new_height = int(base_height * self.zoom_factor)
        image = image.resize((new_width, new_height), Image.LANCZOS)

        self.canvas_image = ImageTk.PhotoImage(image)
        self.canvas.delete("all")

        # Affiche l’image aux coordonnées selon offset
        self.canvas.create_image(-self.image_offset_x, -self.image_offset_y, anchor="nw", image=self.canvas_image)

        # scrollregion étendue très large pour éviter les limites de déplacement
        margin = 2000
        self.canvas.config(scrollregion=(-margin, -margin, new_width + margin, new_height + margin))

        # compteur pour savoir à quelle image on est
        total = len(self.filtered_indices) if self.filter_value and self.filtered_indices else len(self.image_files)
        self.counter_var.set(str(self.current_index + 1))
        self.total_label_var.set(f"/{total}")

        # données associées
        img_key = os.path.basename(image_name).strip().casefold()
        df_key = self.df['filename'].astype(str).str.strip().str.casefold()

        match = self.df.loc[df_key == img_key]

        if not match.empty:
            self.display_info(match.iloc[0])
        else:
            # Si l'image n'est pas dans l'Excel, on l'ajoute à la volée
            new_row = {'filename': os.path.basename(image_name), 'commentaire': ""}
            self.df = pd.concat([self.df, pd.DataFrame([new_row])], ignore_index=True)
            self.display_info(self.df.iloc[-1])
            # (optionnel) Sauvegarder tout de suite
            self.df.to_excel(self.excel_file, index=False)

        self.update_stats()

    def save_changes(self):
        image_name = self.image_files[self.current_index].split("ù")[-1]
        for col, var in self.entry_vars.items():
            self.df.loc[self.df['filename'] == image_name, col] = var.get()
        self.df.to_excel(self.excel_file, index=False)

    def next_image(self, event=None):
        self.save_changes()
        now = time.time()
        if hasattr(self, "last_image_time"):
            self.time_spent.append(now - self.last_image_time)
        self.last_image_time = now

        if self.filter_value and self.filtered_indices:
            self.current_index = (self.current_index + 1) % len(self.filtered_indices)
        else:
            self.current_index = (self.current_index + 1) % len(self.image_files)

        self.rotation_angle = 0
        self.display_image()

    def prev_image(self, event=None):
        self.save_changes()
        now = time.time()
        if hasattr(self, "last_image_time"):
            self.time_spent.append(now - self.last_image_time)
        self.last_image_time = now

        if self.filter_value and self.filtered_indices:
            self.current_index = (self.current_index - 1) % len(self.filtered_indices)
        else:
            self.current_index = (self.current_index - 1) % len(self.image_files)

        self.rotation_angle = 0
        self.display_image()

    def rotate_left(self, event=None):
        self.rotation_angle = (self.rotation_angle - 90) % 360
        self.display_image()

    def rotate_right(self, event=None):
        self.rotation_angle = (self.rotation_angle + 90) % 360
        self.display_image()

def create_excel(image_folder):
    image_dict={"filename":[],
                "commentaire":[]}
    for root, dirs, files in os.walk(image_folder, topdown=False):
        for name in files:
            image_dict["filename"].append(name)
            image_dict["commentaire"].append("")
    excel_file=pd.DataFrame(image_dict)
    excel_path = os.path.join(os.path.dirname(image_folder),f"Resultat-{image_folder.split('/')[-1]}.xlsx")
    excel_file.to_excel(excel_path,index=False)

    return excel_path

if __name__ == "__main__":
    root = Tk()
    app = ImageApp(root)
    image_folder = filedialog.askdirectory(title="Select Image Folder")
    print(image_folder)
    if f"Resultat-{image_folder.split('/')[-1]}.xlsx" not in os.listdir(os.path.dirname(image_folder)):
        excel_file=create_excel(image_folder)
    else:
        excel_file=os.path.join(os.path.dirname(image_folder),f"Resultat-{image_folder.split('/')[-1]}.xlsx")

    app.load_data(image_folder,image_folder, excel_file)
    root.mainloop()