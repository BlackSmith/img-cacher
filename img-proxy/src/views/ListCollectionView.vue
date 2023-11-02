<script lang="ts">
import {defineComponent, watch} from "vue";
import {useCollectionStore} from '@/stores/collections'
import {RouterLink} from "vue-router";


export default defineComponent({
  components: {RouterLink},
  emits: [],
  setup() {
    const collectionStore = useCollectionStore()
    return {collectionStore}
  },
  async mounted() {
    await this.collectionStore.loadCollectionList()
    document.title = this.appName
    watch(
        () => this.collections,
        (newValue, oldValue) => {
          if (newValue?.name == oldValue?.name && newValue?.thumb_created != oldValue?.thumb_created) {
            console.info('Thumb collection is reloaded.')
            this.$refs.CollectionPreview.src = this.getPreview(newValue)
          }
        }
    );
  },
  data() {
    return {
      selectedGrid: null
    };
  },
  computed: {
    collections() {
      return this.collectionStore.collections
    },
  },
  methods: {
    getPreview(collection) {
      if (collection?.thumb_file) {
        return this.backendUrl + '/' + collection.thumb_file
      }
      return this.backendUrl + '/' + collection.name + '/.thumb/' + collection.name + '.gif?t=' + collection?.thumb_created
    },
    thumbErrorHandler(event) {
      let efile = this.backendUrl + '/static/default.png'
      if (event.target.src != efile) {
        event.target.src = efile
      }
    },
    selectCollection(collection, event=null) {
      if (this.selectedGrid != null) {
        this.selectedGrid.classList.remove('selected')
      }
      let newGrid = this.selectedGrid
      if (event) {
        newGrid = event.target.closest('.grid-item')
      }
      if (newGrid == this.selectedGrid) {
        this.selectedCollection = {}
        this.selectedGrid = null
        return
      }
      this.selectedCollection = collection
      this.selectedGrid = newGrid
      this.selectedGrid.classList.add('selected')
    },

  },

});
</script>


<template>
  <div class="content">
  <nav style="--bs-breadcrumb-divider: '>';" aria-label="breadcrumb">
    <ol class="breadcrumb">
      <li class="breadcrumb-item active" aria-current="page">Collections</li>
    </ol>
  </nav>
    <div class="grid">
      <div v-for="collection in collections" class="grid-item" :key="collection.name" v-on:click="selectCollection(collection, $event)">
        <RouterLink :to="{name: 'images', params: {collection: collection.name}}">
          <img :src="getPreview(collection)" v-on:error="thumbErrorHandler" :alt="'Preview of '+collection.name" /></RouterLink>
        <div class="tags">
          <div class="title">{{ collection.name }}</div>
          <div :class="['tag', 'numbers']" title="images in collection">{{ collection.num_member }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>

  .content {
      padding: 20px;
      margin: 0;
      height: 100vh;
      width: 100%;
      overflow-y: auto;
  }

  .grid {
    padding: 20px;
    margin: 0;
    height: 100vh;
    overflow-y: auto;
  }

  .grid-item {
    float: left;
    color: white;
    text-align: center;
    min-width: 313px;
    height: 500px;
    padding: 13px 13px 13px 10px;
    margin: 10px;
    box-shadow: 0 4px 6px rgba(200, 200, 200, 0.1);
    border-radius: 10px;
    position: relative;
    display: grid;
    place-items: center;
  }

  .grid-item.selected {
    background-color: rgba(151, 151, 151, 0.2);

  }

  .grid-item img {
    max-height: 100%;
    max-width: 100%;
    border-radius: 10px;
    position: relative;
    top: -13px;
  }

  .grid-item .tags {
    width: calc(100% - 26px);
    position: absolute;
    bottom: 13px;
    left: 13px;
  }

  .grid-item .tags .title {
    width: min-content;
    white-space: nowrap;
    font-weight: 700;
    float: left;
    position: relative;
  }

  .grid-item .tags .title span{
    position: absolute;
    top: 20px;
    left: 8px;
    font-weight: normal;
    font-size: 0.7em;
    color: #888;
  }

  .grid-item .tags .tag {
    width: min-content;
    background-color: darkgreen;
    padding: 3px 8px;
    font-weight: 700;
    float: right;
    border-radius: 3px;
  }

</style>
