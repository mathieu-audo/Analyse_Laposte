import os
import shutil


folder_path = "C:/Users/XMHC309/Desktop/noglue_analyser/2025-06-15"
folders_to_remove = ["timbre_numerique_absent", "timbre_numerique_avec_carre", "timbre_numerique_sans_carre"]

for root, dirs, files in os.walk(folder_path):
    for folder in folders_to_remove:
        if folder in root:
            shutil.rmtree(root)