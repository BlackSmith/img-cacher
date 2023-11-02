<script>
import {watch} from "vue";
import {useLoginStore} from "@/stores/login";
import {Modal} from "bootstrap";

export default {
  setup() {
    const loginStore = useLoginStore()
    return {loginStore}
  },
  mounted() {
    this.box = new Modal(this.$refs.loginBox);
    watch(() => this.loginStore.isBoxOpen, (newValue) => {
      if (newValue) {
        this.box.show();
      } else {
        this.box.hide();
      }
    });
  },
  beforeMount() {
    this.loginStore.closeBox();
  },
  methods: {
    onBoxHidden() {
      this.loginStore.closeBox();
    },
    async send() {
      let isOK = true
      if (this.$refs.username.value.length === 0) {
        this.$refs.username.classList.add('is-invalid')
        isOK = false
      } else {
        this.$refs.username.classList.remove('is-invalid')
      }
      if (this.$refs.password.value.length === 0) {
        this.$refs.password.classList.add('is-invalid')
        isOK = false
      } else {
        this.$refs.password.classList.remove('is-invalid')
      }
      if (isOK) {
        if (await this.loginStore.login(this.$refs.username.value, this.$refs.password.value, this.$refs.rememberme.checked)) {
          this.$refs.password.value = '';
        } else {
          this.$refs.password.classList.add('is-invalid')
        }
      }
      return false
    },
    async keyPress(event) {
      if (event.keyCode === 13) {
        await this.send()
      }
    }
  }
}
</script>

<template>
  <div class="modal fade" tabindex="-1" ref="loginBox" aria-hidden="true" @hidden="onBoxHidden">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Login</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close" @click="onBoxHidden"></button>
        </div>
        <div class="modal-body">
          <form>
            <div class="mb-3">
              <label for="user-name" class="col-form-label">Username:</label>
              <input type="text" class="form-control" id="user-name" @keyup="keyPress" ref="username">
            </div>
            <div class="mb-3">
              <label for="password" class="col-form-label">Password:</label>
              <input type="password" class="form-control" id="password" @keyup="keyPress" ref="password">
            </div>
            <div class="mb-3 form-check">
              <input type="checkbox" class="form-check-input" id="remember-me" checked @keyup="keyPress" ref="rememberme">
              <label for="remember-me" class="form-check-label">Remember me</label>
            </div>
          </form>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" @click="onBoxHidden">Close</button>
          <button type="button" class="btn btn-primary" @click="send">Login</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>
