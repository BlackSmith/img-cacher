<script lang="ts">
import RightPanel from "@/components/RightPanel.vue";
import {defineComponent, watch, ref} from "vue";
import {useImagesStore} from '@/stores/images'
import {useWebSocketStore} from '@/stores/socket'
import {useLoginStore} from '@/stores/login'
import TinyWindow from "@/components/detail/TinyWindow.vue";
import YandexWindow from "@/components/detail/YandexWindow.vue";

export default defineComponent({
  components: {TinyWindow, YandexWindow, RightPanel},
  emits: ['close', 'open', 'updateImage'],
  setup() {
    const loginStore = useLoginStore()
    const socket = useWebSocketStore()
    const imagesStore = useImagesStore()
    return {loginStore, socket, imagesStore}
  },
  props: {
    startOpen: {
      type: Boolean,
      default: false
    },
    width: {
      type: String,
      default: '20%'
    },
    backgroundColor: {
      type: String,
      default: '#333'
    },
    selectedImage: null,
    isDetailView: {
      type: Boolean,
      default: false
    }

  },
  data() {
    return {
      isOpen: this.startOpen,
      thumbCreated: ref(1),
      showMenu: false,
      editTitle: false,
      oldTitle: null,
    }
  },
  computed: {
    is_user_login() {
      return this.loginStore.userProfile !== null;
    },
    is_image_main() {
      return this.selectedImage?.uuid.indexOf(':') == -1;
    },
    panelWidth() {
      return this.isOpen ? this.$refs.panel.panelWidth : 0;
    }
  },
  mounted() {
    watch(
        () => this.selectedImage,
        (newValue, oldValue) => {
          if (newValue === null) {
            this.close()
          } else {
            this.open()
          }
          if (newValue?.uuid == oldValue?.uuid && newValue?.thumb_created != oldValue?.thumb_created) {
            console.info('Thumb image is reloaded.')
            this.$refs.imagePreview.src = this.getPreview(newValue)
          }
        }
    );
  },
  methods: {
    close() {
      this.$emit('close')
      this.isOpen = false;
    },
    open() {
      this.$emit('open')
      this.isOpen = true;
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
    dateFormat(ts) {
      return (new Date(parseInt(ts) * 1000)).toLocaleDateString(
          'cs-CZ', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            timeZoneName: 'short'
          }
      )
    },
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
      event.target.src = this.backendUrl + '/static/default.png'
    },
    getImageUrl(image) {
      return this.backendUrl + '/' + image.filename
    },
    toggleMenu() {
      this.showMenu = !this.showMenu;
    },
    openTinyRefs() {
      this.$refs.tinyPanel.open(this.selectedImage)
    },
    openYandexRefs() {
      this.$refs.yandexPanel.open(this.selectedImage)
    },
    titleEdit() {
      if (this.is_user_login) {
        this.editTitle = true;
        this.oldTitle = `${this.selectedImage.title}`
      }
    },
    titleReset() {
      this.$emit('updateImage', 'title', this.oldTitle);
      this.editTitle = false;
    },
    async titleSave() {
      let resp = await this.socket.sendRequest({
        cmd: 'update_image',
        params: {
          uuid: this.selectedImage.uuid,
          title: this.selectedImage.title
        }
      })
      if (resp.status !== 'ok') {
        console.error(resp.msg)
        return
      }
      this.editTitle = false
    },
  }
})
</script>

