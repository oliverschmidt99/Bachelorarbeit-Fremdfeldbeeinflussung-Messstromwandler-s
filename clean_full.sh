#!/bin/bash

# Definition der Dateiendungen, die weg sollen
EXTENSIONS=(
    "aux" "log" "out" "toc" "lof" "lot"       # Standard
    "synctex.gz" "fdb_latexmk" "fls"          # Build-Tools
    "bbl" "blg" "bbl-SAVE-ERROR"              # Literaturverzeichnis & Fehler
    "acn" "acr" "alg" "glg" "glo" "gls" "ist" # Glossaries & Acronyms
    "nav" "snm" "vrb"                         # Beamer
    "xdv" "indent.log" "lod"  "bcf"                 # Sonstiges
)

echo "Starte rekursive Bereinigung in allen Ordnern..."

# Loop durch alle Endungen
for ext in "${EXTENSIONS[@]}"; do
    # find sucht im aktuellen Verzeichnis (.) und allen Unterordnern
    # -type f beschränkt die Suche auf Dateien
    # -name "*.$ext" sucht nach der spezifischen Endung
    # -delete löscht die gefundene Datei sofort
    find . -type f -name "*.$ext" -delete
done

# Speziell für Dateien, die mit .bbl-SAVE-ERROR enden
find . -type f -name "*.bbl-SAVE-ERROR" -delete

echo "Fertig! Es verbleiben nur .tex, .pdf, .bib und Ressourcen."