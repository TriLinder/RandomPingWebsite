<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import confetti from 'canvas-confetti';
    import { replyToPing } from '../../utils';

    import { Button } from '@sveltestrap/sveltestrap';
    import AccountDeletionLink from '../../components/AccountDeletionLink.svelte';

    const replyTo = window.location.hash.substring(1); // The original ping's ID
    const pingSoundEffect = new Audio("/static/ping.mp3"); 
    let pingedBack = false;

    const dispatch = createEventDispatcher();

    async function pingButtonClick() {
        pingedBack = true;

        // Launch pointless confetti
        confetti({
            disableForReducedMotion: true,
            particleCount: 1000,
            spread: 180,
            origin: {
                x: 0.5,
                y: 1
            }
        });

        // Play sound
        pingSoundEffect.play();

        // Send the reply
        try {
            await replyToPing(replyTo);
        } catch(error) {
            alert(error);
            return;
        }
    }
</script>

<style>
    .ping-button {
        margin-top: 15px;
    }

    .footer {
        position: fixed;
        bottom: 0;
    }
</style>

<h1>You got pinged!</h1>

<div class="ping-button">
    {#if !pingedBack}
        <Button on:click={pingButtonClick} color="primary" size="lg">PING BACK</Button>
    {:else}
        You have replied to this ping. <a href="#" on:click={function() {dispatch("returnToRandomPingPage")}}>Ping someone else</a>.
    {/if}
</div>

<div class="footer">
    <AccountDeletionLink/>
</div>