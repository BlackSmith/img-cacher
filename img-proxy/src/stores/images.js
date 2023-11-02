import {defineStore} from 'pinia'
import {useWebSocketStore} from "@/stores/socket";

export const useImagesStore = defineStore('image', {
  state: () => ({
    collection: null,
    images: [],
    loading: false,
    imageAlternates: [],
    alternatesForUUID: null,
    shownItems: 30,
    scrollTop: 0
  }),
  getters: {
    imageDetailCount: (state)  => state.imageAlternates.length,  // Object.keys(
    imageSlice: (state) => state.images.slice(0, state.shownItems)
  },
  actions: {
    async loadAlternates(uuid) {
      if (!uuid) {
        console.error('The loadImageDetail function requires uuid parameter')
      }
      this.alternatesForUUID = uuid
      const socket = useWebSocketStore()
      const res = await socket.sendRequest({cmd: 'get_image_alternates', params: {uuid: uuid}})
      this.imageAlternates = res.data
    },
    clear() {
      this.images = []
      this.shownItems = 30
      this.scrollTop = 0
    },
    // append(newImages) {
    //   for (const img of newImages){
    //     if (img.collection === this.collection) {
    //       this.images.push(img)
    //     }
    //   }
    // },
    updateList(data) {
      const tcol = this.collection || '@'
      if (data.collection === tcol) {
        for (const ix in this.images) {
          if (this.images[ix].uuid === data.uuid) {
            this.images[ix] = data
            return
          }
        }
        if (data.uuid.indexOf(':') === -1) {
          this.images.unshift(data)
        }
      } else {
        this.images = this.images.filter(img => img.uuid !== data.uuid);
      }
    },
    updateImageAlternates(data) {
      if (this.imageAlternates.length > 0) {
        for (const ix in this.imageAlternates) {
          if (this.imageAlternates[ix].uuid === data.uuid) {
            this.imageAlternates[ix] = data
            return
          }
        }
        if (data.uuid.indexOf(':') !== -1 && this.imageAlternates[0].collection === data.collection) {
          this.imageAlternates.push(data)
        }
      }
    },
    update(data) {
      const uuids = data.uuid.split(':')
      if (uuids[0] === this.alternatesForUUID) {
        this.updateImageAlternates(data)
      }
      if (uuids.length === 1) {
        this.updateList(data)
      }
    },
    async delete(uuid) {
      const socket = useWebSocketStore()
      let resp = await socket.sendRequest({
        cmd: 'delete_image',
        params: {uuid: uuid}
      })
      if (resp.status !== 'ok') {
        console.error(resp.msg)
        return false
      }
      return true
    },
    delete_handler(data) {
      this.images = this.images.filter(img => img.uuid !== data.uuid);
      this.imageAlternates = this.imageAlternates.filter(img => img.uuid !== data.uuid);
    },
    async move(uuids, collection) {
      const socket = useWebSocketStore()
      let resp = await socket.sendRequest({
        cmd: 'set_image_collection',
        params: {
          uuid: uuids,
          collection: collection
        }
      })
      if (resp.status !== 'ok') {
        console.error(resp.msg)
        return false
      }
      return true
    },
    move_handler(data) {
      // {"from": "31992ed6ebe294559338e562cb24de7b", "to": "b59894041e5767199c6189c7f207ec27:31992ed6ebe294559338e562cb24de7b"}
      let aix = null;
      const n_uuids = data.to.split(':')
      if (this.imageAlternates.length > 0) {
        if (this.alternatesForUUID === n_uuids[0]) {
          for (const ix in this.imageAlternates) {
            if (this.imageAlternates[ix].uuid === data.from) {
              this.imageAlternates[ix].uuid = data.to
              if (data.to.indexOf(':') === -1) {
                aix = ix;
              }
              break
            }
          }
          if (aix) {
            // We set alternate image as main image
            for (const ix in this.images) {
              if (this.images[ix].uuid === data.to) {
                this.images[ix] = this.imageAlternates[aix]
                return
              }
            }
          }
        }
      }
      if (this.images && n_uuids.length > 1) {
        // We set image as alternate
        this.images = this.images.filter(img => img.uuid !== data.from);
        for (const ix in this.images) {
          if(this.images[ix].uuid === n_uuids[0]) {
            this.images[ix].alternates_count += 1
          }
        }
      }

    },
    async joinImages(uuids) {
      const socket = useWebSocketStore()
      let resp = await socket.sendRequest({
        cmd: 'join_images',
        params: {
          uuids: uuids,
        }
      })
      if (resp.status !== 'ok') {
        console.error(resp.msg)
        return false
      }
      return true
    },
    async loadCollectionImages(name=null) {
      this.loading = true
      if (name && this.collection !== name) {
        this.clear()
        this.collection = name
        const socket = useWebSocketStore()
        const res = await socket.sendRequest({
          cmd: 'get_collection_images', collection: this.collection, offset: 0, num: -1
        })
        this.images = [...this.images, ...res.members]
      }
      this.shownItems += 30
      this.loading = false
    },
    addTask(params) {
      const socket = useWebSocketStore()
      socket.sendObj({
        cmd: 'add_task', params: params
      })
    }
  }
})
