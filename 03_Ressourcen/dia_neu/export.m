function lade_und_plotte_alle()
    % --- MATLAB STYLE CONFIGURATION (LIGHT MODE FORCE) ---
    set(groot, 'defaultFigureColor', 'w');
    set(groot, 'defaultAxesColor', 'w');
    set(groot, 'defaultTextColor', 'k');
    set(groot, 'defaultAxesXColor', 'k', 'defaultAxesYColor', 'k');
    set(groot, 'defaultTextInterpreter', 'latex');
    set(groot, 'defaultAxesTickLabelInterpreter', 'latex');
    set(groot, 'defaultLegendInterpreter', 'latex');
    set(groot, 'defaultLineLineWidth', 1.2);
    set(groot, 'defaultAxesLineWidth', 1.2);
    set(groot, 'defaultAxesTickDir', 'in');
    set(groot, 'defaultAxesBox', 'on');
    set(groot, 'defaultAxesGridLineStyle', '--');
    set(groot, 'defaultAxesMinorGridLineStyle', ':');
    set(groot, 'defaultAxesGridAlpha', 0.7);
    set(groot, 'defaultAxesMinorGridAlpha', 0.4);

    % --- KONFIGURATION ---
    CSV_DATEI = 'export_sortiert.csv';
    X_WERTE_LINIE = [5, 20, 50, 80, 90, 100, 120];
    DIRS = struct(...
        'verlauf', 'verlauf', ...
        'wirtschaft', 'wirtschaftlichkeit', ...
        'kosten', 'kosten_horizontal', ...
        'verbesserung', 'verbesserung_pct', ...
        'absolut', 'absoluten_fehler', ...
        'bereich', 'bereichs_analyse');

    % --- ORDNER ERSTELLEN ---
    fields = fieldnames(DIRS);
    for i = 1:numel(fields)
        if ~exist(DIRS.(fields{i}), 'dir')
            mkdir(DIRS.(fields{i}));
        end
    end

    fprintf('Lade Datei %s ...\n', CSV_DATEI);
    if ~exist(CSV_DATEI, 'file')
        fprintf('Datei nicht gefunden.\n');
        return;
    end

    % CSV Einlesen
    opts = detectImportOptions(CSV_DATEI);
    opts.VariableNamingRule = 'preserve';
    try
        T = readtable(CSV_DATEI, opts);
    catch ME
        fprintf('Fehler beim Einlesen: %s\n', ME.message);
        return;
    end

    % Spaltennamen standardisieren (Kleinbuchstaben, Trimmen)
    varNames = T.Properties.VariableNames;
    varNames = lower(strtrim(varNames));
    for i = 1:length(varNames)
        varNames{i} = strrep(varNames{i}, '"', '');
    end
    T.Properties.VariableNames = varNames;
    
    % Textspalten definieren
    strCols = {'hersteller', 'modell', 'technologie', 'geometrie', 'nennstrom', 'export_group', 'final_legend'};
    for i = 1:length(strCols)
        col = strCols{i};
        if ismember(col, varNames)
            if isstring(T.(col)) || iscategorical(T.(col))
                T.(col) = cellstr(T.(col));
            elseif isnumeric(T.(col))
                T.(col) = cellstr(num2str(T.(col)));
            end
        end
    end
    
    % Numerische Spalten bereinigen
    for i = 1:length(varNames)
        col = varNames{i};
        if ~ismember(col, strCols)
            valData = T.(col);
            if iscell(valData) || isstring(valData)
                strArray = string(valData);
                strArray = strrep(strArray, '"', '');
                strArray = strrep(strArray, ',', '.');
                T.(col) = str2double(strArray);
            end
        end
    end
    
    if ismember('nennstrom', varNames)
        ns_str = T.nennstrom;
        T.nennstrom_num = str2double(regexprep(string(ns_str), '[^\d\.]', ''));
        T = sortrows(T, 'nennstrom_num');
    end

    if ~ismember('export_group', varNames)
        T.export_group = repmat({'default'}, height(T), 1);
    end
    
    % --- FARBEN ZUWEISEN ---
    [groups, ~, idx] = unique(T.export_group, 'stable');
    T.color = repmat({''}, height(T), 1);
    
    for i = 1:numel(groups)
        groupMask = (idx == i);
        T(groupMask, :) = assign_dynamic_colors_per_group(T(groupMask, :));
    end

    fprintf('\n--- Erstelle Diagramme ---\n');
    
    for i = 1:numel(groups)
        group = groups{i};
        if iscell(group), group = group{1}; end
        subT = T(strcmp(T.export_group, group), :);
        if isempty(subT), continue; end
        
        current_val = '?';
        if ismember('nennstrom', subT.Properties.VariableNames)
            current_val = subT.nennstrom{1};
        end
        
        % 1. Verlauf
        plot_line_curves_thesis_grouped(subT, group, current_val, X_WERTE_LINIE, DIRS);
        
        % 2. Bereichsanalyse
        if all(ismember({'nieder_ges', 'nenn_ges', 'ueber_ges'}, subT.Properties.VariableNames))
            plot_range_analysis(subT, sprintf('%s_bereichs_analyse.png', group), 'bereich', group, current_val, DIRS);
        end
        
        % 3. Absoluter Fehler
        if ismember('gesamtfehler', subT.Properties.VariableNames)
            plot_horizontal_generic(subT, 'gesamtfehler', 'Absoluter Fehler', group, current_val, ...
                'Fehler [\%]', sprintf('%s_abs_fehler.png', group), 'absolut', false, DIRS);
        end
        
        % 4. Kosten
        if ismember('preis (€)', subT.Properties.VariableNames)
            plot_horizontal_generic(subT, 'preis (€)', 'Kosten', group, current_val, ...
                'Kosten [EUR]', sprintf('%s_kosten.png', group), 'kosten', true, DIRS);
        end
    end
    
    % 5. Global: Verbesserung
    if ismember('verbesserung dreick', T.Properties.VariableNames)
        plot_unified_bars(T, 'verbesserung dreick', 'Verbesserung Dreieck', 'Verbesserung [\%]', ...
            'verbesserung_dreieck.png', 'verbesserung', DIRS);
    end