<template>
  <RightPanel :is-open="isOpen" :title="selectedImage?.title" :width="width"
              :backgroundColor="backgroundColor" ref="panel">
    <template v-slot:panelHeader>
      <slot name="header"></slot>
    </template>
    <template v-slot:default>
      <div class="info" v-if="selectedImage">
        <h4 :class="{'title': true, 'edit': is_user_login}" v-if="!editTitle"
            @click="titleEdit">{{ selectedImage.title }}&nbsp;<span class="bi bi-feather"></span>
        </h4>
        <div class="title-edit input-group mb-3" v-if="editTitle">
          <input type="text" class="form-control"
                 @input="$emit('updateImage', 'title', $event.target.value)"
                 :value="selectedImage.title"
                 @keyup.enter="titleSave"
                 @keyup.esc="titleReset">
          <button class="btn btn-outline-secondary bi bi-check" type="button" @click="titleSave"></button>
          <button class="btn btn-outline-secondary bi bi-x" type="button" @click="titleReset"></button>
        </div>
        <div class="resolution">{{ selectedImage.width }} x {{ selectedImage.height }}
          <span>( {{ getSize(selectedImage.size) }} )</span>
        </div>
        <div class="preview">
        <img :src="getPreview(selectedImage)"
             ref="imagePreview"
             v-on:error="thumbErrorHandler"
             :alt="'Preview of '+selectedImage.title"
             :key="thumbCreated" />
        </div>
        <table class="details">
          <tbody>
          <tr>
            <th>Filename:</th>
            <td><a :href="getImageUrl(selectedImage)">{{ selectedImage.filename }}</a></td>
          </tr>
          <tr>
            <th>Type:</th>
            <td>{{ selectedImage.content_type }}</td>
          </tr>
          <tr v-if="selectedImage.created">
            <th>Saved:</th>
            <th>{{ dateFormat(selectedImage.created) }}</th>
          </tr>

          <tr v-if="selectedImage.duration">
            <th>Duration:</th>
            <td>{{ selectedImage.duration }}s</td>
          </tr>
          <tr v-if="selectedImage.bitrate_kbps">
            <th>Bitrate:</th>
            <td>{{ selectedImage.bitrate_kbps }} Kbps</td>
          </tr>
          <tr v-if="selectedImage.url">
            <th>Original&nbsp;url:</th>
            <td><a :href="selectedImage.url" target="_blank">{{ selectedImage.url }}</a></td>
          </tr>
          <tr v-if="selectedImage.reddit_score">
            <td>Reddit score:</td>
            <th>{{ selectedImage.reddit_score }}</th>
          </tr>
          <tr>
            <td colspan="2">&nbsp;</td>
          </tr>
          <tr class="iconPanel" v-if="is_user_login">
            <td>Actions:</td>
            <td>
              <div
                  v-if="selectedImage.content_type?.startsWith('image/') && is_user_login"
                  class="icon tineye" title="Search image on Tineye"
                  @click="openTinyRefs"></div>
              <div
                  v-if="selectedImage.content_type?.startsWith('image/') && is_user_login"
                  class="icon yandex" title="Search image on Yandex"
                  @click="openYandexRefs"></div>
            </td>
          </tr>
          <tr v-if="selectedImage.original_uuid">
            <td class="linkHead">Links:</td>
            <th><p v-for="it in selectedImage.original_uuid.split(';')" class="links">{{ it }}</p></th>
          </tr>
          <slot name="tableItems"></slot>
          </tbody>
        </table>
        <slot name="otherContent"></slot>
      </div>
    </template>
  </RightPanel>
  <TinyWindow ref="tinyPanel"></TinyWindow>
  <YandexWindow ref="yandexPanel"></YandexWindow>
</template>


<style scoped>
.info {
  width: calc(100% - 2rem);
  text-align: center;
  margin: 1rem;
}

.details {
  text-align: left;
  width: 100%;
}

.details tr {
  line-height: 200%;
  max-width: 100%;
}

.details tr th {
  vertical-align: top;
  padding-right: 1rem
}

.details a {
  color: #2aabd2;
}

.title {
  text-align: center;
  font-size: 1.8em;
  padding-bottom: .5rem;
  display: inline-block;
}

.title.edit:hover {
  color: cornflowerblue;
  cursor: pointer;
}

.title.edit {
  cursor: text;
}

.title span {
  font-size: 1rem;
  vertical-align: top;
  visibility: hidden;
}

.title.edit:hover span {
  visibility: visible;
}

.title-edit {
  text-align: left;
  width: 100%;
}
.resolution {
  width: 100%;
  text-align: center;
}

.resolution span {
  margin-left: 1rem;
}

