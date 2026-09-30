const ACTIVE_SCHEDULE_FIELDS = 6;
const TIME_COLUMN_RATIO = 0.027;
const OCR_BATCH_SIZE = 20;
const GRID_LINE_DARK_RATIO = 0.45;

function parseScheduleTsv(tsv) {
    return String(tsv || "")
        .split("\n")
        .slice(1)
        .map((line) => line.split("\t"))
        .filter((columns) => columns.length >= 12 && columns[0] === "5")
        .map((columns) => ({
            text: columns.slice(11).join("\t").trim(),
            left: Number(columns[6]),
            top: Number(columns[7]),
            width: Number(columns[8]),
            height: Number(columns[9])
        }))
        .filter((word) => word.text);
}

async function scheduleSourceCanvas(file) {
    const url = URL.createObjectURL(file);
    try {
        const image = await new Promise((resolve, reject) => {
            const element = new Image();
            element.onload = () => resolve(element);
            element.onerror = () => reject(new Error("No se pudo leer la imagen."));
            element.src = url;
        });
        const canvas = document.createElement("canvas");
        canvas.width = image.naturalWidth;
        canvas.height = image.naturalHeight;
        canvas.getContext("2d", {willReadFrequently: true}).drawImage(image, 0, 0);
        return canvas;
    } finally {
        URL.revokeObjectURL(url);
    }
}

function scheduleGridLineCenters(darkRatios, height) {
    const candidates = [];
    for (let y = 0; y < darkRatios.length; y += 1) {
        if (darkRatios[y] >= GRID_LINE_DARK_RATIO) candidates.push(y);
    }

    const groups = [];
    for (const y of candidates) {
        const last = groups[groups.length - 1];
        if (!last || y > last[last.length - 1] + 1) groups.push([y]);
        else last.push(y);
    }
    const centers = groups.map((group) => Math.round(
        group.reduce((sum, value) => sum + value, 0) / group.length
    ));

    const minGap = height * 0.04;
    const maxGap = height * 0.10;
    const tolerance = height * 0.018;
    let best = [];
    for (let start = 0; start < centers.length; start += 1) {
        const sequence = [centers[start]];
        let expected = null;
        for (let index = start + 1; index < centers.length; index += 1) {
            const gap = centers[index] - sequence[sequence.length - 1];
            if (gap < minGap) continue;
            if (gap > maxGap) break;
            if (expected !== null && Math.abs(gap - expected) > tolerance) continue;
            sequence.push(centers[index]);
            expected = expected === null ? gap : expected * 0.7 + gap * 0.3;
        }
        if (sequence.length > best.length) best = sequence;
    }
    if (best.length < 4) throw new Error("No se pudo detectar la cuadrícula del rol.");
    return best;
}

function scheduleGridLines(canvas) {
    const context = canvas.getContext("2d", {willReadFrequently: true});
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
    const sampleStep = Math.max(1, Math.floor(canvas.width / 800));
    const darkRatios = [];

    for (let y = 0; y < canvas.height; y += 1) {
        let dark = 0;
        let total = 0;
        for (let x = 0; x < canvas.width; x += sampleStep) {
            const offset = (y * canvas.width + x) * 4;
            const gray = (
                pixels[offset] * 0.299
                + pixels[offset + 1] * 0.587
                + pixels[offset + 2] * 0.114
            );
            if (gray < 115) dark += 1;
            total += 1;
        }
        darkRatios.push(dark / total);
    }
    return scheduleGridLineCenters(darkRatios, canvas.height);
}

function cellSource(canvas, cell) {
    const margin = Math.max(2, Math.round(canvas.width * 0.0008));
    const x = Math.max(0, Math.round(cell.x0 + margin));
    const y = Math.max(0, Math.round(cell.y0 + margin));
    const right = Math.min(canvas.width, Math.round(cell.x1 - margin));
    const bottom = Math.min(canvas.height, Math.round(cell.y1 - margin));
    const width = Math.max(1, right - x);
    const height = Math.max(1, bottom - y);
    const image = canvas.getContext("2d", {willReadFrequently: true})
        .getImageData(x, y, width, height);
    return {image, width, height};
}

