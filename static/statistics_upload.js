const STATISTICS_UPLOAD_LIMIT = 4 * 1024 * 1024;

async function prepareStatisticsUpload(file) {
    if (!file || !/\.xlsx$/i.test(file.name)) throw new Error('Selecciona un archivo .xlsx.');
    if (file.size > 15 * 1024 * 1024) throw new Error('El archivo excede 15 MB.');
    if (file.size <= STATISTICS_UPLOAD_LIMIT) return file;
    const buffer = await file.arrayBuffer();
    return new Promise((resolve, reject) => {
        const worker = new Worker('/static/statistics_upload_worker.js?v=20261007-1');
        const timeout = setTimeout(() => finish(new Error('El Excel tardo demasiado en prepararse. Intenta con una copia mas pequena.')), 120000);
        function finish(error, result) {
            clearTimeout(timeout);
            worker.terminate();
            if (error) reject(error); else resolve(result);
        }
        worker.onerror = () => finish(new Error('No se pudo preparar el Excel. Recarga la pagina e intenta de nuevo.'));
        worker.onmessage = ({data}) => {
            if (data.error) return finish(new Error(data.error));
            const prepared = new File([data.bytes], file.name, {type: file.type});
            if (prepared.size > STATISTICS_UPLOAD_LIMIT) {
                return finish(new Error('El Excel sigue siendo demasiado grande. Divide las hojas Wk en archivos separados.'));
            }
            finish(null, prepared);
        };
        worker.postMessage(buffer, [buffer]);
    });
}

async function readStatisticsImportResponse(response) {
    if (response.status === 413) {
        throw new Error('El archivo supera el limite de carga del servidor. Usa un Excel mas pequeno.');
    }
    const data = await response.json().catch(() => null);
    if (!response.ok) {
        throw new Error(typeof data?.detail === 'string' ? data.detail : 'No se pudo importar el archivo. Intenta nuevamente.');
    }
    if (!data || !Array.isArray(data.weeks)) throw new Error('El servidor devolvio una respuesta inesperada.');
    return data;
}
