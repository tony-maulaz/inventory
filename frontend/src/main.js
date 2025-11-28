import { createApp } from "vue";
import { createVuetify } from "vuetify";
import * as components from "vuetify/components";
import * as directives from "vuetify/directives";
import "vuetify/styles";
import "@mdi/font/css/materialdesignicons.css";

import App from "./App.vue";

const palette = {
  primary: "#1f4b99",
  secondary: "#6b7a90",
  accent: "#7bc5ff",
  info: "#3c5d7b",
  success: "#3aa0a2",
  warning: "#e8a23c",
  error: "#d64545",
};

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: "lightBlue",
    themes: {
      lightBlue: {
        dark: false,
        colors: {
          background: "#f5f7fb",
          surface: "#ffffff",
          ...palette,
        },
      },
      darkBlue: {
        dark: true,
        colors: {
          background: "#0f1724",
          surface: "#131c2d",
          primary: "#7bc5ff",
          secondary: "#4a5568",
          accent: "#9ad6ff",
          info: "#6aa1ff",
          success: "#62d7c7",
          warning: "#f7c266",
          error: "#ff7b7b",
        },
      },
    },
  },
});

createApp(App).use(vuetify).mount("#app");
