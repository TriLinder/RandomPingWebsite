<script lang="ts">
    import { deleteAccount } from "../utils";

    import { Button, Modal, ModalBody, ModalFooter, Spinner } from '@sveltestrap/sveltestrap';

    let isModalOpen = false;
    let deleting = false;

    async function deleteButtonClick() {
        deleting = true;

        try {
            await deleteAccount();
        } catch(error) {
            alert(error);
            deleting = false;
            return;
        }
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
    
    button {
        border: 0;
        background-color: transparent;
        text-decoration: underline;
    }
</style>

<Modal bind:isOpen={isModalOpen} header="Account deletion" toggle={function() {isModalOpen = !isModalOpen}}>
    <ModalBody>
        <div class="modal-body">
            {#if !deleting}
                Are you sure you want to unsubscribe from the notifications and delete all your data?
            {:else}
                Deleting. Please wait. <br>
                <Spinner type="border" color="primary"/>
            {/if}
        </div>
    </ModalBody>
    <ModalFooter>
        <Button color="secondary" on:click={function() {isModalOpen = false}}>Cancel</Button>
        <Button color="danger" on:click={deleteButtonClick} bind:disabled={deleting}>Confirm</Button>
    </ModalFooter>
</Modal>

<button on:click={function() {isModalOpen = true}}>Delete account</button>