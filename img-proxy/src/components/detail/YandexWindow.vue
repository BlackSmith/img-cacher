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
      sites: null,
      similar: null,
      external_link: null,
      showSameImages: true,
      errorMessage: null
    }
  },
  methods: {
    async open(image) {
      this.sites = null;
      this.external_link = null;
      this.similar = null
      this.$refs.modalRef.open();
      let data = await this.socket.sendRequest({cmd: 'get_yandex_links', uuid: image.uuid})
      if (data.status === 'ok') {
        this.external_link = data.response.response_url;
        const sites = data.response?.sites.sites
        sites.sort((a,b) => (b.originalImage.width + b.originalImage.height) - (a.originalImage.width + a.originalImage.height))
        this.sites = sites.slice(0, 20)
        this.similar = data.response.similar.thumbs;
        this.$refs.modalRef.stopLoading();
      } else {
        this.errorMessage = data.response?.error;
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
  <MyModalPanel :startWithLoading="true" ref="modalRef">
    <template #title>
      <h5>Yandex refs
        <a v-if="external_link"
           :href="external_link"
           class="bi bi-box-arrow-up-right externalLink"
           target="_blank" title="Link to Yandex"></a></h5>
    </template>
    <template #footer>
      <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" @click="$refs.modalRef.close">Close</button>
    </template>
    <template #default>
      <div v-if="sites?.length > 0">
        <ul class="nav nav-tabs menu">
          <li class="nav-item">
            <a :class="{'nav-link': true, 'active': showSameImages}" aria-current="page" href="#" @click="showSameImages=true" >The same images</a>
          </li>
          <li class="nav-item">
            <a :class="{'nav-link': true, 'active': !showSameImages}" aria-current="page" href="#"
               @click="showSameImages=false">A similar images</a>
          </li>
        </ul>
        <table class="tiny-list" ref="sameTable" v-if="showSameImages">
        <thead>
        <tr>
          <th>&nbsp;</th>
          <th>Resolution</th>
          <th>Sources</th>
        </tr>
        </thead>
        <tbody>
        <tr v-for="it in sites" :key="it?.key">
          <td class="image"><a :href="it.originalImage.url" target="_blank"><img :src="it.thumb.url" alt=""/></a></td>
          <td class="resolution">{{ it.originalImage.width }}&nbsp;x&nbsp;{{ it.originalImage.height }}</td>
          <td class="sources">
            <a :href="it.url" target="_blank">{{ it.title }}</a>
            <p>{{it.description}}</p>
          </td>
          <td class="icons">
            <a :href="getUrl(it.originalImage.url)" target="_blank"
               :class="{'bi': true, 'bi-cloud-download': true, 'disabled': isLinkDisabled(it.originalImage.url)}"
               @click.stop="downloadAlternate($event)"></a>
          </td>
        </tr>
        </tbody>
      </table>
      <div class="grid" v-else-if="similar?.length > 0 && !showSameImages">
        <a class="grid-item"
           v-for="ir in similar"
           :key="ir.linkUrl"
           :href="ir.linkUrl"
           target="_blank"
           :title="ir.title"><img :src="ir.imageUrl" alt="" width="200"></a>
      </div>
    </div>
    <div v-else class="text-center">
      <p v-if="errorMessage">{{ errorMessage }}</p>
      <p v-else>The image does not have alternatives.</p>
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
.externalLink {
  font-size: 0.8em;
  margin-left: 10px;
}

.menu {
  position: relative;
  top: -7px;
}

.grid-item {
  height: 230px;
  float: left;
  position: relative;
  display: grid;
  place-items: center;
}
.grid-item img {
  vertical-align: top;
  margin: 8px;
}

</style>