end

% ==========================================
% HELPER & FARBLOGIK
% ==========================================
function txt = escape_latex(txt)
    if iscell(txt)
        for i = 1:numel(txt)
            txt{i} = escape_latex_single(txt{i});
        end
    else
        txt = escape_latex_single(txt);
    end
end

function txt = escape_latex_single(txt)
    txt = strrep(char(txt), '&', '\&');
    txt = strrep(txt, '%', '\%');
    txt = strrep(txt, '$', '\$');
    txt = strrep(txt, '#', '\#');
    txt = strrep(txt, '_', '\_');
end

function t = build_title(base_title, group_name, current_val)
    clean_group = strrep(group_name, 'mes_', '');
    clean_group = strrep(clean_group, '_', ' ');
    suffix = regexprep(clean_group, '^\d+\s*A\s*', '');
    
    if ~isempty(suffix) && ~strcmp(suffix, clean_group)
        t = sprintf('%s | Nennstrom (%s A) - %s', base_title, current_val, suffix);
    else
        t = sprintf('%s | Nennstrom (%s A)', base_title, current_val);
    end
    t = escape_latex(t);
end

function g = normalize_geo(geo)
    g = lower(strtrim(char(geo)));
    if contains(g, 'dreieck'), g = 'Dreieck'; return; end
    if contains(g, 'parallel'), g = 'Parallel'; return; end
end

function label = format_label_text(row, include_current)
    h = strtrim(char(row.hersteller{1}));
    m = strtrim(char(row.modell{1}));
    t = strtrim(char(row.technologie{1}));
    geo = normalize_geo(row.geometrie{1});
    
    if isempty(t) || strcmpi(t, 'nan') || strcmpi(t, 'none'), t = '-'; end
    if isempty(m) || strcmpi(m, 'nan') || strcmpi(m, 'none'), m = ''; end
    label = sprintf('%s %s | %s | %s', h, m, t, geo);
    if include_current && ismember('nennstrom', row.Properties.VariableNames)
        ns = strtrim(char(row.nennstrom{1}));
        label = sprintf('%s | %s', label, ns);
    end
    label = regexprep(label, '\s+\|\s+\|\s+', ' | ');
    label = escape_latex(strtrim(label));
end

function rgb = hex2rgb(hexStr)
    if startsWith(hexStr, '#')
        hexStr = hexStr(2:end);
    end
    if isempty(hexStr)
        rgb = [0 0 0]; 
    else
        rgb = sscanf(hexStr, '%2x%2x%2x')' / 255;
    end
    if isempty(rgb)
        rgb = [0 0 0]; 
    end
end

