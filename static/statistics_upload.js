// Keep multipart uploads below the 1 MiB spool threshold on the server.
const STATISTICS_UPLOAD_LIMIT = 900 * 1024;

async function prepareStatisticsUpload(file) {
    if (!file || !/\.xlsx$/i.test(file.name)) throw new Error('Selecciona un archivo .xlsx.');
    if (file.size > 15 * 1024 * 1024) throw new Error('El archivo excede 15 MB.');
    if (file.size <= STATISTICS_UPLOAD_LIMIT) return file;
    let buffer;
    try {
        buffer = await file.arrayBuffer();
    } catch {
        throw new Error('No se pudo leer el archivo del dispositivo. Descárgalo por completo y selecciónalo de nuevo.');
    }
    return new Promise((resolve, reject) => {
        const worker = new Worker('/static/statistics_upload_worker.js?v=20261015-1');
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
                return finish(new Error('No se pudo reducir el Excel lo suficiente para enviarlo de forma segura. No se enviaron datos al servidor.'));
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
    if (response.status >= 500) {
        throw new Error(`El servidor falló al recibir o procesar el Excel (HTTP ${response.status}). No se pudo confirmar el resultado; revisa las estadísticas antes de repetir la carga.`);
    }
    const data = await response.json().catch(() => null);
    if (!response.ok) {
        throw new Error(typeof data?.detail === 'string' ? data.detail : 'No se pudo importar el archivo. Intenta nuevamente.');
    }
    if (!data || !Number.isInteger(data.imported) ||
        (data.weeks !== undefined && !Array.isArray(data.weeks))) {
        throw new Error('El servidor devolvio una respuesta inesperada.');
    }
    return data;
}
