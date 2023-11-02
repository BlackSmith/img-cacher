<script lang="ts">

import {defineComponent, watch} from "vue";
import {useImagesStore} from '@/stores/images'
import {useLoginStore} from '@/stores/login'
import {RouterLink} from "vue-router";
import ImageDetailPanel from "@/components/ImageDetailPanel.vue";
import AlternatesPanel from "@/components/AlternatesPanel.vue";
import ChangeCollectionPopup from "@/components/popup/ChangeCollectionPopup.vue";
import ConfirmationPopUp from "@/components/popup/ConfirmationPopUp.vue";
import UploadPopUp from "@/components/popup/UploadPopUp.vue";
import axios from "axios";


export default defineComponent({
  components: {UploadPopUp, ConfirmationPopUp, ChangeCollectionPopup, AlternatesPanel, ImageDetailPanel, RouterLink},
  emits: [],
  setup() {
    const imagesStore = useImagesStore()
    const loginStore = useLoginStore()
    return {imagesStore, loginStore}
  },
  props: {
    collection: undefined
  },
  async mounted() {
    window.addEventListener('keydown', this.handleKeyDown)
    await this.imagesStore.loadCollectionImages(this.collection)
    document.title = this.collection + ' ' + this.appName
    this.scrolledView = this.$refs.scrollContainer.clientHeight
    if (this.imagesStore.scrollTop) {
      let counter = 100
      while (counter > 0 && this.$refs.scrollContainer.scrollHeight < this.imagesStore.scrollTop) {
        counter -= 1
        await this.imagesStore.loadCollectionImages()
      }
      this.$refs.scrollContainer.scrollTop = this.imagesStore.scrollTop
    }
    watch(
        () => this.collection,
        (newValue) => {
          document.title = this.collection + ' ' + this.appName
          this.multiSelect = []
          this.imagesStore.loadCollectionImages(newValue)
        }
    );
  },
  unmounted() {
    window.removeEventListener('keydown', this.handleKeyDown)
  },
  data() {
    return {
      selectedImage: {},
      selectedGrid: null,
      multiSelect: [],
      multiselectDiffWidth: '0%',
      scrolledView: 0,
      showDetailMenu: false
    };
  },
  computed: {
    images() {
      return this.imagesStore.imageSlice
    },
    imagesCount() {
      return this.imagesStore.images.length
    },
    is_user_login() {
      return this.loginStore.userProfile !== null;
    },
    shownImagesCount() {
      const row = Math.floor(this.$refs.scrollContainer?.clientWidth / 320) || 1; /* 320px = grid-item.width + margin */
      return Math.min(
          Math.ceil(this.scrolledView / 560) * row, /* 560px = grid-item.height + margin */
          this.imagesCount
      );
    }
  },
  methods: {
    getPreview(image) {
      if (image?.thumb_file) {
        return this.backendUrl + '/' + image.thumb_file
      }
      if (image.filename === undefined) {
        return this.backendUrl + '/static/default.png'
      }
      let parts = image.filename.split('/')
      let file = parts.pop()
      parts.push('.thumb')
      parts.push(file)
      return this.backendUrl + '/' + parts.join('/') + '?t=' + image?.thumb_created
    },
    thumbErrorHandler(event) {
      let efile = this.backendUrl + '/static/default.png'
      if (event.target.src != efile) {
        event.target.src = efile
      }
    },
    // selectImage(image, event=null) {
    //
    //
    //   //this.multiselectDiffWidth =  `${this.$refs.imageDetail?.panelWidth}px`
    // },
    async handleScroll(event) {
      const container = event.target //this.$refs.scrollContainer;
      this.scrolledView = container.scrollTop + container.clientHeight
      const bottomOffset = container.scrollHeight - this.scrolledView;
      // console.log(container.scrollHeight)
      // console.log({bottom: bottomOffset, loading: this.imagesStore.loading})
      if (bottomOffset < 1000 && !this.imagesStore.loading) {
        console.log("Loading")
        await this.imagesStore.loadCollectionImages()
      }
    },
    multiselectToggle(image) {
      if (this.multiSelect.filter(img => img.uuid === image.uuid).length === 0) {
        this.multiSelect.push(image)
      } else {
        this.multiSelect = this.multiSelect.filter(img => img.uuid !== image.uuid)
      }
    },
    multiSelectRemoveItem(uuid) {
      this.multiSelect = this.multiSelect.filter(img => img.uuid !== uuid)
    },
    async deleteImages(images) {
      while(images.length > 0) {
        const uuid = images.shift().uuid
        if (this.selectedImage?.uuid == uuid) {
          this.selectedImage = null;
        }
        await this.imagesStore.delete(uuid)
      }
      this.showDetailMenu = false;
    },
    async changeCollection(collection) {
      if (this.imagesStore.move(this.multiSelect.map((img) => img.uuid), collection)) {
        this.multiSelect = []
      }
    },
    async multiselectJoin() {
      await this.imagesStore.joinImages(this.multiSelect.map((img) => img.uuid))
      this.multiSelect = []
    },
    async handleKeyDown(event) {
      if (event.ctrlKey && event.key === 'v') {
        let url = ''
        if (navigator.clipboard) {
          const result = await navigator.permissions.query({name: "clipboard-write"});
          if (result.state === 'granted' || result.state === 'prompt') {
            url = await navigator.clipboard.readText()
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
    }
  },
});
</script>


<template>
  <div class="content">
    <nav class="menu" style="--bs-breadcrumb-divider: '>';" aria-label="breadcrumb">
      <div class="counterPanel">{{ shownImagesCount  }} / {{ imagesStore.images.length }}</div>
      <div class="bi bi-upload uploadButton" @click="$refs.UploadImagePopup.open()" title="Upload image"></div>
      <ol class="breadcrumb" v-if="collection !== '@'">
        <li class="breadcrumb-item" ><RouterLink :to="{name: 'collections'}">Collections</RouterLink></li>
        <li class="breadcrumb-item active text-capitalize" aria-current="page">{{ collection }}</li>
      </ol>
    </nav>
    <div class="content2">
      <div class="viewPort" @scroll="handleScroll" ref="scrollContainer">
        <div class="grid" :key="collection">
          <div v-for="image in images"
               :class="{'grid-item':true, 'selected': image.uuid === selectedImage?.uuid}"
               :key="image.uuid"
               :id="'image_'+image.uuid"
               @click="selectedImage=selectedImage === image ? null : image">
            <div :class="{'preview': true, 'center': (image.height*290)/image.width < 300}">
              <span v-if="is_user_login"
                    :class="{'bi': true, 'bi-circle': multiSelect.indexOf(image) === -1,
                             'bi-check-circle': multiSelect.indexOf(image) !== -1,
                             'green': multiSelect.indexOf(image) !== -1,
                             'multiselect':true}"
                    @click.stop="multiselectToggle(image, $event)"></span>
              <RouterLink :to="{name: 'image', params: {uuid: image.uuid}}"
                          @click="imagesStore.scrollTop = $refs.scrollContainer.scrollTop">
                <img :src="getPreview(image)" v-on:error="thumbErrorHandler" :alt="'Preview of '+image.title" /></RouterLink>
            </div>
            <div class="desc">
              <div>
                <h6 class="title" :title="image.title">{{ image.title }}</h6>
                <span v-if="image.width">{{image.width}} x {{image.height}}</span>
              </div>
              <div class="tags">
                <div :class="['tag', image.content_type?.split('/')[0]]">{{ image.content_type?.split('/')[1] }}</div>
                <div class="tag" title="Alternates" v-if="image.alternates_count > 1">{{ image.alternates_count }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <ImageDetailPanel
          width="20%"
          ref="imageDetail"
          :selected-image="selectedImage"
          @close="showDetailMenu=false">
        <template v-slot:header>
          <div class="menuBox" >
            <span class="bi bi-x-square icon" @click="selectedImage=null"></span>
            <!-- Ikona pro otevření menu -->
            <a v-if="is_user_login" @click="showDetailMenu=!showDetailMenu" class="bi bi-list icon menuButton"></a>
            <!-- Vertikální menu -->
            <div v-if="is_user_login && showDetailMenu" class="menu">
              <a href="#" class="nav-link" @click="$refs.collectionPopup.open([selectedImage])"><span class="bi bi-save2"></span>Change collection</a>
              <a href="#" class="nav-link red" @click="deleteImages([selectedImage])"><span class="bi bi-trash"></span>Delete this image</a>
            </div>
          </div>
        </template>
      </ImageDetailPanel>
      <AlternatesPanel :images="multiSelect"
                  is-open="true"
                  @select="multiSelectRemoveItem"
                  :minusWidth="$refs.imageDetail.panelWidth+'px'"
                  :headTitle="'Select (' + multiSelect.length + '):'"
                  v-if="multiSelect.length > 0">
        <template #left>
          <div class="leftBar">
            <a role="button"
               :class="{'btn': true, 'btn-outline-success': true, 'bi': true, 'bi-menu-app': true, 'disabled': multiSelect.length < 2}"
               title="Join as alternation"
               @click="$refs.joinConfirmation.open"
            ></a>
            <a role="button" class="btn btn-outline-success bi bi-save2" title="Move to collection"
               @click="$refs.collectionPopup.open(multiSelect)"></a>
            <div class="border"></div>
            <a role="button" class="btn btn-outline-danger bi bi-trash" title="Delete pictures"
               @click="$refs.deleteConfirmation.open"></a>
          </div>
        </template>
      </AlternatesPanel>
    </div>
  </div>
  <ChangeCollectionPopup @change-collection="changeCollection" ref="collectionPopup"></ChangeCollectionPopup>
  <ConfirmationPopUp ref="deleteConfirmation" @ok="deleteImages(multiSelect)" title="Delete Confirmation">
    Are you sure, that you want to delete these {{ multiSelect.length }} images?
  </ConfirmationPopUp>
  <ConfirmationPopUp ref="joinConfirmation" @ok="multiselectJoin" title="Join images">
    Are you sure, that you want to join these {{ multiSelect.length }} images as alternations?
    The first one will be used as main.
  </ConfirmationPopUp>
  <UploadPopUp ref="UploadImagePopup" @ok="uploadImageHandler"></UploadPopUp>
</template>

<style scoped>
  .content {
    margin: 0;
    padding: 0 0 0 20px;
    width: 100%;
    overflow-y: hidden;
    position: relative;
  }
  .content2 {
    position: relative;
    width: 100%;
    height: calc(100vh - 3rem);
    overflow-x: hidden;
    overflow-y: hidden;
  }
  .viewPort {
    width: 100%;
    height: 100vh;
    text-align: center;
    position: relative;
    overflow-y: auto;
  }
  .menu {
    margin: 0.5rem 20px 0.5rem 0;
    height: 2rem;
  }
  .menu ol {
    margin: 0;
  }
  .grid {
    margin: 0;
  }
  .grid-item {
    float: left;
    color: white;
    text-align: center;
    height: 500px;
    margin: 0 15px 15px 0;
    box-shadow: 0 0 8px rgba(200, 200, 200, 0.3);
    border-radius: 10px;
    position: relative;
    display: grid;
    /*place-items: center;*/
  }

  .grid-item.selected {
    background-color: rgba(151, 151, 151, 0.2);
  }

  .preview {
    /*height: calc(100% - 60px);*/
    position: relative;
    display: grid;
  }

  .preview a {
    height: min-content;
    min-width: 290px;
  }

  .preview.center {
    place-items: center;
  }

  .preview img {
    max-height: 435px;
    max-width: 290px;
    margin: 0 1px;
    border-radius: 10px;
  }

  .multiselect {
    position: absolute;
    top: 0;
    right: 5px;
    font-weight: bolder;
    font-size: 1.3em;
    color: #777777;
    mix-blend-mode: difference;
  }


  .multiselect:hover {
    color: #999999;
  }

  .multiselect.green {
    color: #8cdc80;
    mix-blend-mode: normal;
  }

  .multiselect.green:hover {
    color: #138b00;
  }

  .grid-item .desc {
    width: 100%;
    height: 60px;
    position: absolute;
    bottom: 0;
    left: 10px;
    text-align: left;
  }

  .grid-item .desc .title {
    width: min-content;
    max-width: calc(100% - 20px);
    overflow-x: hidden;
    white-space: nowrap;
    font-weight: 700;
    position: relative;
    line-height: 1.5em;
    margin: 0;
  }

  .grid-item .desc .title span{
    font-weight: normal;
    font-size: 0.7em;
    color: rgba(136, 136, 136, 0.53);
  }

  .tags {
    position: absolute;
    right: 10px;
    bottom: 0;
    left: auto;
    width: fit-content;
  }

  .tags .tag {
    padding: 3px 8px;
    font-weight: 700;
    margin-left: 0;
    float: right;
    background-color: #103a08;
  }

  .tags .tag:first-child {
    border-top-right-radius: 3px;
    border-bottom-right-radius: 3px;
  }

  .tags .tag:last-child {
    border-top-left-radius: 3px;
    border-bottom-left-radius: 3px;
  }

  .tags .tag.image {
    background-color: #138b00;
  }

  .tags .tag.video {
    background-color: purple;
  }


  .leftBar {
    width: 2.5rem;
    height: 100%;
    margin-left: 1rem;
    float: left;
  }

  .leftBar a {
    margin: .2rem;
    font-size: .9rem;
    padding: .3rem .5rem;
  }

  .leftBar .border {
    margin: .3rem .3rem;
  }

  .counterPanel {
    float: right;
    padding-left: 8px;
  }

  .uploadButton {
    float: right;
    cursor: pointer;
  }


  h4.multiSelectTitle {
    float: left;
    font-size: .9em;
    padding: 7px 0;
    margin: 0 15px 0 0;
  }


  .menuBox {
    position: relative;
    width: 100%;
  }

  .menuBox .menuButton {
    position: absolute;
    top: 0;
    right: 0;
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
    align-items: center;
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

  .red {
    color: #e80d10;
  }

  .red:hover {
    color: #ff0003;
  }

  .nav-link span {
    padding-right: 10px;
  }


</style>
