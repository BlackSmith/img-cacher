<script>
import {Modal} from "bootstrap";
import {useImagesStore} from "@/stores/images";

export default {
  expose: ['open', 'close', 'stopLoading', 'startLoading'],
  setup() {
    const imagesStore = useImagesStore()
    return {imagesStore}
  },
  props: {
    title: {
      type: String,
      default: ''
    },
    startWithLoading: {
      type: Boolean,
      default: false
    },
    minWidth: {
      type: String,
      default: '40%'
    }
  },
  data() {
    return {
      loading: this.startWithLoading,
      box: null
    }
  },
  mounted() {
    this.box = new Modal(this.$refs.modalBox);
  },
  unmounted() {
    this.close()
  },
  methods: {
    startLoading() {
      this.loading = true
    },
    stopLoading() {
      this.loading = false
    },
    close() {
      this.box.hide();
    },
    open() {
      this.loading = this.startWithLoading;
      this.box.show();
    },
  }
}
</script>

<template>
  <div class="modal fade" tabindex="-1" ref="modalBox" :aria-hidden="false">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <slot name="title"><h5 class="modal-title" v-if="title">{{ title }}</h5></slot>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"
                  @click="closePanel"></button>
        </div>
        <div class="modal-body">
          <div v-if="loading" class="text-center">
            <div class="spinner-border" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
          </div>
          <div v-else-if="!loading" class="content">
            <slot name="default"></slot>
          </div>
        </div>
        <div class="modal-footer">
          <slot name="footer"></slot>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-dialog {
  min-width: v-bind(minWidth);
}
.content {
  height: auto;
}
</style>
