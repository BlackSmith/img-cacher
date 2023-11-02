<script>
import axios from 'axios';
import {useImagesStore} from "@/stores/images";
import MyModalPanel from "@/components/MyModalPanel.vue";


export default {
  components: {MyModalPanel},
  setup() {
    const imagesStore = useImagesStore()
    return {imagesStore}
  },
  data() {
    return {
      rows: null,
    }
  },
  methods: {
    async open(image) {
      console.info(this.$refs.modalRef)
      this.$refs.modalRef.open();
      let data = await this.socket.sendRequest({cmd: 'get_tineye_links', uuid: image.uuid})
      if (data.status === 'ok') {
        data.lines.sort((a,b) => (b.width + b.height) - (a.width + a.height))
        this.rows = data.lines
        this.$refs.modalRef.stopLoading();
      }
    },
    getSize(bytes) {
      let units = ['B', 'KB', 'MB', 'GB']
      let ix = 0
      while (bytes >= 1024) {
        bytes = bytes / 1024
        ix = ix + 1
      }
      return (Math.round(bytes * 100) / 100) + ' ' + units[ix]
    },
    getUrl(url) {
      return location.href.replace(/:[0-9a-f]+$/, '').replace(/\?.*$/, '') + '?url=' + url;
    },
    async downloadAlternate(event) {
      event.preventDefault();
      let el = event.target;
      if (el.classList.contains('disabled')) {
        return
      }
      el.classList.add('disabled')
      let url = el.href;
      axios.get(url)
    },
    isLinkDisabled(url) {
      for (const it in this.imagesStore.imageAlternates) {
        if (url === this.imagesStore.imageAlternates[it].url) {
          return true
        }
      }
      return false
    },
  }
}
</script>

<template>
  <MyModalPanel title="Tineye refs" :startWithLoading="true" ref="modalRef">
    <template #footer>
      <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" @click="$refs.modalRef.close">Close</button>
    </template>
    <template #default>
    <table v-if="rows?.length > 0" class="tiny-list">
      <thead>
      <tr>
        <th>&nbsp;</th>
        <th>Resolution</th>
        <th>Size</th>
        <th>Sources</th>
      </tr>
      </thead>
      <tbody>
      <tr v-for="it in rows" :key="it.key">
        <td class="image"><a :href="it.backlinks[0].url" target="_blank"><img :src="it.image_url" alt=""/></a></td>
        <td class="resolution">{{ it.width }}&nbsp;x&nbsp;{{ it.height }}</td>
        <td class="size">{{ getSize(it.size) }}</td>
        <td class="sources">
          <ul>
            <li v-for="link in it.backlinks.slice(0, 5)" :key="link.backlink">
              <a :href="link.backlink" target="_blank">{{ link.backlink }}</a>
            </li>
          </ul>
        </td>
        <td class="icons">
          <a :href="getUrl(it.backlinks[0].url)" target="_blank"
             :class="{'bi': true, 'bi-cloud-download': true, 'disabled': isLinkDisabled(it.backlinks[0].url)}"
             @click.stop="downloadAlternate($event)"></a>
        </td>
      </tr>
      </tbody>
    </table>
    <div v-else class="text-center">
      <p>The image does not have alternatives.</p>
    </div>
    </template>
  </MyModalPanel>
</template>

<style scoped>

.tiny-list table {
  width: 100%;
}
.tiny-list tbody tr:nth-child(odd) {
  background-color: #333;
}

.tiny-list tbody td {
  vertical-align: top;
  padding: 12px;
}

.tiny-list .image {
  padding: 5px 5px;
}

.tiny-list .resolution {
  width: 15%;
}

.tiny-list .size {
  width: 15%;
}

.tiny-list .sources {
  max-width: 50%;
}
.tiny-list .icons a {
  font-size: 150%;
  cursor: pointer;
}
.tiny-list .icons .disabled {
  color: #555;
  cursor: default;
}
</style>
