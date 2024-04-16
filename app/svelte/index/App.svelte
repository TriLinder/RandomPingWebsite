<script lang="ts">
	let count: number = 0;

	function click() {
		count += 1;
	}
</script>

<button on:click={click}>Count {count}</button>