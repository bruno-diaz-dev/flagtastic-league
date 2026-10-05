// Durable referee outbox. A play keeps the same UUID until the server acknowledges it.
class LiveCaptureStore {
    constructor(scope) { this.scope = scope; this.database = null; }
    async open() {
        this.database = await new Promise((resolve, reject) => {
            const request = indexedDB.open("flagtastic-live-capture", 1);
            request.onupgradeneeded = () => {
                const plays = request.result.createObjectStore("plays", {keyPath: "id"});
                plays.createIndex("scope", "scope");
            };
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
            request.onblocked = () => reject(new Error("Cierra las otras pestañas del partido y reintenta."));
        });
    }
    async transact(mode, action) {
        return new Promise((resolve, reject) => {
            const transaction = this.database.transaction("plays", mode);
            const request = action(transaction.objectStore("plays"));
            transaction.oncomplete = () => resolve(request.result);
            transaction.onerror = () => reject(transaction.error);
            transaction.onabort = () => reject(transaction.error || new Error("No se guardó la captura local."));
        });
    }
    async list() {
        const rows = await this.transact("readonly", store => store.index("scope").getAll(this.scope));
        return rows.sort((a, b) => a.createdAt - b.createdAt || a.id.localeCompare(b.id));
    }
    put(play) { return this.transact("readwrite", store => store.put({...play, scope: this.scope})); }
    remove(id) { return this.transact("readwrite", store => store.delete(id)); }
}

class LiveCaptureQueue {
    constructor({store, send, onChange, onConfirmed, onError, canSend = () => true, schedule = (callback, delay) => setTimeout(callback, delay), cancel = timer => clearTimeout(timer)}) {
        Object.assign(this, {store, send, onChange, onConfirmed, onError, canSend, schedule, cancel});
        this.rows = []; this.working = false; this.timer = null; this.failures = 0;
    }
    async reload() { this.rows = await this.store.list(); this.onChange(this.rows); return this.rows; }
    enqueue(payload, labels) {
        const task = (this.persisting || Promise.resolve()).then(async () => {
            const rows = await this.store.list();
            const play = {id: payload.client_id, payload, labels, status: "pending", createdAt: Math.max(Date.now(), (rows.at(-1)?.createdAt || 0) + 1)};
            await this.store.put(play); // Never report a capture before its durable transaction completes.
            this.rows = [...rows, play];
            try { this.onChange(this.rows); } catch (error) { this.onError(error); }
            return play;
        });
        this.persisting = task.catch(() => {});
        return task;
    }
    async replace(id, payload, labels) {
        const existing = (await this.store.list()).find(row => row.id === id);
        if (!existing || existing.status !== "blocked" || existing.httpStatus !== 422) throw new Error("Esta jugada no está disponible para corregir.");
        await this.store.put({...existing, payload: {...payload, client_id: id}, labels, status: "pending", error: null, httpStatus: null});
        await this.reload();
    }
    async retry() {
        this.cancel(this.timer); this.timer = null;
        const first = (await this.store.list())[0];
        if (first) await this.store.put({...first, status: "pending", error: null});
        await this.reload();
        return this.flush();
    }
    async flush() {
        if (this.working || !this.canSend()) return;
        this.cancel(this.timer); this.timer = null; this.working = true;
        let confirmed = false;
        try {
            while (this.canSend()) {
                const play = (await this.reload())[0];
                if (!play || play.status === "blocked") break;
                await this.store.put({...play, status: "sending"});
                await this.reload();
                try {
                    await this.send(play.payload);
                    await this.store.remove(play.id);
                    this.failures = 0; confirmed = true;
                } catch (error) {
                    const blocked = error.status >= 400 && error.status < 500 && ![408, 429].includes(error.status);
                    const message = error.status ? error.message : "No se confirmó el envío. La captura sigue guardada y se reintentará.";
                    await this.store.put({...play, status: blocked ? "blocked" : "retry", error: message, httpStatus: error.status || null});
                    if (!blocked) {
                        this.failures += 1;
                        this.timer = this.schedule(() => { this.flush().catch(this.onError); }, Math.min(60000, 3000 * 2 ** Math.min(this.failures, 4)));
                    }
                    break; // Preserve play order; never skip a failed play.
                }
            }
        } finally {
            this.working = false;
            await this.reload();
            if (confirmed) this.onConfirmed();
        }
    }
}
globalThis.LiveCaptureStore = LiveCaptureStore;
globalThis.LiveCaptureQueue = LiveCaptureQueue;
