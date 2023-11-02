<script>
import MyModalPanel from "@/components/MyModalPanel.vue";
import {useCollectionStore} from "@/stores/collections";

export default {
  components: {MyModalPanel},
  emits: ['changeCollection', 'open', 'close'],
  setup() {
    const collectionStore = useCollectionStore()
    return {collectionStore}
  },
  data() {
    return {
      items: []
    }
  },
  computed: {
    collections() {
      return this.collectionStore.collections
    }
  },
  async mounted() {
    await this.collectionStore.loadCollectionList()
  },
  methods: {
    open(items) {
      this.items = items
      this.$refs.changeCollectionRef.open()
      this.$emit('open')
    },
    close() {
      this.items = []
      this.$refs.changeCollectionRef.close()
      this.$emit('close')
    }
  }
}
</script>

<template>
  <my-modal-panel title="Change collection" ref="changeCollectionRef" min-width="20%">
    <template #default>
      <div class="select-collection-wrapper">
        <div class="input-group mb-3 select-collection">
          <input type="text" class="form-control" aria-label="Collection" ref="collectionRef"
                 @keyup.enter="$emit('changeCollection', $refs.collectionRef.value || '@', items)"
                 @keyup.esc="close">
          <button class="btn btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown"
                  aria-expanded="false">Collections
          </button>
          <ul class="dropdown-menu dropdown-menu-end">
            <li v-for="it in collections" :key="it.name">
              <a class="dropdown-item" href="#" @click="$refs.collectionRef.value=it.name">{{ it.name }}</a>
            </li>
          </ul>
        </div>
      </div>
    </template>
    <template #footer>
      <button type="button" class="btn btn-primary" data-bs-dismiss="modal"
              @click="$emit('changeCollection', $refs.collectionRef.value || '@', items)">Move</button>
      <button type="button" class="btn btn-secondary" data-bs-dismiss="modal"
              @click="close">Close</button>
    </template>
  </my-modal-panel>
</template>

<style scoped>
.select-collection {
  position: absolute;
  z-index: 1000;
  width: calc(100% - 65px);
}

.select-collection-wrapper {
  height: 60px;
}
</style>