function dark = is_dark_color(hex_color, threshold)
    if nargin < 2, threshold = 0.4; end
    rgb = hex2rgb(hex_color);
    dark = (0.299 * rgb(1) + 0.587 * rgb(2) + 0.114 * rgb(3)) < threshold;
end

function txt = format_value(val)
    if isnan(val), txt = ''; return; end
    if val == 0, txt = '0.00'; return; end
    if abs(val) < 0.01, txt = '$< 0.01$'; return; end
    txt = sprintf('%.2f', val);
end

function subT = assign_dynamic_colors_per_group(subT)
    COLOR_MBS_BASE = '#d62728';
    COLOR_CELSA_BASE = '#3187fc';
    COLOR_CELSA_KOMP = '#103dfc';
    COLOR_REDUR_BASE = '#1CAB10';
    COLOR_GRAY_BASE = '#6d0e78';
    COLOR_SIEMENS = '#00FFFF';
    COLOR_3K = '#800080';
    COLOR_ROGOWSKI = '#FFA500';
    
    SEQUENCE_COLORS = {'#d62728', '#0000FF', '#00AA00', '#FFA500', '#800080', '#00FFFF', '#A52A2A', '#FF00FF', '#808080'};
    
    flag = 0;
    if ismember('flags', subT.Properties.VariableNames)
        val = subT.flags(1);
        if ~isnan(val), flag = val; end
    end
    
    group_name = subT.export_group{1};
    if flag == 1
        modeStr = 'SEQUENZ (Rot/Blau...)';
    else
        modeStr = 'Standard';
    end
    fprintf('   -> Gruppe %s | Modus: %s\n', group_name, modeStr);
    
    colors_out = cell(height(subT), 1);
    
    if flag == 0
        for i = 1:height(subT)
            h = lower(char(subT.hersteller{i}));
            t = lower(char(subT.technologie{i}));
            
            if contains(h, 'mbs'), c = COLOR_MBS_BASE;
            elseif contains(h, 'celsa'), if contains(t, 'kompensiert'), c = COLOR_CELSA_KOMP; else, c = COLOR_CELSA_BASE; end
            elseif contains(h, 'redur') || contains(t, 'ffp'), c = COLOR_REDUR_BASE;
            elseif contains(h, 'siemens'), c = COLOR_SIEMENS;
            elseif contains(h, 'rogowski'), c = COLOR_ROGOWSKI;
            elseif contains(h, '3-k'), c = COLOR_3K;
            else, c = COLOR_GRAY_BASE;
            end
            colors_out{i} = c;
        end
    else
        type_keys = cell(height(subT), 1);
        for i = 1:height(subT)
            type_keys{i} = sprintf('%s_%s_%s', subT.hersteller{i}, subT.modell{i}, subT.technologie{i});
        end
        uKeys = unique(type_keys);
        
        seq_idx = 1;
        for k = 1:numel(uKeys)
            keyMask = strcmp(type_keys, uKeys{k});
            idxKey = find(keyMask);
            
            isTri = false(size(idxKey));
            isPar = false(size(idxKey));
            for m = 1:length(idxKey)
                isTri(m) = contains(lower(subT.geometrie{idxKey(m)}), 'dreieck');
                isPar(m) = contains(lower(subT.geometrie{idxKey(m)}), 'parallel');
            end
            
            parallels = idxKey(isPar);
            triangles = idxKey(isTri);
            others = idxKey(~isPar & ~isTri);
            
            n_inst = max([numel(parallels), numel(triangles), 1]);
            if numel(others) > 0, n_inst = max(n_inst, numel(others)); end
            
            for i = 1:n_inst
                c = SEQUENCE_COLORS{mod(seq_idx - 1, numel(SEQUENCE_COLORS)) + 1};
                seq_idx = seq_idx + 1;
                
                if i <= numel(parallels), colors_out{parallels(i)} = c; end
                if i <= numel(triangles), colors_out{triangles(i)} = c; end
                if i <= numel(others), colors_out{others(i)} = c; end
            end
        end
    end
    subT.color = colors_out;
end

function draw_limit_lines(ax, acc_class)
    x_lims = [5, 20, 100, 120];
    if strcmp(acc_class, '0.2')
        y_vals = [0.75, 0.35, 0.20, 0.20];
        lbl = 'Grenzwert Kl. 0.2';
    else
        y_vals = [3.0, 1.5, 1.0, 1.0];
        lbl = 'Grenzwert Kl. 1.0';
    end
    plot(ax, x_lims, y_vals, 'k--', 'LineWidth', 2.5, 'DisplayName', lbl);
    plot(ax, x_lims, -y_vals, 'k--', 'LineWidth', 2.5, 'HandleVisibility', 'off');