function prepareScheduleCell(canvas, cell, scale = 4) {
    const source = cellSource(canvas, cell);
    const histogram = new Array(256).fill(0);
    let darkPixels = 0;
    const total = source.width * source.height;

    for (let index = 0; index < source.image.data.length; index += 4) {
        const gray = Math.round(
            source.image.data[index] * 0.299
            + source.image.data[index + 1] * 0.587
            + source.image.data[index + 2] * 0.114
        );
        histogram[gray] += 1;
        if (gray < 220) darkPixels += 1;
    }

    let cumulative = 0;
    let background = 255;
    const target = total * 0.90;
    for (let value = 0; value < 256; value += 1) {
        cumulative += histogram[value];
        if (cumulative >= target) {
            background = value;
            break;
        }
    }

    const blank = background > 248 && darkPixels / total < 0.01;
    const threshold = Math.max(45, Math.min(190, Math.round(background * 0.68)));
    const binary = document.createElement("canvas");
    binary.width = source.width;
    binary.height = source.height;
    const context = binary.getContext("2d");
    const output = context.createImageData(source.width, source.height);

    for (let index = 0; index < source.image.data.length; index += 4) {
        const gray = Math.round(
            source.image.data[index] * 0.299
            + source.image.data[index + 1] * 0.587
            + source.image.data[index + 2] * 0.114
        );
        const value = gray < threshold ? 0 : 255;
        output.data[index] = value;
        output.data[index + 1] = value;
        output.data[index + 2] = value;
        output.data[index + 3] = 255;
    }
    context.putImageData(output, 0, 0);
    return {cell, binary, blank, scale};
}

function scheduleContactSheet(canvas, cells) {
    const prepared = cells.map((cell) => prepareScheduleCell(canvas, cell));
    const paddingX = 40;
    const paddingY = 20;
    const gap = 20;
    const width = Math.max(...prepared.map(
        (item) => item.binary.width * item.scale + paddingX * 2
    ));
    const heights = prepared.map(
        (item) => item.binary.height * item.scale + paddingY * 2
    );
    const height = heights.reduce((sum, value) => sum + value + gap, 0);
    const sheet = document.createElement("canvas");
    sheet.width = width;
    sheet.height = height;
    const context = sheet.getContext("2d");
    context.fillStyle = "#fff";
    context.fillRect(0, 0, width, height);
    context.imageSmoothingEnabled = false;

    const slots = [];
    let top = 0;
    prepared.forEach((item, index) => {
        const slotHeight = heights[index];
        context.drawImage(
            item.binary,
            paddingX,
            top + paddingY,
            item.binary.width * item.scale,
            item.binary.height * item.scale
        );
        slots.push({key: item.cell.key, top, bottom: top + slotHeight});
        top += slotHeight + gap;
    });
    return {sheet, slots};
}

function scheduleLabels(tsv, slots) {
    const grouped = new Map(slots.map((slot) => [slot.key, []]));
    for (const word of parseScheduleTsv(tsv)) {
        const centerY = word.top + word.height / 2;
        const slot = slots.find(
            (candidate) => centerY >= candidate.top && centerY < candidate.bottom
        );
        if (slot) grouped.get(slot.key).push(word);
    }
    const labels = new Map();
    for (const slot of slots) {
        const words = grouped.get(slot.key)
            .sort((a, b) => a.left - b.left)
            .map((word) => word.text);
        labels.set(slot.key, words.join(" ").trim());
    }
    return labels;
}

async function recognizeScheduleCells(worker, canvas, cells, options = {}) {
    const labels = new Map();
    const usable = cells.filter((cell) => !prepareScheduleCell(canvas, cell).blank);
    const whitelist = options.whitelist || (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz" +
        "ÁÉÍÓÚÜÑáéíóúüñ0123456789 .'-"
    );

    for (let offset = 0; offset < usable.length; offset += OCR_BATCH_SIZE) {
        const batch = usable.slice(offset, offset + OCR_BATCH_SIZE);
        const {sheet, slots} = scheduleContactSheet(canvas, batch);
        await worker.setParameters({
            tessedit_char_whitelist: whitelist,
            tessedit_pageseg_mode: "6",
            preserve_interword_spaces: "1"
        });
        const result = await worker.recognize(sheet, {}, {tsv: true});
        scheduleLabels(result.data.tsv, slots)
            .forEach((value, key) => labels.set(key, value));
        if (options.progress) {
            options.progress(Math.min(offset + batch.length, usable.length), usable.length);
        }
    }
    return labels;
}

function scheduleTimeMinutes(value) {
    const cleaned = String(value || "")
        .toUpperCase()
        .replaceAll("O", "0")
        .replaceAll("I", "1")
        .replaceAll("L", "1")
        .replace(/[.;,]/g, ":")
        .replace(/\s+/g, "");
    const match = cleaned.match(/^(\d{1,2}):?(\d{2})$/);
    if (!match) return null;
    const hour = Number(match[1]);
    const minute = Number(match[2]);
    if (hour > 23 || minute > 59) return null;
    return hour * 60 + minute;
}

function scheduleMedian(values) {
    const sorted = [...values].sort((a, b) => a - b);
    if (!sorted.length) return null;
    const middle = Math.floor(sorted.length / 2);
    return sorted.length % 2
        ? sorted[middle]
        : (sorted[middle - 1] + sorted[middle]) / 2;
}

