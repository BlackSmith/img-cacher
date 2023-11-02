import {useWebSocketStore} from "@/stores/socket";

const WebSocketPlugin = {
  install: (app, options) => {
    app.config.globalProperties.socket = useWebSocketStore()
    app.config.globalProperties.socket.open(options.url)
  }
};
export {WebSocketPlugin};
