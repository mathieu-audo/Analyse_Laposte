import os
import pandas as pd
import requests
import time
from tkinter import Tk, Label, Entry, Button, Canvas, Text, filedialog, StringVar
from tkinter import ttk
from PIL import Image, ImageTk

class ImageApp:
    def __init__(self, master):
        self.master = master
        self.master.title("IHM Classification Noglue LaPoste")
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

        self.csv_path = "D:/Dev/Utils/excel_to_kibana/data/"
        self.date = None
        self.filter_value= None
        self.filtered_indices = []
        self.start_time = time.time()
        self.time_spent = []
        self.last_time = time.time()
        self.rect_start = None
        self.rect_id = None

        self.create_widgets()
        self.bind_keys()

    def create_widgets(self):
        # Zone image (gauche)
        self.image_frame = ttk.LabelFrame(self.master, text="Image à classer", padding=10)
        self.image_frame.grid(row=0, column=0, rowspan=4, padx=10, pady=10, sticky="nsew")

        self.canvas = Canvas(self.image_frame, width=900, height=600, bg="gray")
        self.canvas.pack()

        self.coord_label = Label(self.master, text="", bg="white", fg="black", font=("Arial", 9))
        self.coord_label.place(x=10, y=5)
        self.canvas.bind("<Motion>", self.update_cursor_coordinates)

        # Instructions clavier
        self.info_frame = ttk.LabelFrame(self.master, text="Commandes clavier", padding=10)
        self.info_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")

        instructions = (
            "← Image précédente\n"
            "→ Image suivante\n"
            "↑ Rotation gauche\n"
            "↓ Rotation droite\n"
            "ESPACE : Inverser l'image horizontalement\n"
            "Entrée : Vérifier le code"
        )
        Label(self.info_frame, text=instructions, justify="left").pack(anchor="w")

        # Vérification code
        self.curl_frame = ttk.LabelFrame(self.master, text="Vérification du code", padding=10)
        self.curl_frame.grid(row=1, column=1, padx=10, pady=5, sticky="nsew")

        Label(self.curl_frame, text="Code :").grid(row=0, column=0, sticky="w")
        self.curl_code_var = StringVar()
        Entry(self.curl_frame, textvariable=self.curl_code_var, width=30).grid(row=0, column=1, padx=5, pady=5)
        self.response_text = Text(self.curl_frame, height=2, width=40)
        self.response_text.grid(row=1, column=0, columnspan=2, pady=5)

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

        # Compteur
        self.counter_label = Label(self.master, text="", font=("Arial", 10), bg="white")
        self.counter_label.grid(row=3, column=1, pady=10)

        #bind pour le zoom
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<ButtonPress-1>",self.start_pan)
        self.canvas.bind("<B1-Motion>",self.do_pan)

        #bind pour selection rectangle
        self.canvas.bind("<ButtonPress-3>", self.start_rectangle)  # clic droit
        self.canvas.bind("<B3-Motion>", self.draw_rectangle)
        self.canvas.bind("<ButtonRelease-3>", self.finish_rectangle)

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
        self.master.bind("<Return>", self.run_curl)
        self.master.bind("<space>", self.flip_image)

    def flip_image(self, event=None):
        self.flipped = not self.flipped
        self.display_image()

    def apply_filter(self, value):
        self.filter_value = value  # None ou un nom de commentaire

        if self.filter_value:
            # Filtrer la DataFrame une fois proprement
            df_filtered = self.df[self.df["complement"] == self.filter_value]

            # Mettre à jour la liste des fichiers image
            self.image_files = [
                f"{self.image_folder}/imageù{filename}"
                for filename in df_filtered["filename"]
            ]
        else:
            # Aucun filtre : toutes les images
            self.image_files = [
                f"{self.image_folder}/imageù{filename}"
                for filename in self.df["filename"]
            ]

        self.current_index = 0
        self.display_image()

    def update_stats(self):
        total = len(self.image_files)
        completed = self.df["complement"].notna().sum()
        percent = (completed / total) * 100 if total else 0

        v_count = (self.df["Vrai_Faux"] == "V").sum()
        f_count = (self.df["Vrai_Faux"] == "F").sum()
        ras_count = (self.df["complement"] == "RAS").sum()

        avg_time = sum(self.time_spent) / len(self.time_spent) if self.time_spent else 0

        stats_text = (
            f"Images classées : {completed}/{total} ({percent:.1f}%)\n"
            f"V : {v_count} | F : {f_count} | RAS : {ras_count}\n"
            f"Temps moyen/image : {avg_time:.1f} sec"
        )
        self.stats_label.config(text=stats_text)
        commentaire_counts = self.df["complement"].value_counts(dropna=True).to_dict()
        options = [("Tous", None)] + [(f"{key} ({value})", key) for key, value in commentaire_counts.items()]

        menu = self.filter_menu["menu"]
        menu.delete(0, "end")  # Réinitialise le menu

        for label, value in options:
            menu.add_command(label=label, command=lambda v=value: (self.filter_var.set(v or "Tous"),self.apply_filter(v)))

        if self.filter_value not in [v for _,v in options]:
            self.filter_var.set("Tous")


        # Si la sélection actuelle n'est plus valide (ex. après changement)
        current = self.filter_var.get()
        if current not in [label for label, _ in options]:
            self.filter_var.set("Tous")

    def start_rectangle(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        # Coordonnées dans l'image zoomée (affichée)
        image_x = canvas_x + self.image_offset_x
        image_y = canvas_y + self.image_offset_y

        self.rect_start = (image_x, image_y)

    def draw_rectangle(self, event):
        if not self.rect_start:
            return

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        image_x = canvas_x + self.image_offset_x
        image_y = canvas_y + self.image_offset_y

        x0, y0 = self.rect_start
        x1, y1 = image_x, image_y

        if self.rect_id:
            self.canvas.coords(self.rect_id, x0 - self.image_offset_x, y0 - self.image_offset_y,
                               x1 - self.image_offset_x, y1 - self.image_offset_y)
        else:
            self.rect_id = self.canvas.create_rectangle(x0 - self.image_offset_x, y0 - self.image_offset_y,
                                                        x1 - self.image_offset_x, y1 - self.image_offset_y,
                                                        outline="red", width=2)

    def finish_rectangle(self, event):
        if not self.rect_start:
            return

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        image_x = canvas_x + self.image_offset_x
        image_y = canvas_y + self.image_offset_y

        x0, y0 = self.rect_start
        x1, y1 = image_x, image_y

        x0_disp, x1_disp = sorted([x0, x1])
        y0_disp, y1_disp = sorted([y0, y1])

        # Dimensions de l’image originale
        image_path = os.path.join(self.image_folder, self.image_files[self.current_index])
        image = Image.open(image_path)
        orig_height, orig_width  = image.size

        # Dimensions de l’image affichée
        disp_width = self.canvas_image.width()
        disp_height = self.canvas_image.height()

        # Conversion vers coordonnées originales
        x0_real = int(x0_disp * orig_width / disp_width)
        x1_real = int(x1_disp * orig_width / disp_width)
        y0_real = int(y0_disp * orig_height / disp_height)
        y1_real = int(y1_disp * orig_height / disp_height)

        # Inversion Y pour origine en bas à gauche
        y0_real = orig_height - y0_real
        y1_real = orig_height - y1_real

        lb_coordinates = f"{x0_real} {y0_real};{x1_real} {y1_real}"
        print(f"[OCR] Coordinates: {lb_coordinates}")

        self.send_to_ocr(lb_coordinates)
        self.rect_start = None

    def send_to_ocr(self, lb_coordinates):
        image_index = self.current_index % len(self.image_files)
        image_name = self.image_files[image_index]
        image_path = os.path.join(self.image_folder, image_name)

        url = f"https://courrier.cio.net.intra.laposte.fr/ocr/afx"
        payload = {
        "lbCoordinates": lb_coordinates,
        "rotAngle": self.rotation_angle}
        headers = {}
        try:
            files = [
                ('file', (image_name,
                          open(image_path, 'rb'), 'image/tiff'))
            ]
            response = requests.request("POST", url, headers=headers, data=payload, files=files, verify=False)
            response.raise_for_status()
            try:
                result = response.json()
                if isinstance(result, dict) and "text" in result:
                    code_text = result["text"].strip().replace(" ","")
                    self.curl_code_var.set(code_text)
                    self.response_text.delete(1.0, "end")
                    self.run_curl(code_text)
                else:
                    raise ValueError("Réponse OCR inattendue.")
            except Exception as e_json:
                self.response_text.delete(1.0, "end")
                self.response_text.insert("end", f"Erreur OCR (décodage JSON) : {e_json}")
        except Exception as e_request:
            self.response_text.delete(1.0, "end")
            self.response_text.insert("end", f"Erreur OCR (lecture fichier) : {e_request}")

    def update_cursor_coordinates(self, event):
        # coordonnées dans le canvas (après pan/scroll)
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        # coordonnées dans l’image affichée, avant redimensionnement
        img_disp_x = canvas_x + self.image_offset_x
        img_disp_y = canvas_y + self.image_offset_y

        # ratio de redimensionnement
        disp_w = self.canvas_image.width()
        disp_h = self.canvas_image.height()
        orig_w, orig_h = Image.open(
            os.path.join(self.image_folder, self.image_files[self.current_index])
        ).size
        scale_x = orig_w / disp_w
        scale_y = orig_h / disp_h

        # coordonnées dans l’image originale
        x_real = int(img_disp_x * scale_x)
        y_real = int(img_disp_y * scale_y)

        # inversion Y pour origine en bas à gauche
        y_real = orig_h - y_real

        self.coord_label.config(text=f"Coordonnées image : x={y_real}, y={x_real}")
    def on_mousewheel(self, event):
       #Position curseur
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
        self.image_files = [f for f in os.listdir(image_folder) if f.lower().endswith(('png', 'jpg', 'jpeg', 'tif'))]
        self.excel_file = excel_file
        self.df = pd.read_excel(excel_file, dtype=str)
        self.date = root_folder.split("/")[-1].replace("-", "") + ".csv"
        self.csv_path = os.path.join(self.csv_path, self.date)
        self.display_image()

    def display_image(self):
        if not self.image_files:
            return

        if self.filter_value and self.filtered_indices:
            index = self.filtered_indices[self.current_index % len(self.filtered_indices)]
        else:
            index = self.current_index % len(self.image_files)

        image_name = self.image_files[index]
        image_path = os.path.join(self.image_folder, image_name)
        image = Image.open(image_path).rotate(self.rotation_angle, expand=True)
        if self.flipped:
            image = image.transpose(Image.FLIP_LEFT_RIGHT)
        # redimensioner avec le zoom
        base_width, base_height = 900, 650
        new_width = int(base_width * self.zoom_factor)
        new_height = int(base_height * self.zoom_factor)
        image = image.resize((new_width,new_height),Image.LANCZOS)

        self.canvas_image = ImageTk.PhotoImage(image)
        self.canvas.delete("all")

        # Affiche l’image aux coordonnées selon offset
        self.canvas.create_image(-self.image_offset_x, -self.image_offset_y, anchor="nw", image=self.canvas_image)

        # scrollregion étendue très large pour éviter les limites de déplacement
        margin = 2000
        self.canvas.config(scrollregion=(-margin, -margin, new_width + margin, new_height + margin))

        self.counter_label.config(text=f"{self.current_index + 1}/{len(self.image_files)}")

        row = self.df.loc[self.df['filename'] == image_name.split("ù")[-1]]
        if not row.empty:
            self.display_info(row.iloc[0])
        self.update_stats()

    def display_info(self, row):
        for entry in self.entries:
            entry.destroy()
        self.entries.clear()
        self.entry_vars.clear()

        for i, (col, val) in enumerate(row.items()):
            if col in ["filename", "Mode", "Vrai_Faux", "Positif_Negatif", "complement"]:
                Label(self.data_frame, text=col + ":", anchor="w").grid(row=i, column=0, sticky="w")
                var = StringVar(value=val)

                if col == "Vrai_Faux":
                    widget = ttk.OptionMenu(self.data_frame, var, var.get(), "V", "F")
                elif col == "complement":
                    options = ["RAS", "FraudeTN", "FraudeMA", "Meca", "CGU", "FraudeInter",
                               "FraudeZOO", "Carre", "Doublon", "Dactylo", "LR", "FraudeDivers"]
                    widget = ttk.OptionMenu(self.data_frame, var, var.get(), *options)
                else:
                    widget = Entry(self.data_frame, textvariable=var, width=25)

                widget.grid(row=i, column=1, sticky="w", pady=2)
                self.entries.append(widget)
                self.entry_vars[col] = var

    def save_changes(self):
        image_name = self.image_files[self.current_index].split("ù")[-1]
        complement = self.entry_vars.get("complement", StringVar()).get()

        # Règle auto : certains compléments imposent Vrai_Faux à "V"
        auto_true_complements = ["Meca", "FraudeTN", "FraudeInter", "FraudeZOO", "FraudeDivers", "LR", "FraudeMA"]
        if complement in auto_true_complements:
            self.entry_vars["Vrai_Faux"].set("V")

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
        else :
            self.current_index = (self.current_index + 1) % len(self.image_files)

        self.rotation_angle = 0
        self.display_image()
        self.response_text.delete(1.0, "end")
        self.curl_code_var.set("")

    def prev_image(self, event=None):
        self.save_changes()
        now = time.time()
        if hasattr(self, "last_image_time"):
            self.time_spent.append(now - self.last_image_time)
        self.last_image_time = now

        if self.filter_value and self.filtered_indices:
            self.current_index = (self.current_index - 1) % len(self.filtered_indices)
        else :
            self.current_index = (self.current_index - 1) % len(self.image_files)

        self.rotation_angle = 0
        self.display_image()

    def rotate_left(self, event=None):
        self.rotation_angle = (self.rotation_angle - 90) % 360
        self.display_image()

    def rotate_right(self, event=None):
        self.rotation_angle = (self.rotation_angle + 90) % 360
        self.display_image()

    def run_curl(self, event=None):
        code = self.curl_code_var.get().strip().upper()
        self.response_text.delete(1.0, "end")
        if not code:
            self.response_text.insert("end", "Veuillez entrer un code !")
            return

        url = f"https://courrier.cio.net.intra.laposte.fr/noglue/{code}"
        try:
            response = requests.get(url, verify=False)
            data = response.json()
            if data.get("smartData"):
                self.response_text.insert("end", "CODE OK", "green_bold")
            else:
                self.response_text.insert("end", "CODE ERRONE", "red_bold")
        except Exception as e:
            self.response_text.insert("end", f"Erreur : {e}")

        self.response_text.tag_configure("green_bold", foreground="green", font=("Arial", 12, "bold"))
        self.response_text.tag_configure("red_bold", foreground="red", font=("Arial", 12, "bold"))


if __name__ == "__main__":
    root = Tk()
    app = ImageApp(root)
    image_folder = filedialog.askdirectory(title="Sélectionnez le dossier d'images")

    if "automatic_filtering.xlsx" not in os.listdir(image_folder):
        parse_folder(image_folder)

    image_folder_fn = os.path.join(image_folder, "Automatic_filtering", "modeForce", "FN")
    print(image_folder_fn)
    excel_file = os.path.join(image_folder, "automatic_filtering.xlsx")

    if os.path.exists(image_folder_fn) and os.path.exists(excel_file):
        app.load_data(image_folder, image_folder_fn, excel_file)
        root.mainloop()
