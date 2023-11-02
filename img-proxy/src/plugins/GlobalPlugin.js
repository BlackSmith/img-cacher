const GlobalPlugin = {
  install: (app, options) => {
    for (const key in options) {
      if (Object.prototype.hasOwnProperty.call(options, key)) {
        app.config.globalProperties[key] = options[key];
      }
    }
  }
};
export {GlobalPlugin};
