<script>
import MyModalPanel from "@/components/MyModalPanel.vue";

export default {
  components: {MyModalPanel},
  emits: ['ok', 'open', 'close'],
  props: {
    title: {
      default: 'Upload Image'
    },
    validation: {
      default: true
    }
  },
  data() {
    return {
      url: '',
    }
  },
  computed: {
    isEmpty() {
      return this.url.length === 0
    },
    isInvalid() {
      return this.validation && !this.url.startsWith('http')
    }
  },
  methods: {
    open(url='') {
      this.url = url
      this.$refs.uploadUrl.focus()
      this.$refs.confirmationRef.open()
      this.$emit('open')
    },
    close() {
      this.$refs.confirmationRef.close()
      this.$refs.confirmationRef.stopLoading()
      this.$emit('close')
    },
    ok() {
      if (!this.isInvalid) {
        this.$refs.confirmationRef.startLoading()
        this.$emit('ok', this.$refs.uploadUrl.value)
      } else {
        this.$refs.uploadUrl.classList.add()
      }
    }
  }
}
</script>

<template>
  <my-modal-panel :title="$props.title" ref="confirmationRef" min-width="20%">
    <template #default>
      <div class="input-group flex-nowrap has-validation">
        <span class="input-group-text bi bi-link" id="addon-wrapping"></span>
        <input v-model="url" type="text" :class="{'form-control':true, 'is-invalid': isInvalid && !isEmpty}"
               placeholder="Url" aria-label="Url" ref="uploadUrl"
               @keydown.enter="ok" @keydown.esc="close">
      </div>
    </template>
    <template #footer>
      <a role="button" :class="{'btn':true, 'btn-primary':true, 'disabled': isInvalid}" @click="ok">OK</a>
      <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" @click="close">Cancel</button>
    </template>
  </my-modal-panel>
</template>

<style scoped>
</style>
