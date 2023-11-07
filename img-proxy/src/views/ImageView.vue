<script lang="ts">
import 'bootstrap-icons/font/bootstrap-icons.css';
import {defineComponent, watch} from "vue";
import {useImagesStore} from '@/stores/images'
import {useLoginStore} from '@/stores/login'
import {useWebSocketStore} from '@/stores/socket'
import ImageDetailPanel from "@/components/ImageDetailPanel.vue";
import AlternatesPanel from "@/components/AlternatesPanel.vue";
import UploadPopUp from "@/components/popup/UploadPopUp.vue";
import axios from "axios";
import ChangeCollectionPopup from "@/components/popup/ChangeCollectionPopup.vue";
import ConfirmationPopUp from "@/components/popup/ConfirmationPopUp.vue";

export default defineComponent({
  components: {ConfirmationPopUp, ChangeCollectionPopup, UploadPopUp, AlternatesPanel, ImageDetailPanel},
  emits: [],
  setup() {
    const imagesStore = useImagesStore()
    const loginStore = useLoginStore()
    const socket = useWebSocketStore()
    return {socket, imagesStore, loginStore}
  },
  props: {
    uuid: {
      type: String
    }
  },
  data() {
    return {
      isPanelOpen: true,
      showAlternate: true,
      showDetailMenu: false
    };
  },
  computed: {
    image() {
      for (const ix in this.imagesStore.imageAlternates) {
        if (this.imagesStore.imageAlternates[ix].uuid == this.uuid) {
          return this.imagesStore.imageAlternates[ix]
        }
      }
      return null
    },
    aleternateCount() {
      return this.imagesStore.imageDetailCount
    },
    is_user_login() {
      return this.loginStore.userProfile !== null;
    },
    imagePanelWidth() {
      return this.$refs.imageDetail ? `${this.$refs.imageDetail.panelWidth}px` : ''
    }
  },
  mounted() {
    window.addEventListener('keydown', this.handleKeyDown)
    this.imagesStore.loadAlternates(this.uuid.replace(/:.*$/, ''))
    watch(
        () => this.image,
        (newValue) => {
          if (newValue) {
            document.title = this?.image.title + ' (' + this?.image.width + 'x' + this?.image.height + ') - ' + this.appName
          } else {
            this.deletedAlternationHandler()
          }
        }
    );
  },
  unmounted() {
    window.removeEventListener('keydown', this.handleKeyDown)
  },
  methods: {
    handlerImageLoad() {
      let img = this.$refs.imageRef
      if (img?.height < img?.naturalHeight || img?.width < img?.naturalWidth) {
        img.classList.add('zoom', 'zoom-in')
      }
    },
    handlerClick() {
      let img = this.$refs.imageRef
      if (img.classList.contains('zoom')) {
        if (img.classList.contains('zoom-in')) {
          img.classList.replace('zoom-in','zoom-out')
          this.$refs.imageDetail.close()
          this.showAlternate = false
        } else {
          this.$refs.imageDetail.open()
          img.classList.replace('zoom-out', 'zoom-in')
          this.showAlternate = true
        }
      }
    },
    linkToParent() {
      return this.image.collection == '@' ? '/' : this.image.collection
    },
    openImage(uuid) {
      this.showDetailMenu = false
      this.$router.push({name: 'image', params: {uuid: uuid}});
    },
    async deleteImage() {
      if (await this.imagesStore.delete(this.image.uuid)) {
        this.showMenu = false
      }
    },
    deletedAlternationHandler() {
      let collection = '@'
      const alen = this.aleternateCount
      if (alen > 0) {
        if (this.imagesStore.imageAlternates[alen - 1]) {
          collection = this.imagesStore.imageAlternates[alen - 1].collection;
        }
        if (this.imagesStore.imageAlternates[0].uuid != this.uuid) {
          this.$router.push({name: 'image', params: {uuid: this.imagesStore.imageAlternates[0].uuid}});
          return
        } else if (alen > 1) {
          this.$router.push({name: 'image', params: {uuid: this.imagesStore.imageAlternates[1].uuid}});
          return
        }
      }
      this.$router.push({name: 'images', params: {collection: collection}});
    },
    async setAsMainImage() {
      if (this.image.uuid.indexOf(':') === -1) {
        return
      }
      let resp = await this.socket.sendRequest({
        cmd: 'set_main_image',
        params: {
          uuid: this.image.uuid,
        }
      })
      if (resp.status !== 'ok') {
        console.error(resp.msg)
        return
      }
      this.showDetailMenu = false
    },
    async addLinkHandler(url) {
      let resp = await this.socket.sendRequest({
        cmd: 'add_image_link',
        params: {
          uuid: this.image.uuid,
          url: url
        }
      })
      if (resp.status !== 'ok') {
        console.error(resp.msg)
        return
      }
      this.showDetailMenu = false
    },
    async handleKeyDown(event) {
      if (event.ctrlKey && event.key === 'v') {
        let url = ''
        if (navigator.clipboard) {
          try {
            url = await navigator.clipboard.readText();
          } catch {
            const permissionName = "clipboard-read" as PermissionName;
            const result = await navigator.permissions.query({name: permissionName});
            if (result.state === 'granted' || result.state === 'prompt') {
              url = await navigator.clipboard.readText();
            }
          }
          if (!url.startsWith('http')) {
            url = ''
          }
        }
        this.$refs.UploadImagePopup.open(url)
      }
    },
    async uploadImageHandler(url) {
      await axios.get(location.href + '?webui=1&url=' + url)
      this.$refs.UploadImagePopup.close()
    },
    async changeCollection(collection) {
      if (this.imagesStore.move([this.image.uuid], collection)) {
        this.multiSelect = []
      }
    },
    updateImageAttrs(attr, value) {
      if (attr === 'title') {
        this.image.title = value
      }
    }
  }
})
</script>

