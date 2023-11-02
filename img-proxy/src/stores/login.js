import {jwtDecode} from 'jwt-decode'
import {defineStore} from 'pinia'
import {useWebSocketStore} from "@/stores/socket";


export const useLoginStore = defineStore('login', {
  state: () => ({
    isBoxOpen: false,
    userProfile: null
  }),
  actions: {
    openBox() {
      this.isBoxOpen = true;
    },
    closeBox() {
      this.isBoxOpen = false;
    },
    setProfile(profile) {
      this.userProfile = profile;
    },
    setCookie(name, value, expire=-1, days=-1) {
      let expires_key = ''
      if (expire) {
        const expires = new Date(expire);
        expires_key = `expires=${expires.toUTCString()}; `
      } else if (days > -1) {
        const expires = new Date();
        expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
        expires_key = `expires=${expires.toUTCString()}; `
      }
      document.cookie = `${name}=${value}; ${expires_key}SameSite=Strict; path=/`;
    },
    getCookie(name) {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.startsWith(`${name}=`)) {
          return cookie.substring(name.length + 1);
        }
      }
      return null;
    },
    async login(username, password, remember_me) {
      const socket = useWebSocketStore()
      const respons = await socket.sendRequest({
        cmd: 'user_login', params: {
          username: username,
          password: password,
          remember_me: remember_me
        }
      })
      if (respons?.status === 'ok') {
        this.setProfile(jwtDecode(respons.access_token))
        this.setCookie('access_token', respons.access_token,
           this.userProfile?.exp ? parseFloat(this.userProfile?.exp)*1000: -1)
        this.closeBox()
        return true
      } else {
        this.setProfile(null)
        this.setCookie('access_token', '', 0)
        return false
      }
    },
    async automatic_login() {
      let access_token = this.getCookie('access_token')
      if (access_token) {
        const socket = useWebSocketStore()
        const respons = await socket.sendRequest({cmd: 'automatic_login', access_token: access_token})
        if (respons?.status === 'ok') {
          this.setProfile(jwtDecode(access_token))
          console.info('Automatic login')
          return true
        }
      }
      this.setProfile(null)
      this.setCookie('access_token', '', 0)
      return false
    },
    logout() {
      this.setProfile(null)
      this.setCookie('access_token', '', 0)
      const socket = useWebSocketStore()
      socket.conn.close()
    }
  }
});
