function importRequest(url, options, onProgress) {
    if (!onProgress || typeof XMLHttpRequest === "undefined") return fetch(url, options);
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open(options.method || "GET", url);
        xhr.withCredentials = true;
        for (const [name, value] of Object.entries(options.headers || {})) xhr.setRequestHeader(name, value);
        xhr.upload.onprogress = (event) => {
            if (event.lengthComputable) onProgress({phase: "upload", loaded: event.loaded, total: event.total});
        };
        xhr.upload.onload = () => onProgress({phase: "processing"});
        xhr.onload = () => {
            onProgress({phase: "response"});
            const headers = new Headers();
            xhr.getAllResponseHeaders().trim().split(/[\r\n]+/).filter(Boolean).forEach((line) => {
                const separator = line.indexOf(":");
                if (separator > 0) headers.append(line.slice(0, separator), line.slice(separator + 1).trim());
            });
            resolve(new Response(xhr.responseText, {status: xhr.status, statusText: xhr.statusText, headers}));
        };
        xhr.onerror = () => reject(new TypeError("Error de red al importar."));
        xhr.onabort = () => reject(new TypeError("Se canceló la importación."));
        onProgress({phase: "start"});
        xhr.send(options.body || null);
    });
}

const importProgressTimers = new WeakMap();
function updateImportProgress(element, percent, message = "") {
    if (!element) return;
    clearTimeout(importProgressTimers.get(element));
    element.classList.remove("is-complete", "is-error");
    const value = Math.max(0, Math.min(100, Math.round(percent)));
    element.hidden = false;
    element.setAttribute("aria-valuenow", String(value));
    element.setAttribute("aria-valuetext", `${value}%${message ? ` ${message}` : ""}`);
    const fill = element.querySelector(".import-progress-fill, .schedule-save-progress-fill");
    if (fill) fill.style.width = `${value}%`;
    const label = element.querySelector(".import-progress-percent");
    if (label) label.textContent = `${value}%${message ? ` · ${message}` : ""}`;
}

function updateRequestProgress(element, event) {
    if (!event) return;
    if (event.phase === "start") updateImportProgress(element, 1, "Preparando envío");
    else if (event.phase === "upload") {
        updateImportProgress(element, event.total ? 2 + 88 * event.loaded / event.total : 2, "Enviando archivo");
    } else if (event.phase === "processing") updateImportProgress(element, 92, "Procesando en servidor");
    else if (event.phase === "response") updateImportProgress(element, 98, "Recibiendo resultado");
}

function finishImportProgress(element, success) {
    if (!element) return;
    clearTimeout(importProgressTimers.get(element));
    updateImportProgress(element, 100, success ? "Completado" : "Finalizado");
    element.classList.toggle("is-complete", Boolean(success));
    element.classList.toggle("is-error", !success);
    importProgressTimers.set(element, setTimeout(() => { element.hidden = true; element.classList.remove("is-complete", "is-error"); }, 1800));
}
