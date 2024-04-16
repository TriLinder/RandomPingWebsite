import { writable } from 'svelte/store';

export const PERSISTENT_DATA_STORE_KEY = "trilinder.randomnotificationsite.persistentDataStore"; // Also duplicated in the service worker

type PersistentDataStore = {
    dataTypeVersion: number;
    serverInformation: undefined | {
        publicKey: Uint8Array;
        pingCooldown: number;
    }
    userInformation: undefined | {
        id: string;
        country: {
            iso: string,
            emoji: string
        };
    },
    stats: {
        sentPingsCount: number;
    }
}

function loadPersistentDataStore(): PersistentDataStore {
    // Load data from local storage if available
    const localStorageValue = localStorage.getItem(PERSISTENT_DATA_STORE_KEY);
    
    if (localStorageValue) {
        return JSON.parse(localStorageValue) as PersistentDataStore;
    }

    // Return default values otherwise
    console.log("Returning default persistent data store values.")
    return {
        "dataTypeVersion": 0,
        serverInformation: undefined,
        userInformation: undefined,
        stats: {
            sentPingsCount: 0
        }
    }
}

export const persistentDataStore = writable<PersistentDataStore>(loadPersistentDataStore());

persistentDataStore.subscribe(function(value) {
    localStorage.setItem(PERSISTENT_DATA_STORE_KEY, JSON.stringify(value));
});

window.addEventListener("storage", function(event) {
    if (event.key == PERSISTENT_DATA_STORE_KEY) {
        location.reload();
    }
});