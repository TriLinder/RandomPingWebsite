<script lang="ts">
	import { onMount } from "svelte";
	import { persistentDataStore } from "../stores";
	import { fetchServerInformation, getPushServiceSubscriptionObject, updatePushServiceSubscriptionObject } from "../utils";

	import Register from "./pages/Register.svelte";
	import SendRandomPing from "./pages/SendRandomPing.svelte";
    import ReplyToPing from "./pages/ReplyToPing.svelte";
	
	let currentPage: "loading" | "register" | "sendRandomPing" | "replyToPing" = "loading";

	onMount(async function() {
		// Mount the service worker
		navigator.serviceWorker.register("./sw.js");

		// Check if already registered
		if ($persistentDataStore.userInformation) {
			// Update information
			try {
				await fetchServerInformation();
				await updatePushServiceSubscriptionObject(await getPushServiceSubscriptionObject());
			} catch(error) {
				alert(error);
				return;
			}

			if (window.location.hash.length > 1) {
				currentPage = "replyToPing";
			} else {
				currentPage = "sendRandomPing";
			}
		} else {
			currentPage = "register";
		}
	});
</script>

<style>
	.center {
		display: flex;
		justify-content: center;
	}

	.content {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;

		max-width: 800px;
		width: 100%;
		height: 100vh;
	}
</style>

<svelte:head>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
</svelte:head>

<div class="center">
	<div class="content">
		{#if currentPage == "loading"}
			Loading..
		{:else if currentPage == "register"}
			<Register on:registered={function() {currentPage = "sendRandomPing"}}/>
		{:else if currentPage == "sendRandomPing"}
			<SendRandomPing/>
		{:else if currentPage == "replyToPing"}
			<ReplyToPing on:returnToRandomPingPage={function() {currentPage = "sendRandomPing"}}/>
		{/if}
	</div>
</div>