end

% ==========================================
% PLOT FUNKTIONEN
% ==========================================
function plot_line_curves_thesis_grouped(subT, group_name, current_val, X_WERTE_LINIE, DIRS)
    is_messstrecke = contains(lower(group_name), 'messstrecke');
    acc_class = '0.2';
    if ~is_messstrecke, acc_class = '1.0'; end
    fprintf(' -> Verlauf fuer %s (%s A)\n', group_name, current_val);
    
    fig = figure('Position', [100, 100, 1600, 750], 'Color', 'w', 'Visible', 'off');
    plt_title = build_title('Genauigkeitsverlauf', group_name, current_val);
    sgtitle(sprintf('\\textbf{%s}', plt_title), 'FontSize', 24, 'Color', 'k');
    
    phases = {'L1', 'L2', 'L3'};
    sp_axes = gobjects(1,3);
    
    leg_labels = {};
    leg_colors = {};
    leg_ls = {};
    leg_mk = {};
    
    for i = 1:3
        phase = phases{i};
        ax = subplot(1, 3, i);
        sp_axes(i) = ax;
        hold(ax, 'on');
        
        ax.XGrid = 'on';
        ax.YGrid = 'on';
        ax.XMinorGrid = 'on';
        ax.YMinorGrid = 'on';
        
        pos = ax.Position;
        pos(2) = 0.22;  
        pos(4) = 0.65;
        ax.Position = pos;
        
        yline(ax, 0, 'k-', 'LineWidth', 1.2, 'HandleVisibility', 'off');
        draw_limit_lines(ax, acc_class);
        
        title(ax, sprintf('\\textbf{Phase %s}', phase), 'FontSize', 16, 'Color', 'k');
        xlabel(ax, 'Strom $I / I_N$ [\%]', 'FontSize', 14, 'Color', 'k');
        if i == 1
            ylabel(ax, 'Abweichung [\%]', 'FontSize', 14, 'Color', 'k');
        end
        xlim(ax, [0, 125]);
        
        varNames = subT.Properties.VariableNames;
        
        for j = 1:height(subT)
            row = subT(j, :);
            y_vals = NaN(1, length(X_WERTE_LINIE));
            
            for k = 1:length(X_WERTE_LINIE)
                searchStr = sprintf('%d%% in_%s', X_WERTE_LINIE(k), lower(phase));
                idx = find(contains(varNames, searchStr));
                if ~isempty(idx)
                    val = row{1, idx(1)};
                    if iscell(val), val = val{1}; end
                    if ischar(val) || isstring(val)
                        val = str2double(strrep(strrep(string(val), '"', ''), ',', '.'));
                    end
                    y_vals(k) = double(val);
                end
            end
            
            mask = ~isnan(y_vals);
            if ~any(mask), continue; end
            
            colHex = row.color{1};
            colRgb = hex2rgb(colHex);
            geo = lower(char(row.geometrie{1}));
            
            if contains(geo, 'dreieck')
                ls = '--'; mk = '^';
            else
                ls = '-'; mk = 'o';
            end
            
            plot(ax, X_WERTE_LINIE(mask), y_vals(mask), 'Color', colRgb, 'LineStyle', ls, ...
                'Marker', mk, 'MarkerFaceColor', colRgb, 'MarkerSize', 8, 'LineWidth', 2);
            
            lbl = format_label_text(row, false);
            if ~ismember(lbl, leg_labels)
                leg_labels{end+1} = lbl; %#ok<AGROW>
                leg_colors{end+1} = colRgb; %#ok<AGROW>
                leg_ls{end+1} = ls; %#ok<AGROW>
                leg_mk{end+1} = mk; %#ok<AGROW>
            end
        end
        hold(ax, 'off');
    end
    linkaxes(sp_axes, 'y');
    
    if ~isempty(leg_labels)
        hold(sp_axes(2), 'on');
        leg_handles = gobjects(1, length(leg_labels));
        for k = 1:length(leg_labels)
            leg_handles(k) = plot(sp_axes(2), NaN, NaN, 'Color', leg_colors{k}, ...
                'LineStyle', leg_ls{k}, 'Marker', leg_mk{k}, 'MarkerFaceColor', leg_colors{k}, 'MarkerSize', 8, 'LineWidth', 2);
        end
        hold(sp_axes(2), 'off');
        
        L = legend(sp_axes(2), leg_handles, leg_labels, 'Orientation', 'horizontal', 'NumColumns', 2, 'FontSize', 12);
        L.Color = 'w';
        L.TextColor = 'k'; 
        L.Box = 'off';
        
        L.Position(1) = 0.5 - L.Position(3)/2;
        L.Position(2) = 0.02; 
    end
    
    full_path = fullfile(DIRS.verlauf, sprintf('%s_verlauf.png', group_name));
    exportgraphics(fig, full_path, 'Resolution', 300, 'BackgroundColor', 'w');
    close(fig);
