<script lang="ts">
  import {defineComponent, watch} from "vue";

  export default defineComponent({
    emits: ['toggle', 'select'],
    props: {
      isOpen: {
        type: Boolean,
        default: true
      },
      headTitle: null,
      images: {},
      selected: null,
      minusWidth: {
        type: String,
        default: '0%'
      }
    },
    data() {
      return {
        open: this.isOpen,
      }
    },
    mounted() {
      watch(
          () => this.isOpen,
          (newValue) => {
            this.open = newValue
          }
      );
    },
    methods: {
      getPreview(image) {
        if (image?.thumb_file) {
          return this.backendUrl + '/' + image.thumb_file
        }
        if (image?.filename === undefined) {
          return this.backendUrl + '/static/default.png'
        }
        let parts = image.filename.split('/')
        let file = parts.pop()
        parts.push('.thumb')
        parts.push(file)
        return this.backendUrl + '/' + parts.join('/') + '?t=' + image?.thumb_created
      },
      toggle() {
        this.open = !this.open;
        this.$emit('toggle')
      },
      thumbErrorHandler(event) {
        const efile = this.backendUrl + '/static/default.png'
        if (event.target.src != efile) {
          event.target.src = efile
        }
      }
    },
  })
</script>

<template>
  <div :class="{'alternates': true, 'close': !open}">
    <div :class="{'earBox': true, 'bi':true, 'bi-chevron-double-down': open,
                 'bi-chevron-double-up': !open}"
         @click="toggle" title="Alternates">
      <h4 v-if="headTitle">{{ headTitle }}</h4>
    </div>
    <div class="alternatesList">
      <slot name="left"></slot>
      <div :class="{'alternatesPreview': true, 'alternateSelected': selected?.uuid == aimage?.uuid}"
           v-for="aimage in images"
           :key="aimage?.filename">
        <a href="#" @click="$emit('select', aimage.uuid)">
          <img :src="getPreview(aimage)" v-on:error="thumbErrorHandler" alt="" />
          <div class="mainBox" v-if="aimage.uuid.indexOf(':') == -1" title="Main Alternation"></div>
        </a>
      </div>
    </div>
  </div>
</template>

<style scoped>
.alternates {
  width: calc(100% - v-bind(minusWidth));
  height: 20%;
  min-height: 180px;
  position: absolute;
  bottom: 0;
  left: 0;
  background-color: rgba(48, 48, 48, 0.8);
  /*border-radius: 8px 8px 0 0;*/
  text-align: left;
  border: 1px solid rgba(92, 92, 92, 0.5);
}

.alternates.close {
  height: 0;
  min-height: 0;
}

.earBox {
  color: #ffffff;
  display: block;
  padding: 5px 15px 0 15px;
  cursor: pointer;
  position: relative;
  width: 100%;
  height: 33px;
  text-align: right;
}

.alternates.close .earBox {
  bottom: 0;
  position: absolute;
  right: 0;
  width: auto;
  background-color: rgba(48, 48, 48, 0.7);
  border-radius: 8px 0 0 0;
}

.alternates .earBox h4 {
  float: left;
  font-size: .9em;
  padding-top: 2px;
  margin-right: 15px;
}


.alternates .alternatesList {
  clear: left;
  /*display: flex;*/
  flex-wrap: nowrap;
  overflow-x: auto;
  height: 70%;
}

.alternates.close .alternatesList {
  display: none;
}

.alternates .alternatesPreview {
  float: left;
  position: relative;
  min-width: 100px;
  margin: 0 1rem;
  height: 100%;
}

.alternates .alternatesPreview img {
  object-fit: contain;
  border-radius: 8px;
  border: 2px transparent solid;
  height: 100%;
}

.alternates .mainBox {
  position: absolute;
  left: 1px;
  top: 1px;
  width: 0;
  height: 0;
  border-left: 1.2rem solid rgba(255, 0, 0, 0.8);
  border-right: 1.2rem solid transparent;
  border-bottom: 1.2rem solid transparent;
  border-top-left-radius: 8px;
}

.alternates .alternateSelected img {
  border-color: silver;
}

</style>
