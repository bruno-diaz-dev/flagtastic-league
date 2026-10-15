/* Keep the official import's A:BA source cells, including cached formula values. */
importScripts('/static/vendor/xlsx-0.20.3.min.js');

self.onmessage = ({data}) => {
    try {
        const allNames = XLSX.read(data, {type: 'array', bookSheets: true}).SheetNames;
        let names = allNames.filter(name => /^wk\s*\d+$/i.test(name.trim()));
        // Compact templates and single-sheet official imports have no Wk name.
        if (!names.length) names = allNames.slice(0, 1);
        if (!names.length) throw new Error('El archivo no contiene hojas.');
        const input = XLSX.read(data, {
            type: 'array', sheets: names, dense: true,
            cellFormula: false, cellHTML: false, cellText: false
        });
        const output = XLSX.utils.book_new();
        let included = 0;
        for (const name of names) {
            const source = input.Sheets[name];
            if (!source || !source['!ref']) throw new Error(`La hoja ${name} esta vacia.`);
            const end = XLSX.utils.decode_range(source['!ref']).e.r;
            // Never remove interior blank rows: the server reads fixed 15-row blocks.
            const rows = XLSX.utils.sheet_to_json(source, {
                header: 1, raw: true, defval: null, blankrows: true,
                range: {s: {r: 0, c: 0}, e: {r: end, c: 52}}
            });
            const hasTeam = rows.some(row => {
                const team = String(row[0] ?? '').trim();
                return team && team.toLocaleLowerCase('es-MX') !== 'equipo'
                    && String(row[1] ?? '').trim() && String(row[2] ?? '').trim();
            });
            // Empty Wk templates carry thousands of formula/label cells but
            // no team data. They are ignored by the server as well.
            if (!hasTeam) continue;
            for (const row of rows) {
                for (let index = 0; index < row.length; index += 1) {
                    if (row[index] === '') row[index] = null;
                }
                while (row.length && (row.at(-1) === null || row.at(-1) === '')) row.pop();
            }
            while (rows.length && rows.at(-1).length === 0) rows.pop();
            XLSX.utils.book_append_sheet(output, XLSX.utils.aoa_to_sheet(rows), name);
            included += 1;
        }
        if (!included) throw new Error('El archivo no contiene jornadas con equipos.');
        const bytes = XLSX.write(output, {type: 'array', bookType: 'xlsx', compression: true, bookSST: true});
        self.postMessage({bytes}, [bytes]);
    } catch (error) {
        self.postMessage({error: 'No se pudo preparar el Excel. Verifica que sea un archivo oficial valido.'});
    }
};