end

function plot_range_analysis(subT, filename, folder_key, group_name, current_val, DIRS)
    fig = figure('Position', [100, 100, 1400, max(700, height(subT)*45)], 'Color', 'w', 'Visible', 'off');
    ax = axes('Parent', fig);
    hold(ax, 'on');
    
    ax.XGrid = 'on';
    ax.YGrid = 'off';
    
    COLOR_LOW = hex2rgb('#1f77b4');
    COLOR_NOM = hex2rgb('#2ca02c');
    COLOR_HIGH = hex2rgb('#d62728');
    y_pos = 1:height(subT);
    h = 0.25;
    b1 = barh(ax, y_pos - h, subT.nieder_ges, h, 'FaceColor', COLOR_LOW, 'EdgeColor', 'k');
    b2 = barh(ax, y_pos, subT.nenn_ges, h, 'FaceColor', COLOR_NOM, 'EdgeColor', 'k');
    b3 = barh(ax, y_pos + h, subT.ueber_ges, h, 'FaceColor', COLOR_HIGH, 'EdgeColor', 'k');
    
    all_vals = [subT.nieder_ges; subT.nenn_ges; subT.ueber_ges];
    valid_vals = all_vals(~isnan(all_vals));
    if ~isempty(valid_vals)
        max_v = max(valid_vals);
        min_v = min(valid_vals);
        xlim(ax, [min(0, min_v * 1.05), max(0, max_v * 1.05)]);
    end

    y_labels = cell(height(subT), 1);
    for i = 1:height(subT)
        y_labels{i} = format_label_text(subT(i,:), false);
        
        vals = [subT.nieder_ges(i), subT.nenn_ges(i), subT.ueber_ges(i)];
        offs = [-h, 0, h];
        for k = 1:3
            if ~isnan(vals(k)) && vals(k) ~= 0
                text(ax, vals(k) + 0.01, y_pos(i) + offs(k), format_value(vals(k)), 'VerticalAlignment', 'middle', 'FontSize', 12, 'Color', 'k');
            end
        end
    end
    yticks(ax, y_pos);
    yticklabels(ax, y_labels);
    set(ax, 'YDir', 'reverse');
    
    xlabel(ax, 'Mittlerer Fehler $|\varepsilon|$ [\%]', 'FontSize', 14, 'Color', 'k');
    
    plt_title = build_title('Fehleranalyse Bereiche', group_name, current_val);
    title(ax, sprintf('\\textbf{%s}', plt_title), 'FontSize', 18, 'Color', 'k');
    
    L = legend(ax, [b1, b2, b3], {'Niederlast', 'Nennlast', 'Überlast'}, 'Location', 'southoutside', 'Orientation', 'horizontal', 'FontSize', 12);
    L.TextColor = 'k';
    L.Box = 'off';
    
    full_path = fullfile(DIRS.(folder_key), filename);
    exportgraphics(fig, full_path, 'Resolution', 300, 'BackgroundColor', 'w');
    close(fig);
end

