<script>
export default {
  name: 'RightPanel',
  emits: ['closing'],
  props: {
    isOpen: {
      type: Boolean,
      default: false
    },
    title: {
      type: String,
      default: ''
    },
    width: {
      type: String,
      default: '20%'
    },
    backgroundColor: {
      type: String,
      default: '#333'
    }
  },
  computed: {
    panelWidth() {
      return this.$refs.panel.clientWidth
    }
  }
}
</script>

<template>
  <div class="panel" v-bind:class="{ 'open': isOpen }" ref="panel">
    <div class="header">
      <slot name="panelHeader"></slot>
    </div>
    <div class="content">
    <slot></slot>
    </div>
  </div>
</template>

<style scoped>
.panel {
  position: absolute;
  top: 0;
  right: calc(-1.1 * 100%);
  width: v-bind(width);
  min-width: 350px;
  height: 100%;
  background-color: v-bind(backgroundColor);
  color: white;
  transition: right 0.3s;
  overflow-y: auto;
  /*padding: 13px 5px 13px 13px;*/
  border-left: 1px solid rgba(92, 92, 92, 0.5);
}
.open {
  right: 0;
}
.panel .header {
  position: relative;
  margin: .5rem .5rem 0 .5rem;
}
.panel .header h2 {
  line-height: 1em;
  margin-left: 30px;
  text-align: center;
}
.panel .header button{
  position: absolute;
  top: 3px;
  left: 0;
  color: #eee;
  background-color: #666;
  border: 0;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 8px;
}
</style>
