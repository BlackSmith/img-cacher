<script>
import MyModalPanel from "@/components/MyModalPanel.vue";

export default {
  components: {MyModalPanel},
  emits: ['ok', 'open', 'close'],
  props: {
    title: {
      default: 'Confirmation'
    }
  },
  async mounted() {

  },
  methods: {
    open() {
      this.$refs.confirmationRef.open()
      this.$emit('open')
    },
    close() {
      this.$refs.confirmationRef.close()
      this.$emit('close')
    },
    ok() {
      this.$emit('ok')
      this.close()
    }
  }
}
</script>

<template>
  <my-modal-panel :title="$props.title" ref="confirmationRef" min-width="20%">
    <template #default>
      <slot name="default"></slot>
    </template>
    <template #footer>
      <button type="button" class="btn btn-primary" data-bs-dismiss="modal" @click="ok">OK</button>
      <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" @click="close">Cancel</button>
    </template>
  </my-modal-panel>
</template>

<style scoped>
</style>
