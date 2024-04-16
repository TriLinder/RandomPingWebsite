<script lang="ts">
    import confetti from 'canvas-confetti';
    import { onMount } from 'svelte';
    import { persistentDataStore } from '../../stores';
    import { sendRandomPing } from '../../utils';

    import { Button } from '@sveltestrap/sveltestrap';
    
    let nextAllowedPingTimestamp = new Date(0);
    let currentTime = new Date();
    $: timeUntilNextAllowedPing = nextAllowedPingTimestamp.getTime() - currentTime.getTime();

    let pingSoundEffect = new Audio("/static/ping.mp3"); 

    async function pingButtonClick() {
        // Update ping cooldown now, for visual effect
        nextAllowedPingTimestamp = new Date(new Date().getTime() + $persistentDataStore.serverInformation.pingCooldown * 1000);
        
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

        // Send ping
        try {
            await sendRandomPing();
            $persistentDataStore.stats.sentPingsCount += 1;

            // Update ping cooldown again for actual cooldown functionality
            nextAllowedPingTimestamp = new Date(new Date().getTime() + $persistentDataStore.serverInformation.pingCooldown * 1000);
        } catch(error) {
            alert(error);
            return;
        }
    }

    function updateCurrentTime() {
        currentTime = new Date();
    }

    onMount(function() {
        setInterval(updateCurrentTime, 500);
    });
</script>

<h1>Welcome back!</h1>

<!-- Ensure correct plural form -->
{#if $persistentDataStore.stats.sentPingsCount != 1}
    <p>You've sent {$persistentDataStore.stats.sentPingsCount} pings.</p>
{:else}
    <p>You've sent {$persistentDataStore.stats.sentPingsCount} ping.</p>
{/if}

<!-- The main ping button -->
<Button on:click={pingButtonClick} disabled={timeUntilNextAllowedPing >= 0} color="primary" size="lg">
    {#if timeUntilNextAllowedPing >= 0}
        {Math.ceil(timeUntilNextAllowedPing / 1000)}s
    {:else}
        SEND PING
    {/if}
</Button>