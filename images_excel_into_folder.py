import pandas as pd
import shutil
import os

excel_file = r"C:\Users\XMHC309\Desktop\Analyse_diverse\Dates\yo.xlsx"       # fichier Excel
colonne = "filename" # nom de la colonne avec les noms d'image
source_folder = r"C:\Users\XMHC309\Desktop\Analyse_diverse\Dates\images"              # dossier où sont stockées toutes les images
destination_folder = r"C:\Users\XMHC309\Desktop\Analyse_diverse\Dates\images_avec_dates"       # dossier je veux copier les images

# Créer le dossier de destination s’il n’existe pas
os.makedirs(destination_folder, exist_ok=True)

# Lire les noms d’images depuis l’Excel
df = pd.read_excel(excel_file)
image_names = df[colonne].dropna().astype(str).tolist()

# Copier les fichiers correspondants
for image_name in image_names:
    source_path = os.path.join(source_folder, image_name)
    dest_path = os.path.join(destination_folder, image_name)

    if os.path.isfile(source_path):
        shutil.copy2(source_path, dest_path)
    else:
        print(f"Fichier introuvable : {image_name}")

print("Copie terminée.")