<script lang="ts">
    import { fetchServerInformation, getPushServiceSubscriptionObject, registerAccount, updatePushServiceSubscriptionObject, finalizeAccountCreation } from "../../utils";
    import { createEventDispatcher } from 'svelte';
    import { Button, Modal, Spinner } from '@sveltestrap/sveltestrap';

    let registering = false;
    let stage: "notificationPermission" | "fetchServerInfo" | "pushServiceSubscription" | "accountRegistration" | "finalizing" | "error" = "notificationPermission";
    let errorMessage = "";

    const dispatch = createEventDispatcher();

    function showErrorMessage(error) {
        errorMessage = error;
        stage = "error";
    }

    async function register() {
        registering = true;

        // First ask the user for notification permissons
        if (await Notification.requestPermission() == "denied") {
            showErrorMessage("You must accept notifications to continue.");
            return;
        }

        // Now get server information (most notably the public key) from the server
        stage = "fetchServerInfo";
        try {
            await fetchServerInformation();
        } catch(error) {
            showErrorMessage(`Failed to fetch server information: ${error}`);
            return;
        }
        
        // Next subscribe to the push service and get the subscription object
        stage = "pushServiceSubscription";
        let subscription: PushSubscription;
        try {
            subscription = await getPushServiceSubscriptionObject();
        } catch(error) {
            showErrorMessage(`Failed to get subscription object. Does your device and browser support push notifications? ${error}`);
            return;
        }

        // Register an account and attach the subscription object to it
        stage = "accountRegistration";
        try {
            await registerAccount();
            await updatePushServiceSubscriptionObject(subscription);
        } catch(error) {
            showErrorMessage(`Failed to send information to server: ${error}`);
            return;
        }

        // And finally, finalize the account creation process by sending a test notification.
        // This is required for being able to send and recieve pings.
        // If this fails, the account is automatically deleted and this page is reloaded, so
        // there's no point in handling any errors.
        stage = "finalizing";
        await finalizeAccountCreation();
        
        // Done! :)
        // We will now be taken to the next page.
        dispatch("registered");
    }
</script>

<style>
    .modal-body {
        display: flex;
        flex-direction: column;
        width: 100%;
        height: 100%;
        justify-content: center;
        align-items: center;
    }

    p {
        text-align: center;
    }
</style>

<Modal body header="Please wait" isOpen={registering}>
    <div class="modal-body">
        {#if stage == "notificationPermission"}
            Please accept notifications to continue. <br>
            <Spinner type="border" color="primary"/>
        {:else if stage == "fetchServerInfo"}
            Fetching server information <br>
            <Spinner type="border" color="primary"/>
        {:else if stage == "pushServiceSubscription"}
            Subscribing to push service <br>
            <Spinner type="border" color="primary"/>
        {:else if stage == "accountRegistration"}
            Sending data to server <br>
            <Spinner type="border" color="primary"/>
        {:else if stage == "finalizing"}
            Finalizing. Please wait, this can take a while. <br>
            <Spinner type="border" color="primary"/>
        {:else if stage == "error"}
            <h2>Error</h2>
            {errorMessage} <br>
            Please try again later.
        {/if}
    </div>
</Modal>

<h1>RandomPing</h1>
<p>Turn on notifications and ping other random users! Don't worry, you can always easily opt out and delete all your data. No sign up needed.</p>
<Button on:click={register} disabled={registering} color="primary">Turn on notifications</Button>