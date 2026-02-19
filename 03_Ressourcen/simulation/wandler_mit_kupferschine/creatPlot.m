% 1. Fläche definieren
A_mm2 = 10 * 30;       % Fläche in mm^2 (300 mm^2)
A_m2 = A_mm2 * 1e-6;   % Umrechnung in m^2 für die Formel (Phi = B * A)

% 2. Dateien einlesen
% MATLABs 'load' Befehl ignoriert Zeilen mit %, das passt also für deine Dateien
data_sym = load('data/wandler.sym.0.txt');
data_unsym = load('data/wandler.unsym.0.txt');

% 3. Spalten zuweisen (Spalte 1: Länge, Spalte 2: B-Feld)
len_sym = data_sym(:, 1);
B_sym = data_sym(:, 2);
len_unsym = data_unsym(:, 1);
B_unsym = data_unsym(:, 2);

% 4. Magnetischen Fluss berechnen (Phi = B * A)
Phi_sym = B_sym * A_m2;
Phi_unsym = B_unsym * A_m2;

% --- Daten glätten ---
% Fenstergröße für die Glättung festlegen (anpassbar)
window_size = 50; 
Phi_sym_smooth = smoothdata(Phi_sym, 'gaussian', window_size);
Phi_unsym_smooth = smoothdata(Phi_unsym, 'gaussian', window_size);

% Maximale Länge zur Sicherheit aus beiden Datensätzen ermitteln
max_len = max([max(len_sym), max(len_unsym)]);

% 5. Plotten
% Fenster explizit mit weißem Hintergrund erstellen (heller Modus)
figure('Color', 'w');

% Plotten der geglätteten Daten (Phi_sym_smooth und Phi_unsym_smooth)
plot(len_sym, Phi_sym_smooth * 1e6, 'b', 'LineWidth', 1.5, 'DisplayName', 'Zentrisch'); 
hold on;
plot(len_unsym, Phi_unsym_smooth * 1e6, 'Color', '#00CC00', 'LineWidth', 1.5, 'DisplayName', 'Exzentrisch');

% Vertikale Linien viertelweise von der maximalen Länge einzeichnen
xline(max_len * 0.25, '--r', '1/4', 'HandleVisibility', 'off');
xline(max_len * 0.50, '--r', '1/2', 'HandleVisibility', 'off');
xline(max_len * 0.75, '--r', '3/4', 'HandleVisibility', 'off');
xline(max_len, '--r', 'Max', 'HandleVisibility', 'off');

% Beschriftung
xlabel('Länge [mm]');
ylabel('Magnetischer Fluss \Phi [\muWb]'); % Anzeige in Mikro-Weber

% Titel explizit auf Schwarz setzen
title('Verlauf des magnetischen Flusses', 'Color', 'k');

% Legende anzeigen, nach unten rechts verschieben und auf helles Design zwingen
lgd = legend('show', 'Location', 'southeast');
set(lgd, 'Color', 'w', 'TextColor', 'k', 'EdgeColor', 'k');

grid on;

% Achsenhintergrund, Linien- und Textfarbe auf helles Design (schwarz auf weiß) festlegen
set(gca, 'Color', 'w', 'XColor', 'k', 'YColor', 'k', 'GridColor', 'k');

hold off;