// Public player registration controller; credentials are sent only to the API.

const registerForm = document.querySelector("#register-form");
const registerMessage = document.querySelector("#register-message");
const SAFE_PROFILE_UPLOAD_BYTES = 3 * 1024 * 1024;
const PROFILE_PHOTO_MAX_DIMENSION = 1600;


function canvasBlob(canvas, quality) {
    return new Promise((resolve, reject) => {
        canvas.toBlob(
            (blob) => blob ? resolve(blob) : reject(new Error("Image compression failed")),
            "image/jpeg",
            quality
        );
    });
}


async function decodedPhoto(file) {
    if (typeof createImageBitmap === "function") {
        return createImageBitmap(file, {imageOrientation: "from-image"});
    }
    const objectUrl = URL.createObjectURL(file);
    try {
        const image = new Image();
        image.src = objectUrl;
        await image.decode();
        return image;
    } catch (error) {
        URL.revokeObjectURL(objectUrl);
        throw error;
    }
}


async function optimizeProfilePhoto(file) {
    // Vercel rejects large multipart bodies before FastAPI can explain the
    // error. Keep the complete request comfortably below that platform limit.
    if (!(file instanceof File) || file.size <= SAFE_PROFILE_UPLOAD_BYTES) return file;

    const image = await decodedPhoto(file);
    const sourceWidth = image.naturalWidth || image.width;
    const sourceHeight = image.naturalHeight || image.height;
    const scale = Math.min(
        1,
        PROFILE_PHOTO_MAX_DIMENSION / Math.max(sourceWidth, sourceHeight)
    );
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(sourceWidth * scale));
    canvas.height = Math.max(1, Math.round(sourceHeight * scale));
    const context = canvas.getContext("2d");
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0, canvas.width, canvas.height);

    let blob = null;
    for (const quality of [0.86, 0.74, 0.62, 0.50]) {
        blob = await canvasBlob(canvas, quality);
        if (blob.size <= SAFE_PROFILE_UPLOAD_BYTES) break;
    }
    if (typeof image.close === "function") image.close();
    if (image.src?.startsWith("blob:")) URL.revokeObjectURL(image.src);
    if (!blob || blob.size > SAFE_PROFILE_UPLOAD_BYTES) {
        throw new Error("Optimized image is still too large");
    }
    const baseName = file.name.replace(/\.[^.]+$/, "") || "perfil";
    return new File([blob], `${baseName}.jpg`, {
        type: "image/jpeg",
        lastModified: Date.now()
    });
}

registerForm.elements.curp.addEventListener("input", (event) => {
    registerForm.elements.age.value = calendarAgeFromCurp(event.target.value) ?? "";
});

registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fields = new FormData(registerForm);
    registerMessage.textContent = "Creando cuenta...";

    try {
        const originalPhoto = fields.get("photo");
        if (originalPhoto?.size > SAFE_PROFILE_UPLOAD_BYTES) {
            registerMessage.textContent = "Optimizando foto...";
            const optimizedPhoto = await optimizeProfilePhoto(originalPhoto);
            fields.set("photo", optimizedPhoto, optimizedPhoto.name);
            registerMessage.textContent = "Creando cuenta...";
        }
        const response = await registerPlayerAccount(fields);
        if (!response.ok) {
            let detail = "No se pudo crear la cuenta.";
            if (response.status === 413) {
                detail = "La foto es demasiado grande. Elige otra imagen e intenta nuevamente.";
            } else if (response.headers.get("content-type")?.includes("application/json")) {
                const error = await response.json();
                detail = error.detail || detail;
            } else if (response.status >= 500) {
                detail = "Ocurrió un error interno. Revisa las migraciones del servidor.";
            }
            registerMessage.textContent = detail;
            return;
        }
        window.location.assign("/login");
    } catch (error) {
        registerMessage.textContent = error instanceof TypeError
            ? "No se pudo conectar con el servidor."
            : "No se pudo procesar la foto. Elige una imagen JPG, PNG o WebP.";
    }
});
