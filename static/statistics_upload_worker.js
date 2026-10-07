/* Keep the official import's A:BA source cells, including cached formula values. */
importScripts('/static/vendor/xlsx-0.20.3.min.js');

self.onmessage = ({data}) => {
    try {
        const names = XLSX.read(data, {type: 'array', bookSheets: true}).SheetNames
            .filter(name => /^wk\s*\d+$/i.test(name.trim()));
        if (!names.length) throw new Error('El archivo no contiene hojas Wk.');
        const input = XLSX.read(data, {
            type: 'array', sheets: names, dense: true,
            cellFormula: false, cellHTML: false, cellText: false
        });
        const output = XLSX.utils.book_new();
        for (const name of names) {
            const source = input.Sheets[name];
            if (!source || !source['!ref']) throw new Error(`La hoja ${name} esta vacia.`);
            const end = XLSX.utils.decode_range(source['!ref']).e.r;
            // Never remove interior blank rows: the server reads fixed 15-row blocks.
            const rows = XLSX.utils.sheet_to_json(source, {
                header: 1, raw: true, defval: null, blankrows: true,
                range: {s: {r: 0, c: 0}, e: {r: end, c: 52}}
            });
            XLSX.utils.book_append_sheet(output, XLSX.utils.aoa_to_sheet(rows), name);
        }
        const bytes = XLSX.write(output, {type: 'array', bookType: 'xlsx', compression: true});
        self.postMessage({bytes}, [bytes]);
    } catch (error) {
        self.postMessage({error: 'No se pudo preparar el Excel. Verifica que sea un archivo oficial valido.'});
    }
};
