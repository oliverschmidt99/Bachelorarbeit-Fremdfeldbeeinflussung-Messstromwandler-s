<#
.SYNOPSIS
Skript zur rekursiven Bereinigung von LaTeX-Hilfsdateien.
#>

# Definition der Dateiendungen, die weg sollen
$extensions = @(
    "aux", "log", "out", "toc", "lof", "lot",       # Standard
    "synctex.gz", "fdb_latexmk", "fls",             # Build-Tools
    "bbl", "blg", "bbl-SAVE-ERROR",                 # Literaturverzeichnis & Fehler
    "acn", "acr", "alg", "glg", "glo", "gls", "ist",# Glossaries & Acronyms
    "nav", "snm", "vrb",                            # Beamer
    "xdv", "indent.log", "lod", "bcf"                      # Sonstiges
)

Write-Host "Starte rekursive Bereinigung in allen Ordnern..."

# Loop durch alle Endungen
foreach ($ext in $extensions) {
    # Get-ChildItem sucht im aktuellen Verzeichnis und allen Unterordnern
    # Remove-Item löscht die gefundenen Dateien
    # ErrorAction SilentlyContinue unterdrückt Fehler, falls Dateien nicht existieren
    Get-ChildItem -Path . -Recurse -File -Filter "*.$ext" -ErrorAction SilentlyContinue | Remove-Item -Force
}

# Speziell für Dateien, die mit .bbl-SAVE-ERROR enden
Get-ChildItem -Path . -Recurse -File -Filter "*.bbl-SAVE-ERROR" -ErrorAction SilentlyContinue | Remove-Item -Force

Write-Host "Fertig! Es verbleiben nur .tex, .pdf, .bib und Ressourcen."