<script lang="ts">
    import { deleteAccount } from "../utils";

    import { Button, Modal, ModalBody, ModalFooter } from '@sveltestrap/sveltestrap';

    let isModalOpen = false;
</script>

<style>
    button {
        border: 0;
        background-color: transparent;
        text-decoration: underline;
    }
</style>

<Modal bind:isOpen={isModalOpen} header="Account deletion" toggle={function() {isModalOpen = !isModalOpen}}>
    <ModalBody>
        Are you sure you want to unsubscribe from the notifications and delete all your data?
    </ModalBody>
    <ModalFooter>
        <Button color="secondary" on:click={function() {isModalOpen = false}}>Cancel</Button>
        <Button color="danger" on:click={deleteAccount}>Confirm</Button>
    </ModalFooter>
</Modal>

<button on:click={function() {isModalOpen = true}}>Delete account</button>