.preview {
  padding: .5rem 0;
}

.preview img {
  border-radius: 5px;
  width: 90%;
}

.linkHead {
  vertical-align: top;
}

.links {
  margin: 0;
}

.iconPanel {
  margin-top: 8px;
}

.icon {
  width: 25px;
  height: 25px;
  border: 1px solid #777777;
  margin: 4px;
  border-radius: 3px;
  cursor: pointer;
  float: left;
}

.icon.tineye {
  background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACMAAAAkCAYAAAAD3IPhAAAAw3pUWHRSYXcgcHJvZmlsZSB0eXBl IGV4aWYAAHjabVBBDgMhCLzzij5BAVl4jtu1SX/Q5xeVbda2kzggQ0YE2uv5gFsHZgYum4qJJAcb G1ZPNE3UwTnx4AGk0PJaB+QQ0Eu9KRpVov+s54/BDNWzcjHSewj7Klg8gPplhDNQn6jnRxhZGBFO IYdBnd9KYrpdv7C3tELngU6s69g/9823dxR/hxAbZUrORDwHoH4IqHpizkjmjZl4VMS5kISZL+Tf nk7AG+WCWSDVtTjqAAABhGlDQ1BJQ0MgcHJvZmlsZQAAeJx9kT1Iw0AcxV/TalUqDnYQUchQneyi Io61CkWoEGqFVh1MLv2CJg1Ji4uj4Fpw8GOx6uDirKuDqyAIfoC4ujgpukiJ/0sKLWI8OO7Hu3uP u3eA0CgzzQrEAE2vmqlEXMxkV8XgK3oxihC6EZCZZcxJUhKe4+sePr7eRXmW97k/R7+asxjgE4lj zDCrxBvEM5tVg/M+cZgVZZX4nHjCpAsSP3JdcfmNc8FhgWeGzXRqnjhMLBY6WOlgVjQ14mniiKrp lC9kXFY5b3HWyjXWuid/YSinryxzneYIEljEEiSIUFBDCWVUEaVVJ8VCivbjHv5hxy+RSyFXCYwc C6hAg+z4wf/gd7dWfmrSTQrFga4X2/4YA4K7QLNu29/Htt08AfzPwJXe9lcawOwn6fW2FjkCBraB i+u2puwBlzvA0JMhm7Ij+WkK+TzwfkbflAUGb4G+Nbe31j5OH4A0dZW8AQ4OgfECZa97vLuns7d/ z7T6+wExonKM71QoeQAADXhpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADw/eHBhY2tldCBiZWdp bj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+Cjx4OnhtcG1ldGEgeG1sbnM6 eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IlhNUCBDb3JlIDQuNC4wLUV4aXYyIj4KIDxyZGY6 UkRGIHhtbG5zOnJkZj0iaHR0cDovL3d3dy53My5vcmcvMTk5OS8wMi8yMi1yZGYtc3ludGF4LW5z IyI+CiAgPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIKICAgIHhtbG5zOnhtcE1NPSJodHRw Oi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvbW0vIgogICAgeG1sbnM6c3RFdnQ9Imh0dHA6Ly9ucy5h ZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZUV2ZW50IyIKICAgIHhtbG5zOmRjPSJodHRw Oi8vcHVybC5vcmcvZGMvZWxlbWVudHMvMS4xLyIKICAgIHhtbG5zOkdJTVA9Imh0dHA6Ly93d3cu Z2ltcC5vcmcveG1wLyIKICAgIHhtbG5zOnRpZmY9Imh0dHA6Ly9ucy5hZG9iZS5jb20vdGlmZi8x LjAvIgogICAgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIgogICB4bXBN TTpEb2N1bWVudElEPSJnaW1wOmRvY2lkOmdpbXA6Y2MzNTc0ZjQtYWY2YS00N2M4LWIwMjEtMzI5 ZWMzYWRmZjAzIgogICB4bXBNTTpJbnN0YW5jZUlEPSJ4bXAuaWlkOmVlNjFjY2NkLWU3NzItNGFm MC05NGE3LTc5ZDM0YzNlZTg0ZCIKICAgeG1wTU06T3JpZ2luYWxEb2N1bWVudElEPSJ4bXAuZGlk Ojk1ZmM5NzI5LTMyYmEtNDA5Mi1hNzNiLTNhYTI3YjQ2NWI4NCIKICAgZGM6Rm9ybWF0PSJpbWFn ZS9wbmciCiAgIEdJTVA6QVBJPSIyLjAiCiAgIEdJTVA6UGxhdGZvcm09IkxpbnV4IgogICBHSU1Q OlRpbWVTdGFtcD0iMTY5NTk4OTIxNjExMDQ0MCIKICAgR0lNUDpWZXJzaW9uPSIyLjEwLjM0Igog ICB0aWZmOk9yaWVudGF0aW9uPSIxIgogICB4bXA6Q3JlYXRvclRvb2w9IkdJTVAgMi4xMCIKICAg eG1wOk1ldGFkYXRhRGF0ZT0iMjAyMzowOToyOVQxNDowNjo1NiswMjowMCIKICAgeG1wOk1vZGlm eURhdGU9IjIwMjM6MDk6MjlUMTQ6MDY6NTYrMDI6MDAiPgogICA8eG1wTU06SGlzdG9yeT4KICAg IDxyZGY6U2VxPgogICAgIDxyZGY6bGkKICAgICAgc3RFdnQ6YWN0aW9uPSJzYXZlZCIKICAgICAg c3RFdnQ6Y2hhbmdlZD0iLyIKICAgICAgc3RFdnQ6aW5zdGFuY2VJRD0ieG1wLmlpZDoxZWMxZjE2 ZS1hNDJmLTQxMGQtYWVlZS1lNTU1YzdlZGRhYmEiCiAgICAgIHN0RXZ0OnNvZnR3YXJlQWdlbnQ9 IkdpbXAgMi4xMCAoTGludXgpIgogICAgICBzdEV2dDp3aGVuPSIyMDIzLTA5LTI5VDE0OjA2OjU2 KzAyOjAwIi8+CiAgICA8L3JkZjpTZXE+CiAgIDwveG1wTU06SGlzdG9yeT4KICA8L3JkZjpEZXNj cmlwdGlvbj4KIDwvcmRmOlJERj4KPC94OnhtcG1ldGE+CiAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAK ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg IAogICAgICAgICAgICAgICAgICAgICAgICAgICAKPD94cGFja2V0IGVuZD0idyI/PrBMS2YAAAAG YktHRAD/AP8A/6C9p5MAAAAJcEhZcwAACxMAAAsTAQCanBgAAAAHdElNRQfnCR0MBjgftIrVAAAL NElEQVRYw8WYe5BU1ZnAf/fVt7tvv2Z63sMMwwzzYBhHhBFwUfAPHjHqBMsya0xixQQ1tdmVRaLU KhpdtLY2rixqYUWi7vqqTbJmUxADAquugETAAOoMr3kz7+lhumf6efv2vXf/GNKzDRit/LH5qrq6 z3fO+e6vz/nO933nCgCrtx68FdgAXAt4+P+RGHAM2LrvwRveARBWbz34FPAof0ERbOvpvRtXbBZW bz1oAyxKHiEv0UeHdg19zto/37Jp4HKqyKIw3bRsEob1VWa2ygD3KftZIp4kOXYMa/zfeKNsE8e8 N37p7EjP50z2tRMf7kSPhklNXcCIhREFyOgpAGzRgeoPsuq2u8lb9DVC8QwZy8a07EvNbZDrzC6W ujuR8+egD5/Giof55sTP+YNnOZYgXhEiKEQ59MqT9Lcd+VJgiQRLCyMcevtFbvJJrFq2EqfbQ9JU 6Aun6B1PENMzAC2yMzVOYvRjFFkmkB4l6naRjoxCpX1F43PlC7z4wNqvtGNVMmxct4LhpfdTnnbS 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");
}

.icon.yandex {
  background-image: url("/static/yandex.png");
}

</style>
