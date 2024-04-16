import { writable } from 'svelte/store';

type PersistentDataStore = {
    dataTypeVersion: number;
    serverInformation: undefined | {
        publicKey: Uint8Array;
        pingCooldown: number;
    }
    userInformation: undefined | {
        id: string;
        country: string;
    },
    stats: {
        sentPingsCount: number;
    }
}

function loadPersistentDataStore(): PersistentDataStore {
    // Load data from local storage if available
    const localStorageValue = localStorage.getItem("trilinder.randomnotificationsite.persistentDataStore");
    
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
    localStorage.setItem("trilinder.randomnotificationsite.persistentDataStore", JSON.stringify(value));
});