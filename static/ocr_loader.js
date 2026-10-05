// Calendar OCR is optional; do not block match navigation on its download.
let scheduleOcrPromise = null;
function loadScheduleOcr() {
    if (window.Tesseract) return Promise.resolve(window.Tesseract);
    if (scheduleOcrPromise) return scheduleOcrPromise;
    scheduleOcrPromise = new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = "https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js";
        script.crossOrigin = "anonymous";
        script.async = true;
        script.onload = () => {
            if (window.Tesseract) resolve(window.Tesseract);
            else { script.remove(); scheduleOcrPromise = null; reject(new Error("No se pudo cargar el lector OCR. Reintenta la importación.")); }
        };
        script.onerror = () => {
            script.remove();
            scheduleOcrPromise = null;
            reject(new Error("No se pudo descargar el lector OCR. Revisa tu conexión y reintenta."));
        };
        document.head.appendChild(script);
    });
    return scheduleOcrPromise;
}
