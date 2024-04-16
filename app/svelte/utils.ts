import { persistentDataStore } from "./stores";
import { get } from "svelte/store";

export function base64ToUint8Array(base64String) {
    // Calculate the padding needed for the base64 string
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    
    // Replace characters that are not compatible with base64 encoding
    const normalizedBase64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/_/g, '/');
    
    // Decode the base64 string
    const binaryString = window.atob(normalizedBase64);
    
    // Create a Uint8Array to hold the decoded binary data
    const uint8Array = new Uint8Array(binaryString.length);
    
    // Convert each character in the binary string to its character code
    for (let i = 0; i < binaryString.length; ++i) {
        uint8Array[i] = binaryString.charCodeAt(i);
    }
    
    // Return the Uint8Array containing the decoded binary data
    return uint8Array;
}

export async function fetchServerInformation() {
    const response = await fetch("/info");
    const json = await response.json() as {public_key: string, ping_cooldown: number};
    
    // Update the data store
    const persistentDataStoreValue = get(persistentDataStore);
    persistentDataStoreValue.serverInformation = {
        publicKey: base64ToUint8Array(json.public_key),
        pingCooldown: json.ping_cooldown
    }
    persistentDataStore.set(persistentDataStoreValue);
}

export async function getPushServiceSubscriptionObject(): Promise<PushSubscription> {
    if (!get(persistentDataStore).serverInformation) {
        await fetchServerInformation();
    }
    
    const reg = await navigator.serviceWorker.ready;
    const subscription = await reg.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: get(persistentDataStore).serverInformation!.publicKey
        });

    return subscription;
}

export async function registerAccount() {
    const response = await fetch("/user/register", {method: "POST"});
    const json = await response.json() as {user_id: string, country: {iso: string, emoji: string}};

    const persistentDataStoreValue = get(persistentDataStore);
    persistentDataStoreValue.userInformation = {
        id: json.user_id,
        country: {
            iso: json.country.iso,
            emoji: json.country.emoji
        }
    }
    persistentDataStore.set(persistentDataStoreValue);
}

export async function updatePushServiceSubscriptionObject(subscription: PushSubscription) {
    if (!get(persistentDataStore).userInformation) {
        throw Error("User information not available")
    }
    
    const response = await fetch("/user/update_notification_subscription_object", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            user_id: get(persistentDataStore).userInformation?.id,
            subscription: subscription
        })
    });

    // Handle errors
    if (response.status != 200) {
        throw Error(`Unexpected status code: ${response.status}`);
    }
    const json = await response.json();
    if (!json.ok) {
        throw Error(json.error);
    }
}


export async function sendRandomPing(displayCountryOfOrigin = true) {
    if (!get(persistentDataStore).userInformation) {
        throw Error("User information not available")
    }
    
    const response = await fetch("/ping/random", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            user_id: get(persistentDataStore).userInformation?.id,
            display_country_of_origin: displayCountryOfOrigin
        })
    });

    // Handle errors
    if (response.status != 200) {
        throw Error(`Unexpected status code: ${response.status}`);
    }
    const json = await response.json();
    if (!json.ok) {
        throw Error(json.error);
    }
}

export async function replyToPing(replyTo: string) {
    if (!get(persistentDataStore).userInformation) {
        throw Error("User information not available")
    }
    
    const response = await fetch("/ping/reply", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            user_id: get(persistentDataStore).userInformation?.id,
            reply_to: replyTo
        })
    });

    // Handle errors
    if (response.status != 200) {
        throw Error(`Unexpected status code: ${response.status}`);
    }
    const json = await response.json();
    if (!json.ok) {
        throw Error(json.error);
    }
}