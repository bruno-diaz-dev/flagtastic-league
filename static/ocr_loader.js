// Calendar OCR is optional; do not block match navigation on its download.
let scheduleOcrPromise = null;
function loadScheduleOcr() {
    if (window.Tesseract) return Promise.resolve(window.Tesseract);
    if (scheduleOcrPromise) return scheduleOcrPromise;
    scheduleOcrPromise = new Promise((resolve, reject) => {
        const script = document.createElement("script");
        // Pinned version with Subresource Integrity: the browser refuses the
        // file if the CDN ever serves different bytes. Update both together.
        script.src = "https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/tesseract.min.js";
        script.integrity = "sha384-GJqSu7vueQ9qN0E9yLPb3Wtpd7OrgK8KmYzC8T1IysG1bcvxvIO4qtYR/D3A991F";
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