function plot_horizontal_generic(subT, value_col, base_title, group_name, current_val, x_label, filename, folder_key, is_cost, DIRS)
    fig = figure('Position', [100, 100, 1400, max(700, height(subT)*55)], 'Color', 'w', 'Visible', 'off');
    ax = axes('Parent', fig);
    hold(ax, 'on');
    
    ax.XGrid = 'on';
    ax.YGrid = 'off';
    
    y_pos = 1:height(subT);
    bar_height = 0.7;
    
    vals_for_lims = subT{:, value_col};
    valid_vals = vals_for_lims(~isnan(vals_for_lims));
    if ~isempty(valid_vals)
        max_v = max(valid_vals);
        min_v = min(valid_vals);
        xlim(ax, [min(0, min_v * 1.05), max(0, max_v * 1.05)]);
    end
    
    for i = 1:height(subT)
        val = subT{i, value_col};
        colHex = subT.color{i};
        colRgb = hex2rgb(colHex);
        geo = lower(char(subT.geometrie{i}));
        
        edgeCol = 'k';
        ls = '-';
        if contains(geo, 'dreieck')
            ls = '--';
            if is_dark_color(colHex), edgeCol = 'w'; end
        end
        
        barh(ax, y_pos(i), val, bar_height, 'FaceColor', colRgb, 'EdgeColor', edgeCol, 'LineStyle', ls, 'LineWidth', 1.5);
        
        txt = format_value(val);
        if is_cost
            txt = sprintf('%.2f EUR', val);
            text(ax, val + 0.01, y_pos(i), txt, 'VerticalAlignment', 'middle', 'FontSize', 14, 'Interpreter', 'latex', 'Color', 'k');
        else
            text(ax, val + 0.01, y_pos(i), txt, 'VerticalAlignment', 'middle', 'FontSize', 14, 'Color', 'k');
        end
    end
    
    y_labels = cell(height(subT), 1);
    for i = 1:height(subT)
        y_labels{i} = format_label_text(subT(i,:), true);
    end
    
    yticks(ax, y_pos);
    yticklabels(ax, y_labels);
    set(ax, 'YDir', 'reverse');
    
    if is_cost
        xlabel(ax, 'Kosten [EUR]', 'FontSize', 14, 'Interpreter', 'latex', 'Color', 'k');
    else
        xlabel(ax, x_label, 'FontSize', 14, 'Color', 'k');
    end
    
    plt_title = build_title(base_title, group_name, current_val);
    title(ax, sprintf('\\textbf{%s}', plt_title), 'FontSize', 18, 'Color', 'k');
    
    full_path = fullfile(DIRS.(folder_key), filename);
    exportgraphics(fig, full_path, 'Resolution', 300, 'BackgroundColor', 'w');
    close(fig);
end

function plot_unified_bars(T, y_col, plt_title, ylabel_str, filename, folder_key, DIRS)
    validIdx = ~isnan(T.(y_col)) & T.(y_col) ~= 0;
    subT = T(validIdx, :);
    if isempty(subT), return; end
    fig = figure('Position', [100, 100, 1600, 800], 'Color', 'w', 'Visible', 'off');
    ax = axes('Parent', fig);
    hold(ax, 'on');
    
    ax.XGrid = 'off';
    ax.YGrid = 'on';
    
    vals_for_lims = subT{:, y_col};
    valid_vals = vals_for_lims(~isnan(vals_for_lims));
    if ~isempty(valid_vals)
        max_v = max(valid_vals);
        min_v = min(valid_vals);
        ylim(ax, [min(0, min_v * 1.05), max(0, max_v * 1.05)]);
    end
    
    groups = unique(subT.nennstrom_num, 'stable');
    x_pos_list = 1:numel(groups);
    x_labels = cell(1, numel(groups));
    
    FIXED_BAR_WIDTH = 0.3;
    
    for i = 1:numel(groups)
        grp = groups(i);
        grpData = subT(subT.nennstrom_num == grp, :);
        x_labels{i} = sprintf('%d A', grp);
        
        n_bars = height(grpData);
        start_x = i - (n_bars * FIXED_BAR_WIDTH / 2);
        
        for j = 1:n_bars
            val = grpData{j, y_col};
            x = start_x + (j-1) * FIXED_BAR_WIDTH + FIXED_BAR_WIDTH/2;
            
            c = hex2rgb(grpData.color{j});
            edge = 'k';
            if is_dark_color(grpData.color{j}), edge = 'w'; end
            
            bar(ax, x, val, FIXED_BAR_WIDTH*0.9, 'FaceColor', c, 'EdgeColor', edge, 'LineWidth', 1.5);
            
            y_txt = val + sign(val)*0.5;
            if abs(val) < 2, y_txt = val + sign(val)*2; end
            text(ax, x, y_txt, format_value(val), 'HorizontalAlignment', 'center', 'FontSize', 12, 'Color', 'k');
        end
    end
    
    xticks(ax, x_pos_list);
    xticklabels(ax, x_labels);
    ylabel(ax, ylabel_str, 'FontSize', 14, 'Color', 'k');
    title(ax, sprintf('\\textbf{%s}', plt_title), 'FontSize', 22, 'Color', 'k');
    
    full_path = fullfile(DIRS.(folder_key), filename);
    exportgraphics(fig, full_path, 'Resolution', 300, 'BackgroundColor', 'w');
    close(fig);
end