export interface ChatPhoto {
    id: string;
    name: string;
}

export const PHOTO_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif", "image/avif"];
const MAX_PHOTO_BYTES = 10 * 1024 * 1024;
const STORE = "photos";

export function photoValidationError(file: File): string {
    if (!PHOTO_TYPES.includes(file.type)) return "Выберите фото в формате JPEG, PNG, WebP, GIF или AVIF.";
    if (!file.size) return "Этот файл пуст.";
    if (file.size > MAX_PHOTO_BYTES) return "Размер фото не должен превышать 10 МБ.";
    return "";
}

function openPhotoDatabase(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open("mathcontext-chat", 1);
        request.onupgradeneeded = () => request.result.createObjectStore(STORE);
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

export async function saveChatPhoto(userId: string, photo: ChatPhoto, file: File): Promise<void> {
    const db = await openPhotoDatabase();
    try {
        await new Promise<void>((resolve, reject) => {
            const transaction = db.transaction(STORE, "readwrite");
            transaction.oncomplete = () => resolve();
            transaction.onabort = () => reject(transaction.error);
            transaction.objectStore(STORE).put(file, [userId, photo.id]);
        });
    } finally {
        db.close();
    }
}

export async function readChatPhoto(userId: string, id: string): Promise<Blob | undefined> {
    const db = await openPhotoDatabase();
    try {
        return await new Promise<Blob | undefined>((resolve, reject) => {
            const request = db.transaction(STORE, "readonly").objectStore(STORE).get([userId, id]);
            request.onsuccess = () => resolve(request.result instanceof Blob ? request.result : undefined);
            request.onerror = () => reject(request.error);
        });
    } finally {
        db.close();
    }
}