function regularScheduleTimes(values) {
    // A break in the schedule is legitimate; OCR must never regularize it.
    return values.map((value) => Number.isInteger(value) && value >= 0 && value < 1440 ? value : null);
}

function scheduleTimeText(minutes) {
    if (minutes === null) return null;
    const value = ((minutes % 1440) + 1440) % 1440;
    const hour = Math.floor(value / 60);
    const minute = value % 60;
    return String(hour).padStart(2, "0") + ":" + String(minute).padStart(2, "0");
}

window.analyzeScheduleImageCells = async function(file, week, progress) {
    if (!window.Tesseract) throw new Error("El lector OCR del navegador no está disponible.");
    progress("Detectando cuadrícula...");
    const canvas = await scheduleSourceCanvas(file);
    const lines = scheduleGridLines(canvas);
    const rows = lines.slice(0, -1).map((top, index) => ({
        index,
        top,
        bottom: lines[index + 1]
    }));
    const timeWidth = canvas.width * TIME_COLUMN_RATIO;

    let worker = null;
    try {
        worker = await window.Tesseract.createWorker("eng", 1);
        const timeCells = rows.map((row) => ({
            key: "time:" + row.index,
            x0: 0,
            x1: timeWidth,
            y0: row.top,
            y1: row.bottom
        }));

        progress("Leyendo horarios...");
        const timeLabels = await recognizeScheduleCells(worker, canvas, timeCells, {
            whitelist: "0123456789:"
        });
        // Narrow time cells often disappear in block OCR. Retry individually
        // as a single line, with padding and enlarged glyphs, never inferred hours.
        for (const cell of timeCells) {
            if (scheduleTimeMinutes(timeLabels.get(cell.key)) !== null) continue;
            const {sheet} = scheduleContactSheet(canvas, [cell]);
            await worker.setParameters({
                tessedit_char_whitelist: "0123456789:.,",
                tessedit_pageseg_mode: "7"
            });
            const result = await worker.recognize(sheet);
            const text = result.data.text || "";
            if (scheduleTimeMinutes(text) !== null) timeLabels.set(cell.key, text);
        }
        const parsed = rows.map((row) =>
            scheduleTimeMinutes(timeLabels.get("time:" + row.index))
        );
        // Preserve unreadable times as null so administrators can correct them.
        const dataRows = rows;
        const times = regularScheduleTimes(parsed);
        const subcolumnWidth = (
            canvas.width - timeWidth
        ) / (ACTIVE_SCHEDULE_FIELDS * 2);

        const teamCells = [];
        const games = [];
        dataRows.forEach((row, rowIndex) => {
            for (let field = 0; field < ACTIVE_SCHEDULE_FIELDS; field += 1) {
                const homeIndex = field * 2;
                const awayIndex = homeIndex + 1;
                const home = {
                    key: "team:" + rowIndex + ":" + field + ":home",
                    x0: timeWidth + homeIndex * subcolumnWidth,
                    x1: timeWidth + (homeIndex + 1) * subcolumnWidth,
                    y0: row.top,
                    y1: row.bottom
                };
                const away = {
                    key: "team:" + rowIndex + ":" + field + ":away",
                    x0: timeWidth + awayIndex * subcolumnWidth,
                    x1: timeWidth + (awayIndex + 1) * subcolumnWidth,
                    y0: row.top,
                    y1: row.bottom
                };
                const homeBlank = prepareScheduleCell(canvas, home).blank;
                const awayBlank = prepareScheduleCell(canvas, away).blank;
                if (homeBlank && awayBlank) continue;
                if (!homeBlank) teamCells.push(home);
                if (!awayBlank) teamCells.push(away);
                games.push({rowIndex, field, home, away, homeBlank, awayBlank});
            }
        });

        progress("Leyendo equipos...");
        const labels = await recognizeScheduleCells(worker, canvas, teamCells, {
            progress: (done, total) => progress("Leyendo equipos... " + done + "/" + total)
        });

        const payloadRows = games.map((game) => ({
            field_number: game.field + 1,
            start_time: scheduleTimeText(times[game.rowIndex]),
            home_team: game.homeBlank
                ? "(sin texto)"
                : (labels.get(game.home.key) || "(sin texto)"),
            away_team: game.awayBlank
                ? "(sin texto)"
                : (labels.get(game.away.key) || "(sin texto)")
        }));
        if (!payloadRows.length) throw new Error("No se reconocieron partidos en la imagen.");

        progress("Relacionando equipos reconocidos...");
        return fetch("/api/games/schedule/analyze-cells", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({week: Number(week), rows: payloadRows})
        });
    } finally {
        if (worker) await worker.terminate();
    }
};
