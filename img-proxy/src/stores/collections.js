import {defineStore} from 'pinia'
import {useWebSocketStore} from "@/stores/socket";

export const useCollectionStore = defineStore('collection', {
  state: () => ({
    collections: [],
  }),
  actions: {
    clear() {
      this.collections = []
    },
    async loadCollectionList() {
      if (this.collections.length === 0) {
        const socket = useWebSocketStore()
        const res = await socket.sendRequest({cmd: 'get_collection_list'})
        this.collections = res.data
      }
    },
    addTask(params) {
      const socket = useWebSocketStore()
      socket.sendObj({
        cmd: 'add_task', params: params
      })
    }
  }
})
