import { defineStore } from 'pinia'
import {useImagesStore} from "@/stores/images";
import {useCollectionStore} from "@/stores/collections";
import {useLoginStore} from "@/stores/login";

export const useWebSocketStore = defineStore({
   id: 'socket',
   state: () => ({
     url: null,
     conn: null,
     message: "",
     reconnectError: false,
     heartBeatInterval: 50000,
     heartBeatTimer: 0,
     reconnectTimer: 0,
     json: true,
     messageQueue: [],
     pendingRequests: new Map(),
  }),
  getters: {
     stores(){
       return [useImagesStore(), useCollectionStore(), useLoginStore()]
     }
  },
  actions: {
    open(url) {
      if (!this.url && url) {
        this.url = url
      }
      if (this.conn && this.conn.readyState === WebSocket.OPEN) {
        return true
      }
      try {
        this.conn = new WebSocket(this.url);
      } catch (ex) {
        console.error("Websocket: connection error. "+ex)
        this.conn = null
        return false
      }
      this.conn.onopen = this.handleOpen;
      this.conn.onmessage = this.handleMessage;
      this.conn.onerror = this.handleError;
      this.conn.onclose = this.handleClose;
      return true
    },

    send(msg) {
      if (!this.conn || this.conn.readyState !== WebSocket.OPEN) {
        this.messageQueue.push(msg);
      } else {
        this.conn.send(msg)
      }
    },
    sendObj(obj) {
      return this.send(JSON.stringify(obj))
    },
    sendRequest(msg) {
      console.debug('Send request:', msg);
      return new Promise((resolve) => {
        const requestId = Math.random().toString(36).substring(7);
        this.pendingRequests.set(requestId, resolve);
        this.sendObj({
          ...msg,
          requestId,
        });
      });
    },
    async handleOpen() {
      console.info('WebSocket connection established');
      this.isConnected = true;
      const login = useLoginStore()
      await login.automatic_login()
      while (this.messageQueue.length > 0) {
        const msg = this.messageQueue.shift();
        this.conn.send(msg);
      }
      this.heartBeatTimer = window.setInterval(() => {
        this.conn && this.conn.readyState === WebSocket.OPEN && this.sendObj({cmd: 'ping'})
      }, this.heartBeatInterval);
    },
    handleMessage(event) {
      // event = { data: string; action: string; }
      if (!event.data) {
        return
      }
      if (event.data === "{'cmd':'pong'}") {
        return
      }
      console.debug('Received message:', event.data);
      this.message = event.data
      if (this.json && this.message && this.message[0] === '{') {
        let msg = JSON.parse(this.message)
        const requestID = msg?.requestId
        if (requestID && this.pendingRequests.has(requestID)) {
          // Request & Response
          const resolve = this.pendingRequests.get(requestID);
          resolve(msg);
          this.pendingRequests.delete(requestID);
        } else {
          // Pub & sub
          this.message = msg
          if (msg.action) {
            let path = msg.action.split('.')
            if (path.length === 1 && this[msg.action]) {
              this[msg.action](msg?.data)
            } else {
              for (let ix in this.stores) {
                let store = this.stores[ix]
                if (store.$id === path[0] && store[path[1]]) {
                  store[path[1]](msg?.data)
                }
              }
            }
          }
        }
      }
    },
    handleError(event) {
      console.error('WebSocket error:', event);
    },
    reconnect() {
      this.reconnectTimer = window.setInterval(() => {
        if (this.open()) window.clearInterval(this.reconnectTimer)
      }, 3000)
    },
    handleClose(event) {
      console.warn('WebSocket connection closed:', event);
      this.isConnected = false;
      window.clearInterval(this.heartBeatTimer);
      this.heartBeatTimer = 0;
      this.reconnect()
    }
  }
})