<template>
  <div class="content">
    <nav class="menu" v-if="image" style="--bs-breadcrumb-divider: '>';" aria-label="breadcrumb">
      <ol class="breadcrumb">
        <li class="breadcrumb-item" v-if="image.collection !== '@'">
          <RouterLink to="collections">Collections</RouterLink>
        </li>
        <li class="breadcrumb-item">
          <RouterLink class="collection" v-if="image.collection === '@'" :to="{name: 'index'}">Home</RouterLink>
          <RouterLink class="collection" v-else
                      :to="{name: 'images', params: {collection: image.collection}}">
            {{ image.collection }}
          </RouterLink>
        </li>
        <li class="breadcrumb-item active" aria-current="page">{{ image.title }}</li>
      </ol>
    </nav>
    <div v-if="image" class="detail">
      <div class="imageView">
        <img class="preview"
             ref="imageRef"
             v-if="image.content_type.startsWith('image')"
             :src="backendUrl + '/' + image.filename"
             @load="handlerImageLoad"
             v-on:click="handlerClick"
        >
        <video class="preview"
               ref="imageRef"
               v-else-if="image.content_type.startsWith('video')"
               :src="backendUrl + '/' + image.filename" controls loop
               @load="handlerImageLoad"
               v-on:click="handlerClick"
        ></video>
        
      </div>
      <ImageDetailPanel
          :start-open="isPanelOpen"
          width="20%"
          ref="imageDetail"
          :selected-image="image"
          background-color="rgba(51, 51, 51, 0.8)"
          @update-image="updateImageAttrs"
          :is-detail-view="true">
        <template #header>
          <div class="menuBox" v-if="is_user_login">
            <a v-if="is_user_login"
               @click="showDetailMenu=!showDetailMenu"
               class="bi bi-list icon menuButton"></a>

            <!-- Vertikální menu -->
            <div v-if="showDetailMenu" class="menu">
              <a v-if="image.uuid.indexOf(':') !== -1" class="nav-link" href="#"
                 @click="setAsMainImage"><span class="bi bi-check2-circle"></span>Set this image as the main</a>
              <a class="nav-link" href="#"
                 @click="$refs.UploadImagePopup.open('')"><span class="bi bi-upload"></span>Upload an alternation</a>
              <a class="nav-link" href="#"
                 @click="$refs.AddLinkPopup.open('')"><span class="bi bi-link"></span>Add link to this image</a>
              <a href="#" class="nav-link" @click="$refs.collectionPopup.open([imagesStore.imageAlternates])"><span class="bi bi-save2"></span>Change collection</a>
              <a href="#" class="nav-link red" @click="deleteImage"><span class="bi bi-trash"></span>Delete this image</a>
            </div>
          </div>
        </template>
      </ImageDetailPanel>
      <AlternatesPanel :images="imagesStore.imageAlternates"
                  :selected="image"
                  @select="openImage"
                  :is-open="true"
                  minus-width="20%"
                  :headTitle="'Alternates (' + aleternateCount + '):'"
                  v-if="aleternateCount > 1 && showAlternate">
      </AlternatesPanel>
    </div>
    <div v-else>
      <h1 class="headTitle">
        <RouterLink to="/"> &lt;</RouterLink> This image is not found.</h1>
    </div>
  </div>
  <UploadPopUp ref="UploadImagePopup" @ok="uploadImageHandler"></UploadPopUp>
  <UploadPopUp ref="AddLinkPopup" @ok="addLinkHandler" title="Add new link to this picture"
               :validation="false"></UploadPopUp>
  <ChangeCollectionPopup @change-collection="changeCollection" ref="collectionPopup"></ChangeCollectionPopup>
  <ConfirmationPopUp ref="deleteConfirmation" @ok="deleteImages([image])" title="Delete Confirmation">
    Are you sure, that you want to delete this image?
  </ConfirmationPopUp>
</template>

<style scoped>

  .content {
    margin: 0;
    padding: 0 0 0 20px;
    height: 100vh;
    width: 100%;
    overflow-y: hidden;
    position: relative;
  }

  .detail {
    /*padding: 20px 20px 0 ;*/
    height: 100vh;
    width: fit-content;
    margin: auto;
    overflow-y: auto;
    overflow-x: auto;
  }

  .menu {
    padding: 8px 20px 0 0;
    margin-bottom: 8px;
  }

  .menu ol {
    margin: 0;
  }


  .panel .header h2 {
    line-height: 1em;
    margin-left: 30px;
    text-align: center;
  }

  .headTitle {
    padding-bottom: 15px;
    text-align: left;
    height: 64px;
  }

  .headTitle a {
    text-decoration: none;
    color: #2a6496;
    margin-right: 15px;
    font-weight: 700;
    font-size: 36px;
  }

  .headTitle a:hover {
    color: #499fe8;
  }

  .detail .preview {
    max-width: 100%;
    max-height: calc(100vh - 110px);
    margin: auto;
  }

  .detail .zoom-in {
    cursor: zoom-in;
  }

  .detail .zoom-out {
    cursor: zoom-out;
    max-width: none;
    max-height: none;
  }
  .detail .imageView {
    width: calc(80% - 55px);
    height: calc(100vh - 108px);
    text-align: center;
    position: relative;
  }

  .collection {
    text-transform: capitalize;
  }

  /* Detail menu */
  .menuBox {
    position: relative;
    width: 100%;
  }

  .menuBox .menuButton {
    float: right;
    width: 2rem;
    height: 2rem;
    margin: 4px;
    cursor: pointer;
  }

  .menuBox .icon {
    width: 2rem;
    height: 2rem;
    margin: 4px;
    cursor: pointer;
  }

  .menuBox .menu {
    position: absolute;
    top: 32px;
    right: 15px;
    background-color: rgba(55, 55, 55, 0.9);;
    box-shadow: 0 2px 5px rgba(250, 250, 250, 0.3);
    padding: 10px;
    display: flex;
    flex-direction: column;
  }

  .menuBox .nav-link {
    display: block;
    padding: 8px;
    text-decoration: none;
    white-space: nowrap;
    color: #ccc;
    min-width: 200px;
    font-weight: 700;
  }

  .menuBox .nav-link span {
    padding-right: 10px;
  }

  .red {
    color: #e80d10;
  }

  .red:hover {
    color: #ff0003;
  }

</style>
